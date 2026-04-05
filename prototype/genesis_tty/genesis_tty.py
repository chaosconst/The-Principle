#!/usr/bin/env python3
"""
Genesis TTY — real PTY + pyte + AI collaboration

  ┌─ TTY ─────────────────────────────────────────┐  45%  real shell
  │  (click to focus, type commands, vim works)   │
  ├─ Chat ─────────────────────────────────────────┤  1fr  AI conversation
  │  [streaming]                                   │
  └─ > AI input ───────────────────────────────────┘  3    chat with AI

AI sees the TTY screen via [Realtime TTY] before every inference.
AI-issued /shell exec commands run directly in the PTY.
"""

import asyncio, fcntl, json, os, pty, re, socket, struct, termios
from datetime import datetime
from pathlib import Path

import aiohttp
import pyte
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual import events, work
from textual.widgets import RichLog, Input, Static
from textual.containers import Vertical
from rich.text import Text
from rich.style import Style

# ── Constants ─────────────────────────────────────────────────────────────────

DEVICE = socket.gethostname().removesuffix('.local')
CONFIG_PATH = Path.home() / '.infero' / 'tty_config.json'
STOP = ['\nSystem - [Shell]', '\n[System Environment]', 'System - [Browser]', '\n[Realtime TTY]']

SYSTEM = f"""You are a collaborative shell AI on {DEVICE}.

You are connected to a real interactive terminal. The current terminal screen is shown
in [Realtime TTY] — you can see exactly what the user sees, including vim, htop, etc.

## Execution

Run commands in the shared PTY (stdout auto-captured and returned to you):
/shell exec {DEVICE}
```bash
command here
```

Send keyboard input to whatever is running in the PTY:
/shell key {DEVICE}
text or {{ctrl+c}} or {{escape}}:wq{{enter}}

Key syntax: plain text is typed as-is. Named keys in braces: {{enter}} {{escape}}
{{ctrl+c}} {{ctrl+d}} {{tab}} {{up}} {{down}} {{left}} {{right}} etc.

Example — open vim and quit:
/shell exec {DEVICE}
```bash
vim /tmp/test.txt
```
/shell key {DEVICE}
ihello world{{escape}}:wq{{enter}}

Rules:
- End with /self_continue (keep going) or /call_for_human (wait for input)
- To capture output: redirect to /tmp/result (e.g. `ls > /tmp/result`), it returns to ctx
- Otherwise see the screen via [Realtime TTY]
- You also see the live screen via [Realtime TTY] before each inference
- *Infero, ergo sum.*
"""

# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    if k := os.environ.get('ANTHROPIC_API_KEY'):
        return {'format': 'anthropic', 'model': 'claude-opus-4-6', 'token': k,
                'endpoint': 'https://api.anthropic.com/v1/messages'}
    if k := os.environ.get('OPENAI_API_KEY'):
        return {'format': 'openai', 'model': 'gpt-4o', 'token': k,
                'endpoint': 'https://api.openai.com/v1/chat/completions'}
    return None

# ── Key map (textual key names → PTY byte sequences) ─────────────────────────

KEY_MAP: dict[str, bytes] = {
    "enter":     b"\r",
    "backspace": b"\x7f",
    "delete":    b"\x1b[3~",
    "escape":    b"\x1b",
    "tab":       b"\t",
    "ctrl+a": b"\x01", "ctrl+b": b"\x02", "ctrl+c": b"\x03",
    "ctrl+d": b"\x04", "ctrl+e": b"\x05", "ctrl+f": b"\x06",
    "ctrl+h": b"\x08", "ctrl+k": b"\x0b", "ctrl+l": b"\x0c",
    "ctrl+n": b"\x0e", "ctrl+p": b"\x10", "ctrl+r": b"\x12",
    "ctrl+u": b"\x15", "ctrl+w": b"\x17", "ctrl+x": b"\x18",
    "ctrl+y": b"\x19", "ctrl+z": b"\x1a",
    "up":       b"\x1b[A", "down":     b"\x1b[B",
    "right":    b"\x1b[C", "left":     b"\x1b[D",
    "home":     b"\x1b[H", "end":      b"\x1b[F",
    "pageup":   b"\x1b[5~", "pagedown": b"\x1b[6~",
    "f1":  b"\x1bOP",   "f2":  b"\x1bOQ",  "f3":  b"\x1bOR",  "f4":  b"\x1bOS",
    "f5":  b"\x1b[15~", "f6":  b"\x1b[17~","f7":  b"\x1b[18~","f8":  b"\x1b[19~",
    "f9":  b"\x1b[20~", "f10": b"\x1b[21~","f11": b"\x1b[23~","f12": b"\x1b[24~",
}

# Pyte named color → Rich color name
PYTE_COLORS: dict[str, str] = {
    "black": "black", "red": "red", "green": "green", "yellow": "yellow",
    "blue": "blue", "magenta": "magenta", "cyan": "cyan", "white": "white",
    "brightblack": "bright_black", "brightred": "bright_red",
    "brightgreen": "bright_green", "brightyellow": "bright_yellow",
    "brightblue": "bright_blue", "brightmagenta": "bright_magenta",
    "brightcyan": "bright_cyan", "brightwhite": "bright_white",
}

# ── PTYShell ──────────────────────────────────────────────────────────────────

class PTYShell:
    """Real PTY + pyte terminal emulator. Supports interactive programs (vim, etc)."""

    def __init__(self, cols: int = 80, rows: int = 24):
        self.cols = cols
        self.rows = rows
        self.screen = pyte.Screen(cols, rows)
        self.byte_stream = pyte.ByteStream(self.screen)
        self.master_fd: int | None = None
        self.on_update: callable | None = None   # called on every screen change

    async def start(self):
        master_fd, slave_fd = pty.openpty()
        self._winsize(master_fd, self.rows, self.cols)

        shell = os.environ.get('SHELL', '/bin/zsh')
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'

        def preexec(fd=slave_fd):
            os.setsid()
            # Make slave PTY the controlling terminal so ^C → SIGINT works
            fcntl.ioctl(fd, termios.TIOCSCTTY, 0)

        await asyncio.create_subprocess_exec(
            shell,
            stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            env=env,
            preexec_fn=preexec,
        )
        os.close(slave_fd)
        self.master_fd = master_fd

        loop = asyncio.get_running_loop()
        loop.add_reader(master_fd, self._readable)

    def _winsize(self, fd: int, rows: int, cols: int):
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))

    def resize(self, cols: int, rows: int):
        if cols == self.cols and rows == self.rows:
            return
        self.cols, self.rows = cols, rows
        self.screen.resize(rows, cols)
        if self.master_fd is not None:
            self._winsize(self.master_fd, rows, cols)

    def write(self, data: bytes):
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, data)
            except OSError:
                pass

    def _readable(self):
        try:
            data = os.read(self.master_fd, 4096)
            if data:
                self.byte_stream.feed(data)
                if self.on_update:
                    self.on_update()
        except OSError:
            asyncio.get_running_loop().remove_reader(self.master_fd)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render_rich(self, show_cursor: bool = False) -> Text:
        """Render pyte screen → Rich Text with colors."""
        out = Text(no_wrap=True, overflow="ignore")
        buf = self.screen.buffer
        cy, cx = self.screen.cursor.y, self.screen.cursor.x
        for y in range(self.screen.lines):
            row = buf[y]
            for x in range(self.screen.columns):
                ch = row[x]
                if show_cursor and y == cy and x == cx:
                    out.append(ch.data or " ", style=Style(reverse=True))
                else:
                    out.append(ch.data or " ", style=self._style(ch))
            if y < self.screen.lines - 1:
                out.append("\n")
        return out

    def _style(self, ch) -> Style:
        kw: dict = {}
        fg = self._resolve_color(getattr(ch, 'fg', 'default'))
        bg = self._resolve_color(getattr(ch, 'bg', 'default'))
        if fg: kw["color"] = fg
        if bg: kw["bgcolor"] = bg
        if getattr(ch, 'bold', False):      kw["bold"] = True
        if getattr(ch, 'italics', False):   kw["italic"] = True
        if getattr(ch, 'underscore', False): kw["underline"] = True
        return Style(**kw) if kw else Style.null()

    def _resolve_color(self, c) -> str | None:
        if c is None or c == "default":
            return None
        if isinstance(c, str):
            return PYTE_COLORS.get(c)
        if isinstance(c, int):
            return f"color({c})"
        return None

    # ── AI perception ─────────────────────────────────────────────────────────

    # Map pyte color names → ANSI escape codes
    _ANSI_FG = {
        "black": "30", "red": "31", "green": "32", "yellow": "33",
        "blue": "34", "magenta": "35", "cyan": "36", "white": "37",
        "brightblack": "90", "brightred": "91", "brightgreen": "92",
        "brightyellow": "93", "brightblue": "94", "brightmagenta": "95",
        "brightcyan": "96", "brightwhite": "97",
    }

    def snapshot(self) -> str:
        """ANSI-colored snapshot of current screen for AI consciousness."""
        lines = []
        buf = self.screen.buffer
        for y in range(self.screen.lines):
            row = buf[y]
            line = ""
            prev_style = ""
            for x in range(self.screen.columns):
                ch = row[x]
                char = ch.data or " "
                style = self._ansi_style(ch)
                if style != prev_style:
                    if prev_style:
                        line += "\033[0m"
                    if style:
                        line += style
                    prev_style = style
                line += char
            if prev_style:
                line += "\033[0m"
            lines.append(line.rstrip())
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines) if lines else "(empty)"

    def _ansi_style(self, ch) -> str:
        codes = []
        if getattr(ch, 'bold', False):      codes.append("1")
        if getattr(ch, 'italics', False):   codes.append("3")
        if getattr(ch, 'underscore', False): codes.append("4")
        fg = getattr(ch, 'fg', 'default')
        bg = getattr(ch, 'bg', 'default')
        if isinstance(fg, str) and fg in self._ANSI_FG:
            codes.append(self._ANSI_FG[fg])
        elif isinstance(fg, int):
            codes.append(f"38;5;{fg}")
        if isinstance(bg, str) and bg in self._ANSI_FG:
            codes.append(str(int(self._ANSI_FG[bg]) + 10))
        elif isinstance(bg, int):
            codes.append(f"48;5;{bg}")
        return f"\033[{';'.join(codes)}m" if codes else ""

    # ── AI command execution ──────────────────────────────────────────────────

    async def exec_and_wait(self, cmd: str, timeout: float = 30.0) -> str | None:
        """Run cmd in PTY, capture stdout via tee, return captured output."""
        sentinel = f"/tmp/_genesis_{os.urandom(4).hex()}"
        result_path = f"/tmp/_genesis_out_{os.urandom(4).hex()}"
        # No tee wrapping — interactive programs (htop, vim) must write to real TTY
        # AI sees output via snapshot; explicit capture: pipe to /tmp/result manually
        full = f"{cmd}; touch {sentinel}\n"
        self.write(full.encode())
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if os.path.exists(sentinel):
                os.unlink(sentinel)
                # Flush PTY buffers to discard residual chars (e.g. 'q' from htop exit)
                # Small delay to let echo settle before flushing
                await asyncio.sleep(0.15)
                try:
                    termios.tcflush(self.master_fd, termios.TCIOFLUSH)
                except OSError:
                    pass
                if os.path.exists(result_path):
                    content = open(result_path).read().strip()
                    os.unlink(result_path)
                    return content or None
                return None
            await asyncio.sleep(0.1)
        return None  # timed out

    def send_keys(self, keys: str):
        """Send raw keyboard input to PTY (for AI interaction with running programs)."""
        # Map named keys to bytes
        result = b""
        for token in re.split(r'(\{[^}]+\})', keys):
            if token.startswith('{') and token.endswith('}'):
                name = token[1:-1].lower()
                result += KEY_MAP.get(name, token.encode())
            else:
                result += token.encode()
        self.write(result)

# ── PTYWidget ─────────────────────────────────────────────────────────────────

class PTYWidget(Widget, can_focus=True):
    """Focusable widget that renders PTYShell and forwards all keystrokes to it."""

    DEFAULT_CSS = """
    PTYWidget {
        background: #0d0d0d;
        height: 1fr;
    }
    PTYWidget:focus {
        border: solid #33aa33;
    }
    PTYWidget:blur {
        border: solid #1a3a1a;
    }
    """

    def __init__(self, shell: PTYShell):
        super().__init__()
        self.shell = shell
        self.shell.on_update = self.refresh   # re-render on every PTY update

    def on_resize(self, event: events.Resize):
        # Use content_size (excludes border) so PTY winsize matches what's visible
        self._sync_size()

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    def _sync_size(self):
        w, h = self.content_size.width, self.content_size.height
        if w > 0 and h > 0:
            self.shell.resize(w, h)

    def render(self):
        # Always sync size before rendering (guards against border changes)
        self._sync_size()
        return self.shell.render_rich(show_cursor=self.has_focus)

    def on_key(self, event: events.Key):
        key = event.key
        if key in KEY_MAP:
            self.shell.write(KEY_MAP[key])
        elif event.character:
            self.shell.write(event.character.encode())
        else:
            return   # unknown key → don't consume, let bubble
        event.stop()
        event.prevent_default()

# ── Brain ─────────────────────────────────────────────────────────────────────

CONSCIOUSNESS_FILE = Path("consciousness.txt")

class Brain:
    def __init__(self, cfg):
        self.cfg = cfg
        self.consciousness = CONSCIOUSNESS_FILE.read_text() if CONSCIOUSNESS_FILE.exists() else ""

    def _save(self):
        CONSCIOUSNESS_FILE.write_text(self.consciousness)

    def perceive(self, user_input: str | None = None):
        now = datetime.now()
        tz = now.astimezone().strftime('%z')
        parts = [
            f"[System Environment]\n"
            f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC{tz})\n"
            f"Device: {DEVICE}\n"
            f"Reminder: end with /self_continue or /call_for_human"
        ]
        if user_input:
            parts.append(f"Human: {user_input}")
        self.consciousness += '\n\n'.join(parts) + '\n\n'
        if user_input:
            self._save()

    def append_ai(self, text: str):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.consciousness += f"**Digital Being - [{ts}]**\n{text}\n\n"
        self._save()

    async def infer(self, on_token, realtime: str | None = None):
        fmt      = self.cfg.get('format', 'anthropic')
        model    = self.cfg['model']
        token    = self.cfg['token']
        endpoint = self.cfg['endpoint']

        # Ephemeral context: injected for this inference only, never saved
        prompt = self.consciousness
        if realtime:
            prompt += f"[Realtime TTY]\n{realtime}\n\n"

        headers = {'Content-Type': 'application/json'}
        if fmt == 'anthropic':
            headers['x-api-key'] = token
            headers['anthropic-version'] = '2023-06-01'
            payload = {
                'model': model, 'system': SYSTEM,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 4096, 'stream': True, 'temperature': 0.7,
                'stop_sequences': STOP,
            }
        elif fmt == 'openai':
            headers['Authorization'] = f'Bearer {token}'
            payload = {
                'model': model,
                'messages': [{'role': 'system', 'content': SYSTEM},
                              {'role': 'user', 'content': prompt}],
                'stream': True, 'temperature': 0.7, 'stop': STOP,
            }
        else:  # gemini
            endpoint = f"{endpoint}models/{model}:streamGenerateContent?alt=sse&key={token}"
            payload = {
                'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'systemInstruction': {'parts': [{'text': SYSTEM}]},
                'generationConfig': {'temperature': 0.7, 'stopSequences': STOP},
            }

        ai_text = ""
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(endpoint, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        return None, f"API {resp.status}: {body[:300]}"
                    buf = ""
                    async for chunk in resp.content.iter_any():
                        buf += chunk.decode('utf-8', errors='replace')
                        lines = buf.split('\n')
                        buf = lines.pop()
                        for line in lines:
                            if not line.startswith('data: '): continue
                            ds = line[6:].strip()
                            if ds == '[DONE]': continue
                            try: d = json.loads(ds)
                            except: continue
                            t = ''
                            if fmt == 'anthropic':
                                if d.get('type') == 'content_block_delta':
                                    t = d['delta'].get('text', '')
                            elif fmt == 'openai':
                                t = d.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            else:
                                for p in d.get('candidates', [{}])[0].get('content', {}).get('parts', []):
                                    if not p.get('thought'): t += p.get('text', '')
                            if t:
                                ai_text += t
                                await on_token(t)
        except Exception as e:
            return None, str(e)

        self.append_ai(ai_text)
        return ai_text, None

# ── App ───────────────────────────────────────────────────────────────────────

class GenesisTTY(App):
    CSS = """
    Screen { background: #0d0d0d; }

    #tty-section  { height: 45%; border-bottom: solid #1a3a1a; }
    #tty-header   { background: #0a2a0a; color: #33aa33; height: 1; padding: 0 1; }
    #tty-section:focus-within #tty-header { background: #1a5a1a; color: #88ff88; }

    #chat-section { height: 1fr; }
    #chat-header  { background: #0a1a2a; color: #3388cc; height: 1; padding: 0 1; }
    #chat         { height: 1fr; background: #0d0d0d; padding: 0 1; }
    #stream       { height: auto; min-height: 1; color: #00cc44; padding: 0 1; }
    #ai-input     { height: 3; border-top: solid #222; background: #111; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="tty-section"):
            yield Static(
                f"  TTY — {DEVICE}  [click to focus · Ctrl+Q quit]",
                id="tty-header"
            )
            yield PTYWidget(PTYShell())
        with Vertical(id="chat-section"):
            yield Static("  Chat", id="chat-header")
            yield RichLog(id="chat", highlight=False, markup=False, wrap=True)
            yield Static("", id="stream")
            yield Input(placeholder="> message to AI", id="ai-input")

    async def on_mount(self):
        self.pty_widget = self.query_one(PTYWidget)
        self.chat_log   = self.query_one("#chat", RichLog)
        self.stream_out = self.query_one("#stream", Static)
        self.ai_inp     = self.query_one("#ai-input", Input)

        cfg = load_config()
        if not cfg:
            self.chat_log.write(Text(
                "No API key found.\nSet ANTHROPIC_API_KEY or OPENAI_API_KEY.", style="red"))
            return

        self.brain = Brain(cfg)
        self.chat_log.write(Text(
            f"Genesis TTY  ·  {cfg['model']}  ·  Ctrl+Q quit\n"
            f"Click TTY panel to type shell commands.  Click Chat to talk to AI.",
            style="yellow"
        ))
        await self.pty_widget.shell.start()
        self.ai_inp.focus()

    def action_quit(self) -> None:
        # Textual's default ctrl+c calls this. If PTY is focused, send ^C there.
        # Otherwise actually quit.
        if isinstance(self.focused, PTYWidget):
            self.focused.shell.write(b"\x03")
        else:
            self.exit()

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return
        self.ai_inp.value = ""
        self.chat_log.write(Text(f"\n> {text}", style="bold white"))
        self.chat_log.scroll_end(animate=False)
        self.run_ai(text)

    @work(exclusive=True)
    async def run_ai(self, user_input: str):
        if not hasattr(self, 'brain'):
            return
        self.brain.perceive(user_input)

        while True:
            ai_text, err = await self._stream_infer()
            if err:
                self.chat_log.write(Text(f"[error] {err}", style="red"))
                break
            if not ai_text:
                break
            await self._act(ai_text)
            last_sc  = ai_text.rfind('/self_continue')
            last_cfh = ai_text.rfind('/call_for_human')
            if last_sc == -1 or last_cfh > last_sc:
                break

    async def _stream_infer(self):
        await asyncio.sleep(0.5)  # let TTY settle before snapshot
        snapshot = self.pty_widget.shell.snapshot()

        buf = ""
        async def on_token(t: str):
            nonlocal buf
            buf += t
            lines = buf.split("\n")
            tail = "\n".join(lines[-20:])  # show last 20 lines to prevent overflow
            self.stream_out.update(Text(tail, style="green"))

        ai_text, err = await self.brain.infer(on_token, realtime=snapshot)
        self.stream_out.update("")
        if ai_text:
            self.chat_log.write(Text(ai_text.rstrip(), style="green"))
            self.chat_log.scroll_end(animate=False)
        return ai_text, err

    async def _act(self, B: str):
        tasks = []
        # /shell exec — run command, capture stdout
        for m in re.finditer(r'^/shell exec (\S+)\n```[^\n]*\n([\s\S]*?)```', B, re.MULTILINE):
            dev, cmd = m.group(1), m.group(2).strip()
            if dev == DEVICE or dev == 'local':
                tasks.append(self.pty_widget.shell.exec_and_wait(cmd))
            else:
                self.chat_log.write(Text(f"[remote '{dev}' not available]", style="yellow"))

        # /shell key — send keyboard input directly to PTY
        for m in re.finditer(r'^/shell key (\S+)\n([\s\S]*?)(?=\n/|\Z)', B, re.MULTILINE):
            dev, keys = m.group(1), m.group(2).rstrip('\n')
            if dev == DEVICE or dev == 'local':
                self.pty_widget.shell.send_keys(keys)

        if tasks:
            results = await asyncio.gather(*tasks)
            for result in results:
                if result:
                    self.brain.consciousness += f"System - [Shell][{DEVICE}] - Result:\n```\n{result}\n```\n\n"


if __name__ == '__main__':
    GenesisTTY().run()
