"""
Infero Device Relay Server
- HTTP (port 8080): pairing endpoints + bash script serving
- WebSocket (port 8081): browser <-> device relay
- Tokens persisted to tokens.json (survives restarts)
"""

import asyncio
import base64
import json
import os
import secrets
import time
from datetime import datetime

import websockets
from aiohttp import web

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ─── In-memory state ───────────────────────────────────────────────────────────

pending_pairs = {}   # code -> {key_b64, instance_id, expires}
browser_conns = {}   # instance_id -> list[websocket]
device_conns  = {}   # "{instance_id}:{device_name}" -> {ws, instance_id, device_name}
device_tokens = {}   # token -> "{instance_id}:{device_name}"

TOKENS_FILE = os.path.join(os.path.dirname(__file__), 'tokens.json')

def load_tokens():
    try:
        with open(TOKENS_FILE) as f:
            device_tokens.update(json.load(f))
        print(f"[{ts()}] [relay] Loaded {len(device_tokens)} tokens from {TOKENS_FILE}")
    except FileNotFoundError:
        pass

def save_tokens():
    with open(TOKENS_FILE, 'w') as f:
        json.dump(device_tokens, f)

async def broadcast_to_instance(instance_id, msg_raw, exclude_ws=None):
    """Send to all online nodes in this instance, excluding sender."""
    for ws in browser_conns.get(instance_id, []):
        if ws != exclude_ws:
            try: await ws.send(msg_raw)
            except Exception: pass
    for key, info in device_conns.items():
        if info['instance_id'] == instance_id and info['ws'] != exclude_ws:
            try: await info['ws'].send(msg_raw)
            except Exception: pass

async def send_to_device(instance_id, device_name, msg_raw):
    """Send to a specific device by name."""
    target = device_conns.get(f"{instance_id}:{device_name}")
    if target:
        try: await target['ws'].send(msg_raw)
        except Exception: pass

async def send_to_browsers(instance_id, msg_raw, exclude_ws=None):
    """Send to all browsers in this instance."""
    for ws in browser_conns.get(instance_id, []):
        if ws != exclude_ws:
            try: await ws.send(msg_raw)
            except Exception: pass

# ─── Bash + Python script template ─────────────────────────────────────────────

AGENT_PY = r'''
import asyncio, json, subprocess, base64, os, sys, socket, re
from datetime import datetime
import aiohttp

INFERO_DIR = os.environ.get('INFERO_DIR', os.path.dirname(os.path.abspath(__file__)))
INSTANCES_FILE = os.path.join(INFERO_DIR, 'instances.json')

def _get_device_name():
    id_file = os.path.join(INFERO_DIR, 'device_id')
    try:
        suffix = open(id_file).read().strip()
    except FileNotFoundError:
        import random, string
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        os.makedirs(INFERO_DIR, exist_ok=True)
        open(id_file, 'w').write(suffix)
    return socket.gethostname().removesuffix('.local') + '-' + suffix

DEVICE_NAME = _get_device_name()

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_log_file(relay_ws):
    """Return log file path based on relay environment."""
    if 'dev.' in relay_ws:
        log_dir = os.path.expanduser('~/.infero-dev')
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, 'agent.log')
    return None  # prod: stdout only (captured by launchd)

def log(relay_ws, msg):
    """Log to stdout and optionally to env-specific log file."""
    print(msg)
    log_file = get_log_file(relay_ws)
    if log_file:
        with open(log_file, 'a') as f:
            f.write(msg + '\n')

def load_instances():
    try:
        return json.load(open(INSTANCES_FILE))
    except:
        return []

def save_instances(instances):
    json.dump(instances, open(INSTANCES_FILE, 'w'), indent=2)

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import websockets

def make_cipher(key_b64):
    pad = 4 - len(key_b64) % 4
    if pad != 4: key_b64 += '=' * pad
    return AESGCM(base64.urlsafe_b64decode(key_b64))

def encrypt(cipher, d):
    iv = os.urandom(12)
    ct = cipher.encrypt(iv, json.dumps(d).encode(), None)
    return base64.b64encode(iv + ct).decode()

def decrypt(cipher, b64):
    raw = base64.b64decode(b64)
    return json.loads(cipher.decrypt(raw[:12], raw[12:], None))

# ─── Genesis Worker: distributed loop ─────────────────────────────────────────

class GenesisWorker:
    def __init__(self, ws, cipher, iid, relay_ws=''):
        self.ws = ws
        self.cipher = cipher
        self.iid = iid
        self.relay_ws = relay_ws
        self.consciousness = ""
        self.metadata = {}
        self.llm_settings = {}  # model, provider, token, format, thinking, endpoint
        self.running = False
        self.pending_user_input = None
        self._stopped_sent = False
        self._pending_exec = {}  # req_id -> asyncio.Future
        self.devices = {}  # name -> {type, online}
        self.being_id = ''

    def _being_dir(self):
        if not self.being_id:
            return None
        d = os.path.join(INFERO_DIR, 'beings', self.being_id)
        os.makedirs(d, exist_ok=True)
        return d

    def save_to_disk(self):
        d = self._being_dir()
        if not d:
            return
        with open(os.path.join(d, 'consciousness.txt'), 'w', encoding='utf-8') as f:
            f.write(self.consciousness)
        with open(os.path.join(d, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        self._log(f"[{ts()}] [infero] Saved being {self.being_id}: consciousness={len(self.consciousness)} chars")

    def load_from_disk(self):
        d = self._being_dir()
        if not d:
            return False
        c_path = os.path.join(d, 'consciousness.txt')
        m_path = os.path.join(d, 'metadata.json')
        if not os.path.exists(c_path):
            return False
        with open(c_path, 'r', encoding='utf-8') as f:
            self.consciousness = f.read()
        if os.path.exists(m_path):
            with open(m_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        self._log(f"[{ts()}] [infero] Loaded being {self.being_id} from disk: consciousness={len(self.consciousness)} chars")
        return True

    def _log(self, msg):
        log(self.relay_ws, msg)

    async def send_relay(self, msg):
        try:
            await self.ws.send(json.dumps(msg))
        except Exception:
            pass

    def _read_core_mem(self, max_chars=20000):  # ~5k tokens
        if not self.being_id: return ''
        cm_path = os.path.join(INFERO_DIR, 'beings', self.being_id, 'core_mem.md')
        try:
            with open(cm_path, encoding='utf-8') as f: content = f.read()
            if len(content) > max_chars:
                return content[:max_chars] + f"\n\n[⚠️ core_mem truncated to {max_chars} chars. Full long_mem: {len(content)} chars]"
            return content
        except: return ''

    async def on_loop_handoff(self, payload_enc):
        data = decrypt(self.cipher, payload_enc)
        self.consciousness = data.get('consciousness', '')
        self.metadata = data.get('metadata', {})
        self.being_id = self.metadata.get('beingId', '')
        core_mem = self.metadata.get('coreMem', '')
        if core_mem and self.being_id:
            import os
            cm_path = os.path.join(INFERO_DIR, 'beings', self.being_id, 'core_mem.md')
            os.makedirs(os.path.dirname(cm_path), exist_ok=True)
            with open(cm_path, 'w', encoding='utf-8') as f: f.write(core_mem)
        self.llm_settings = data.get('settings', {})
        self.devices = data.get('devices', {})
        loop_was_running = data.get('loopWasRunning', False)
        self.running = True
        self._stopped_sent = False
        self.save_to_disk()
        self._log(f"[{ts()}] [infero] Loop handoff received. consciousness={len(self.consciousness)} chars, model={self.llm_settings.get('model')}, loopWasRunning={loop_was_running}")
        await self.send_relay({'type': 'loop_status', 'status': 'started', 'device_name': DEVICE_NAME, 'being_id': self.being_id})
        try:
            await self.run_loop(loop_was_running)
        except Exception as e:
            self._log(f"[{ts()}] [infero] Loop error: {e}")
        finally:
            self.running = False
            self.save_to_disk()
            if not self._stopped_sent:
                self._stopped_sent = True
                await self.send_relay({'type': 'loop_status', 'status': 'stopped',
                    'device_name': DEVICE_NAME, 'being_id': self.being_id,
                    'payload': encrypt(self.cipher, {'consciousness': self.consciousness, 'metadata': {**self.metadata, 'coreMem': self._read_core_mem()}})})
                self._log(f"[{ts()}] [infero] Loop stopped. consciousness={len(self.consciousness)} chars")

    async def run_loop(self, loop_was_running=False):
        """Keep looping: run loop(), wait for user input if stopped, repeat until loop_stop."""
        last_sc = self.consciousness.rfind('/self_continue')
        last_cfh = self.consciousness.rfind('/call_for_human')
        should_auto_run = loop_was_running and last_sc > last_cfh
        self._log(f"[{ts()}] [infero] run_loop: loopWasRunning={loop_was_running}, last_sc={last_sc}, last_cfh={last_cfh}, should_auto_run={should_auto_run}, pending_input={bool(self.pending_user_input)}, running={self.running}")
        if not should_auto_run and not self.pending_user_input:
            self._log(f"[{ts()}] [infero] run_loop: waiting for user input...")
            while self.running and not self.pending_user_input:
                await asyncio.sleep(0.5)
            self._log(f"[{ts()}] [infero] run_loop: wait ended. running={self.running}, pending_input={bool(self.pending_user_input)}")
        while self.running:
            self._log(f"[{ts()}] [infero] run_loop: entering loop(). pending_input={bool(self.pending_user_input)}")
            await self.loop()
            if not self.running:
                self._log(f"[{ts()}] [infero] run_loop: self.running=False after loop(), breaking")
                break
            self._log(f"[{ts()}] [infero] run_loop: loop() returned, waiting for user input...")
            while self.running and not self.pending_user_input:
                await asyncio.sleep(0.5)

    async def loop(self):
        if not self.pending_user_input and '/call_for_human' in self.consciousness:
            last_sc = self.consciousness.rfind('/self_continue')
            last_cfh = self.consciousness.rfind('/call_for_human')
            if last_cfh > last_sc:
                self._log(f"[{ts()}] [infero] loop(): /call_for_human at end, returning immediately")
                return

        while self.running:
            await self.perceive()
            B = await self.infer()
            if B is None:
                break
            await self.act(B)
            self.save_to_disk()
            last_sc = B.rfind('/self_continue')
            last_cfh = B.rfind('/call_for_human')
            cont = last_sc > last_cfh or bool(self.pending_user_input)
            if not cont:
                break

    def _build_realtime(self):
        lines = ''
        # Self (this device, the current loop host)
        lines += f'\n  - {DEVICE_NAME}(online, shell) [core loop host]'
        lines += '\n    - Core loop (read or modify with caution):'
        lines += '\n      async def loop(): await perceive(); B = await infer(); await act(B); if /self_continue in B: repeat; if /call_for_human: wait for input'
        lines += f'\n    - Being ID: {self.being_id}'
        lines += f'\n    - Memory: {INFERO_DIR}/beings/{self.being_id}/ — consciousness.txt (auto-saved, field: value), metadata.json, arbitrary files'
        lines += '\n    - Capabilities: persistent processes, file I/O, system access, any language/runtime'
        lines += f'\n    - Exec (MUST use this exact format — wrong format = code never executed):\n/shell exec {DEVICE_NAME}\n```bash\n<command>\n```'
        lines += '\n      (Runs via asyncio.create_subprocess_shell. Timeout: 30s hard kill. For long tasks use nohup or & to detach, e.g. nohup python train.py > /tmp/out.log 2>&1 &; check results later via log files. Success/failure/timeout does NOT interrupt your inference loop.)'
        # Other devices
        for name, info in self.devices.items():
            if name == DEVICE_NAME:
                continue
            if not info.get('online'):
                continue
            dtype = info.get('type', 'shell')
            if dtype == 'browser':
                lines += f'\n  - {name}(online, browser)'
                lines += '\n    - UI: .right-panel #canvas-container > #html-div (living UI, auto-saved) + #main-canvas'
                lines += '\n         .left-panel #chat-box + #input + #send-btn'
                lines += '\n    - Memory: IndexedDB(\'GenesisDB\', store=\'beings\', keyPath=\'id\')'
                lines += '\n    - Capabilities: DOM/UI, canvas/WebGL, fetch, IndexedDB, FileSystem API, Pyodide, WASM, Speech (neural TTS APIs preferred; WebSpeech as fallback), MediaDevices(camera, mic)'
                lines += '\n    - Exec (MUST use this exact format — wrong format = code displayed as text, never executed):\n/browser exec\n```javascript\n// your code here\n// CRITICAL for canvas: never set canvas.width/height; use const { width: w, height: h } = document.getElementById(\'canvas-container\').getBoundingClientRect();\n// return value — use for immediate results (sync or async)\n// trigger(value) — use for deferred wakeup\n```'
            else:
                lines += f'\n  - {name}(online, {dtype})'
                lines += '\n    - Capabilities: persistent processes, file I/O, system access, any language/runtime'
                lines += f'\n    - Exec: /shell exec {name}\n```bash\n<command>\n```'
                lines += '\n      (Runs via asyncio.create_subprocess_shell. Timeout: 30s hard kill. For long tasks use nohup or & to detach.)'
        return f'[Realtime]\nDevices:{lines}'

    async def perceive(self):
        now = datetime.now()
        days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
        tz_offset = now.astimezone().strftime('%z')
        env = f"[System Environment]\nTime: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC{tz_offset})\nDay: {days[now.weekday()]}\nReminder: end with /self_continue or /call_for_human"
        realtime = self._build_realtime()
        # Build the full prompt context (env + realtime + user_input)
        # but only persist env + user_input to consciousness (not realtime)
        user_input = self.pending_user_input
        if user_input:
            self.pending_user_input = None
        if user_input == '__go__':
            user_input = None  # empty Go — just trigger loop, no text
        # What gets persisted to consciousness.txt (no [Realtime])
        persist_parts = [env]
        if user_input:
            persist_parts.append(user_input)
        self.consciousness += '\n\n'.join(persist_parts) + '\n\n'
        # Store realtime separately for infer() to use
        self._last_realtime = realtime

    async def infer(self):
        fmt = self.llm_settings.get('format', 'openai')
        model = self.llm_settings.get('model', '')
        endpoint = self.llm_settings.get('endpoint', '')
        api_token = self.llm_settings.get('token', '')
        thinking = self.llm_settings.get('thinking', False)
        system_prompt = self.llm_settings.get('system_prompt', '')

        client_id = self.llm_settings.get('client_id', '')
        headers = {'Content-Type': 'application/json'}
        if client_id:
            headers['X-Client-ID'] = client_id
        if fmt == 'anthropic':
            headers['x-api-key'] = api_token
            headers['anthropic-version'] = '2023-06-01'
        elif fmt == 'openai':
            headers['Authorization'] = f'Bearer {api_token}'
        # Gemini uses query param

        payload = self._build_payload(fmt, model, system_prompt, thinking)
        if fmt == 'gemini':
            # Standard Gemini API: endpoint ends with /v1beta/ — append models/{model}:stream...
            # Infero proxy: endpoint is a full URL (e.g. /api/relay) — use as-is
            if endpoint.endswith('/'):
                url = f"{endpoint}models/{model}:streamGenerateContent?alt=sse&key={api_token}"
            else:
                url = endpoint  # infero proxy, POST directly
        else:
            url = endpoint

        ai_text = ""
        thinking_text = ""
        _last_ai_len = 0
        _last_think_len = 0
        usage = {}  # {promptTokens, cachedTokens, outputTokens}
        try:
            async with aiohttp.ClientSession(auto_decompress=False) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status >= 400:
                        err_body = await resp.text()
                        self._log(f"\n[{ts()}] [infero] Infer HTTP {resp.status}: {err_body[:500]}")
                        self.consciousness += f"System - [Error] HTTP {resp.status}: {err_body[:200]}\n\n"
                        return None
                    buffer = ""
                    async for chunk in resp.content.iter_any():
                        buffer += chunk.decode('utf-8', errors='replace')
                        lines = buffer.split('\n')
                        buffer = lines.pop()
                        for line in lines:
                            if not line.startswith('data: '): continue
                            data_str = line[6:].strip()
                            if data_str == '[DONE]': continue
                            try:
                                data = json.loads(data_str)
                            except: continue

                            if fmt == 'anthropic':
                                if data.get('type') == 'content_block_delta':
                                    delta = data.get('delta', {})
                                    if delta.get('type') == 'thinking_delta':
                                        thinking_text += delta.get('thinking', '')
                                    elif delta.get('type') == 'text_delta':
                                        ai_text += delta.get('text', '')
                                if data.get('type') == 'message_start':
                                    u = data.get('message', {}).get('usage', {})
                                    if u:
                                        usage = {'promptTokens': u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0),
                                                 'cachedTokens': u.get('cache_read_input_tokens', 0)}
                                if data.get('type') == 'message_delta':
                                    u = data.get('usage', {})
                                    if u: usage['outputTokens'] = u.get('output_tokens', 0)
                            elif fmt == 'openai':
                                delta = data.get('choices', [{}])[0].get('delta', {})
                                if delta.get('content'): ai_text += delta['content']
                                if delta.get('reasoning_content'): thinking_text += delta['reasoning_content']
                                if data.get('usage'):
                                    usage = {'promptTokens': data['usage'].get('prompt_tokens', 0), 'outputTokens': data['usage'].get('completion_tokens', 0)}
                            else:  # gemini
                                cands = data.get('candidates', [])
                                if cands:
                                    for part in cands[0].get('content', {}).get('parts', []):
                                        if part.get('thought'): thinking_text += part.get('text', '')
                                        else: ai_text += part.get('text', '')
                                if data.get('usageMetadata'):
                                    u = data['usageMetadata']
                                    usage = {'promptTokens': u.get('promptTokenCount', 0), 'cachedTokens': u.get('cachedContentTokenCount', 0), 'outputTokens': u.get('candidatesTokenCount', 0)}

                            # Broadcast token delta
                            td = thinking_text[_last_think_len:]
                            ad = ai_text[_last_ai_len:]
                            if ad or td:
                                await self.send_relay({'type': 'stream_token', 'text_delta': ad, 'thinking_delta': td, 'being_id': self.being_id})
                                _last_ai_len = len(ai_text)
                                _last_think_len = len(thinking_text)
                        # Print latest token to terminal
                        sys.stdout.write(f"\r[infer] {len(ai_text)} chars...")
                        sys.stdout.flush()
        except Exception as e:
            self._log(f"\n[{ts()}] [infero] Infer error: {e}")
            self.consciousness += f"System - [Error] {e}\n\n"
            return None

        self._log(f"\n[{ts()}] [infero] Infer done: {len(ai_text)} chars")
        # Signal stream done
        await self.send_relay({'type': 'stream_token', 'text': ai_text, 'thinking': thinking_text, 'done': True, 'usage': usage, 'being_id': self.being_id})
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.consciousness += f"**Digital Being - [{time_str}]**\n{ai_text}\n\n"
        return ai_text

    def _build_payload(self, fmt, model, system_prompt, thinking):
        # Inject [Realtime] dynamically into the prompt (not persisted)
        realtime = getattr(self, '_last_realtime', '')
        cm = self._read_core_mem()
        core_mem_text = (f"=== CORE MEMORY( in {os.path.join(INFERO_DIR, 'beings', self.being_id, 'core_mem.md')}) ===\n" + cm +
                         "\n\n[Architecture Note]\n"
                         "context = SYS + first 10% ctx_old + last 60% old + core_mem + realtime\n"
                         "⚠️ ATTENTION: Middle old memory in consciousness stream will be compressed/cut in maybeCompressConsciousness() when tokens exceed LIMIT (default ~2/3 of model max context, e.g., 300k). \n"
                         "You MUST save your important notes, protocols, or skills in this core_mem.md (or other persistent shell files) to prevent them from being forgotten.\n"
                         "===================\n\n") if cm else ""
        consciousness = self.consciousness + core_mem_text + (realtime + '\n\n' if realtime else '')
        stop = ['\nSystem - [Browser]', '\nSystem - [Shell]', '\n[System Environment]']

        if fmt == 'anthropic':
            payload = {
                'model': model,
                'system': system_prompt,
                'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': consciousness}]}],
                'max_tokens': 8192,
                'stream': True,
                'stop_sequences': stop
            }
            if thinking:
                payload['thinking'] = {'type': 'enabled', 'budget_tokens': 10000}
                payload['temperature'] = 1
                payload['max_tokens'] = 16000
            else:
                payload['temperature'] = 0.7
            return payload

        if fmt == 'openai':
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': [{'type': 'text', 'text': consciousness}]}
                ],
                'stream': True,
                'temperature': 0.7,
                'stop': stop
            }
            if thinking:
                payload['temperature'] = 1
            return payload

        # gemini
        cache_name = self.metadata.get('cacheName')
        cached_length = self.metadata.get('cachedLength', 0)
        buffer_text = consciousness[cached_length:] if cache_name else consciousness
        gemini_config = {
            'temperature': 0.7,
            'thinkingConfig': {'includeThoughts': True},
            'stopSequences': ['\nSystem - [Browser]', '\n[System Environment]']
        }
        contents = [{'role': 'user', 'parts': [{'text': buffer_text}]}]
        if cache_name:
            return {
                'cachedContent': cache_name,
                'contents': contents,
                'generationConfig': gemini_config
            }
        return {
            'contents': contents,
            'systemInstruction': {'parts': [{'text': system_prompt}]},
            'generationConfig': gemini_config
        }

    async def act(self, B_out):
        if not B_out: return
        tasks = []
        # Parse /browser exec blocks
        for m in re.finditer(r'^/browser exec\n```(?:javascript|js)?\n([\s\S]*?)```', B_out, re.MULTILINE):
            tasks.append(self._exec_browser(m.group(1).strip()))
        # Parse /shell exec blocks
        for m in re.finditer(r'^/shell exec (\S+)\n```[^\n]*\n([\s\S]*?)```', B_out, re.MULTILINE):
            device_name, cmd = m.group(1), m.group(2).strip()
            if device_name == DEVICE_NAME:
                tasks.append(self._exec_local_shell(cmd))
            elif device_name not in self.devices:
                self.consciousness += f"System - [Shell][{device_name}] - Skipped: device is hidden or unknown\n\n"
            else:
                tasks.append(self._exec_remote_shell(device_name, cmd))
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    r = f"System - [Error] {r}\n\n"
                if r:
                    self.consciousness += r

    async def _exec_local_shell(self, cmd):
        self._log(f"[{ts()}] [infero] shell exec (local): {cmd[:60]}")
        try:
            proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                out = ''
                if stdout: out += f"[stdout]\n{stdout.decode()}"
                if stderr: out += f"[stderr]\n{stderr.decode()}"
                out += f"[exit_code] {proc.returncode}"
            except asyncio.TimeoutError:
                proc.kill()
                out = "[stderr]\nTimed out (30s)\n[exit_code] -1"
        except Exception as e:
            out = f"[Shell Error]\n{e}"
        sysMsg = f"System - [Shell][{DEVICE_NAME}] - Result:\n```text\n{out.strip()}\n```\n\n"
        await self.send_relay({'type': 'exec_display', 'being_id': self.being_id, 'text': sysMsg})
        return sysMsg

    async def _exec_remote_shell(self, device_name, cmd):
        self._log(f"[{ts()}] [infero] shell exec (remote → {device_name}): {cmd[:60]}")
        req_id = base64.urlsafe_b64encode(os.urandom(12)).decode()
        payload = encrypt(self.cipher, {'cmd': cmd})
        fut = asyncio.get_running_loop().create_future()
        self._pending_exec[req_id] = fut
        await self.send_relay({'type': 'exec', 'req_id': req_id, 'device_name': device_name, 'payload': payload})
        try:
            result = await asyncio.wait_for(fut, timeout=35)
            data = decrypt(self.cipher, result)
            out = ''
            if data.get('stdout'): out += f"[stdout]\n{data['stdout']}"
            if data.get('stderr'): out += f"[stderr]\n{data['stderr']}"
            out += f"[exit_code] {data.get('exit_code', -1)}"
        except asyncio.TimeoutError:
            out = "[Shell Error]\nRemote exec timed out (35s)"
        except Exception as e:
            out = f"[Shell Error]\n{e}"
        self._pending_exec.pop(req_id, None)
        sysMsg = f"System - [Shell][{device_name}] - Result:\n```text\n{out.strip()}\n```\n\n"
        await self.send_relay({'type': 'exec_display', 'being_id': self.being_id, 'text': sysMsg})
        return sysMsg

    async def _exec_browser(self, code):
        self._log(f"[{ts()}] [infero] browser exec (remote): {code[:60]}")
        req_id = base64.urlsafe_b64encode(os.urandom(12)).decode()
        fut = asyncio.get_running_loop().create_future()
        self._pending_exec[req_id] = fut
        await self.send_relay({'type': 'browser_exec_request', 'req_id': req_id, 'code': code, 'being_id': self.being_id})
        try:
            result = await asyncio.wait_for(fut, timeout=20)
        except asyncio.TimeoutError:
            result = "[Browser Exec Error]\nNo browser responded (20s timeout)"
        except Exception as e:
            result = f"[Browser Exec Error]\n{e}"
        self._pending_exec.pop(req_id, None)
        return f"System - [Browser] - Result:\n```text\n{result}\n```\n\n"

    def on_exec_result(self, msg):
        """Handle result messages for pending remote exec requests."""
        req_id = msg.get('req_id')
        fut = self._pending_exec.get(req_id)
        if fut and not fut.done():
            fut.set_result(msg.get('payload') or msg.get('result', ''))

    def on_browser_exec_result(self, msg):
        req_id = msg.get('req_id')
        fut = self._pending_exec.get(req_id)
        if fut and not fut.done():
            fut.set_result(msg.get('result', ''))

    def on_user_input(self, msg):
        text = msg.get('text', '')
        self.pending_user_input = text if text else '__go__'  # empty Go → truthy sentinel
        self._log(f"[{ts()}] [infero] User input received: {self.pending_user_input[:40]}...")

    async def on_loop_stop(self):
        self._log(f"[{ts()}] [infero] Loop stop requested")
        self.running = False
        self.save_to_disk()
        if not self._stopped_sent:
            self._stopped_sent = True
            await self.send_relay({'type': 'loop_status', 'status': 'stopped',
                'device_name': DEVICE_NAME, 'being_id': self.being_id,
                'payload': encrypt(self.cipher, {'consciousness': self.consciousness, 'metadata': self.metadata})})
            self._log(f"[{ts()}] [infero] Loop stopped. consciousness={len(self.consciousness)} chars")

# ─── Connection handler ───────────────────────────────────────────────────────

async def connect_instance(cfg):
    cipher = make_cipher(cfg['key'])
    backoff = 1
    iid = cfg['instance_id'][:8]
    while True:
        try:
            async with websockets.connect(cfg['relay_ws']) as ws:
                backoff = 1
                await ws.send(json.dumps({
                    "type": "device_hello",
                    "instance_id": cfg['instance_id'],
                    "token": cfg['token'],
                    "device_name": DEVICE_NAME,
                    "device_type": "shell"
                }))
                log(cfg['relay_ws'], f"[{ts()}] [infero] Connected: {DEVICE_NAME} → {iid}...")
                async def handle_exec(req_id, payload_raw):
                    try:
                        cmd = decrypt(cipher, payload_raw)['cmd']
                        log(cfg['relay_ws'], f"[{ts()}] [infero] exec ({iid}): {cmd[:60]}")
                        proc = await asyncio.create_subprocess_shell(
                            cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        try:
                            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                            payload = encrypt(cipher, {"stdout": stdout.decode(), "stderr": stderr.decode(), "exit_code": proc.returncode})
                        except asyncio.TimeoutError:
                            proc.kill()
                            payload = encrypt(cipher, {"stdout": "", "stderr": "Timed out (30s)", "exit_code": -1})
                    except Exception as e:
                        payload = encrypt(cipher, {"stdout": "", "stderr": str(e), "exit_code": -1})
                    await ws.send(json.dumps({"type": "result", "req_id": req_id, "payload": payload}))

                workers = {}  # being_id -> GenesisWorker

                def get_worker(being_id):
                    if being_id and being_id not in workers:
                        workers[being_id] = GenesisWorker(ws, cipher, iid, cfg['relay_ws'])
                    return workers.get(being_id)

                async for raw in ws:
                    msg = json.loads(raw)
                    mtype = msg.get('type', '')
                    being_id = msg.get('being_id', '__default__')
                    if mtype == 'exec':
                        asyncio.create_task(handle_exec(msg['req_id'], msg['payload']))
                    elif mtype == 'loop_handoff':
                        w = get_worker(being_id)
                        log(cfg['relay_ws'], f"[{ts()}] [infero] MSG loop_handoff for being={being_id}, worker={w is not None}")
                        asyncio.create_task(w.on_loop_handoff(msg.get('payload', '')))
                    elif mtype == 'loop_stop':
                        w = workers.get(being_id)
                        log(cfg['relay_ws'], f"[{ts()}] [infero] MSG loop_stop for being={being_id}, worker={w is not None}")
                        if w:
                            await w.on_loop_stop()
                        else:
                            await ws.send(json.dumps({'type': 'loop_status', 'status': 'stopped',
                                'device_name': DEVICE_NAME, 'payload': None}))
                    elif mtype == 'user_input':
                        w = workers.get(being_id)
                        log(cfg['relay_ws'], f"[{ts()}] [infero] MSG user_input for being={being_id}, worker={w is not None}, text={msg.get('text','')[:30]}")
                        if w: w.on_user_input(msg)
                    elif mtype == 'result':
                        for w in workers.values():
                            w.on_exec_result(msg)
                    elif mtype == 'browser_exec_result':
                        for w in workers.values():
                            w.on_browser_exec_result(msg)
                    elif mtype == 'consciousness_sync' and msg.get('action') == 'request':
                        w = workers.get(being_id)
                        log(cfg['relay_ws'], f"[{ts()}] [infero] MSG consciousness_sync request for being={being_id}, worker={w is not None}")
                        if w and w.consciousness:
                            try:
                                resp_payload = encrypt(cipher, {
                                    'consciousness': w.consciousness,
                                    'metadata': w.metadata
                                })
                                await ws.send(json.dumps({
                                    'type': 'consciousness_sync',
                                    'action': 'response',
                                    'device_name': DEVICE_NAME,
                                    'being_id': being_id,
                                    'payload': resp_payload
                                }))
                                log(cfg['relay_ws'], f"[{ts()}] [infero] consciousness_sync response sent: {len(w.consciousness)} chars")
                            except Exception as e:
                                log(cfg['relay_ws'], f"[{ts()}] [infero] consciousness_sync error: {e}")
                        else:
                            log(cfg['relay_ws'], f"[{ts()}] [infero] consciousness_sync: no worker or empty consciousness")
                    elif mtype == 'settings_update':
                        new_settings = msg.get('settings', {})
                        for w in workers.values():
                            w.llm_settings.update(new_settings)
                        log(cfg['relay_ws'], f"[{ts()}] [infero] settings_update: model={new_settings.get('model','?')}")
                    elif mtype == 'device_status':
                        name = msg.get('device_name', '')
                        online = msg.get('online', False)
                        dtype = msg.get('device_type', 'shell')
                        if name:
                            if online:
                                for w in workers.values():
                                    w.devices[name] = {'type': dtype, 'online': True}
                            else:
                                for w in workers.values():
                                    w.devices.pop(name, None)
                            log(cfg['relay_ws'], f"[{ts()}] [infero] device_status: {name} {'online' if online else 'offline'}")
                    elif mtype == 'stream_token':
                        # Another node is streaming — print to terminal
                        text = msg.get('text', '')
                        sys.stdout.write(f"\r[stream] {len(text)} chars...")
                        sys.stdout.flush()
                        if msg.get('done'):
                            print(f"\n[{ts()}] [infero] Stream done from remote")
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code == 4002:
                log(cfg['relay_ws'], f"[{ts()}] [infero] Removed from {iid}. Stopping connection.")
                instances = [i for i in load_instances() if i['instance_id'] != cfg['instance_id']]
                save_instances(instances)
                return
            log(cfg['relay_ws'], f"[{ts()}] [infero] Disconnected from {iid} ({e.code}). Retry in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as e:
            log(cfg['relay_ws'], f"[{ts()}] [infero] Error ({iid}): {e}. Retry in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

async def main():
    instances = load_instances()
    if not instances:
        print(f"[{ts()}] [infero] No instances. Run: infero pair <CODE>")
        return
    print(f"[{ts()}] [infero] Starting agent — {len(instances)} instance(s), device: {DEVICE_NAME}")
    await asyncio.gather(*[connect_instance(c) for c in instances])

asyncio.run(main())
'''

DEVICE_SCRIPT_TEMPLATE = r"""#!/usr/bin/env bash
set -e

RELAY_WS="{RELAY_WS}"
RELAY_HTTP="{RELAY_HTTP}"
INSTANCE_ID="{INSTANCE_ID}"
TOKEN="{TOKEN}"
KEY="{KEY}"
CLIENT_NAME="{CLIENT_NAME}"

# Auto-detect dev vs prod based on relay URL
if echo "$RELAY_WS" | grep -q "dev\."; then
    INFERO_DIR="$HOME/.infero-dev"
    INFERO_CMD="infero-dev"
else
    INFERO_DIR="$HOME/.infero"
    INFERO_CMD="infero"
fi
VENV_DIR="$INFERO_DIR/venv"
AGENT="$INFERO_DIR/agent.py"
INSTANCES="$INFERO_DIR/instances.json"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$INFERO_DIR" "$BIN_DIR"

# ── Setup venv ───────────────────────────────────────────────────────────────
if [ ! -f "$VENV_DIR/bin/python3" ]; then
    echo "[infero] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -q cryptography websockets python-socks aiohttp
echo "[infero] Dependencies ready"

# ── Save agent.py ────────────────────────────────────────────────────────────
cat > "$AGENT" << 'ENDOFAGENT'
AGENT_PY_PLACEHOLDER
ENDOFAGENT

# ── Update instances.json (append or update this instance) ───────────────────
INSTANCE_ID="$INSTANCE_ID" TOKEN="$TOKEN" KEY="$KEY" RELAY_WS="$RELAY_WS" CLIENT_NAME="$CLIENT_NAME" INFERO_DIR="$INFERO_DIR" \
"$VENV_DIR/bin/python3" -c "
import json, os
from datetime import datetime
f = os.environ.get('INFERO_DIR', os.environ['HOME'] + '/.infero') + '/instances.json'
try: instances = json.load(open(f))
except: instances = []
iid = os.environ['INSTANCE_ID']
existing = next((i for i in instances if i.get('instance_id') == iid), None)
first_added = existing.get('first_added') if existing else datetime.now().strftime('%b %-d, %Y, %H:%M')
instances = [i for i in instances if i.get('instance_id') != iid]
instances.append({'instance_id': iid, 'token': os.environ['TOKEN'],
                  'key': os.environ['KEY'], 'relay_ws': os.environ['RELAY_WS'],
                  'client_name': os.environ['CLIENT_NAME'],
                  'first_added': first_added})
json.dump(instances, open(f, 'w'), indent=2)
"
echo "[infero] Instance saved"

# ── Install infero CLI ───────────────────────────────────────────────────────
cat > "$BIN_DIR/$INFERO_CMD" << ENDOFCLI
#!/usr/bin/env bash
# Determine env from script name
case "\$(basename "\$0")" in
    infero-dev) INFERO_DIR="\$HOME/.infero-dev"; INFERO_CMD="infero-dev" ;;
    *)          INFERO_DIR="\$HOME/.infero"; INFERO_CMD="infero" ;;
esac
VENV_DIR="\$INFERO_DIR/venv"
AGENT="\$INFERO_DIR/agent.py"
INSTANCES="\$INFERO_DIR/instances.json"
BIN_DIR="\$HOME/.local/bin"
case "$INFERO_CMD" in infero-dev) PLIST="\$HOME/Library/LaunchAgents/net.infero-dev.device.plist" ;; *) PLIST="\$HOME/Library/LaunchAgents/net.infero.device.plist" ;; esac
SERVICE="\$HOME/.config/systemd/user/\$INFERO_CMD-device.service"
RELAY_HTTP="$RELAY_HTTP"

_stop_agent() {
    pkill -f "\$AGENT" 2>/dev/null || true
    if [ -f "\$PLIST" ]; then launchctl unload "\$PLIST" 2>/dev/null || true; fi
    if [ -f "\$SERVICE" ]; then systemctl --user stop "\$INFERO_CMD-device" 2>/dev/null || true; fi
}

_restart_agent() {
    _stop_agent
    sleep 1
    if [ -f "\$PLIST" ]; then launchctl load "\$PLIST" 2>/dev/null || true
    elif [ -f "\$SERVICE" ]; then systemctl --user start "\$INFERO_CMD-device" 2>/dev/null || true
    else nohup "\$VENV_DIR/bin/python3" "\$AGENT" >> "\$INFERO_DIR/agent.log" 2>&1 & fi
}

case "\$1" in
  pair)
    if [ -z "\$2" ]; then echo "Usage: \$INFERO_CMD pair <CODE>"; exit 1; fi
    curl -fsSL "\$RELAY_HTTP/pair/\$2" | sh
    ;;
  list)
    if [ ! -f "\$INSTANCES" ]; then echo "No instances paired."; exit 0; fi
    INFERO_DIR="\$INFERO_DIR" "\$VENV_DIR/bin/python3" -c "
import json, os, socket
f = os.environ.get('INFERO_DIR', os.environ['HOME'] + '/.infero') + '/instances.json'
try: instances = json.load(open(f))
except: instances = []
if not instances: print('No instances paired.'); exit()
infero_dir = os.environ.get('INFERO_DIR', os.environ['HOME'] + '/.infero')
id_file = os.path.join(infero_dir, 'device_id')
try: suffix = open(id_file).read().strip()
except: suffix = ''
device_name = socket.gethostname().removesuffix('.local') + ('-' + suffix if suffix else '')
print(f'Device: {device_name}')
print(f'Paired ({len(instances)}):')
for i, c in enumerate(instances, 1):
    print(f'  [{i}]')
    print(f'    id         : {c[\"instance_id\"]}')
    print(f'    clientName : {c.get(\"client_name\", \"Unknown\")}')
    print(f'    first added: {c.get(\"first_added\", \"Unknown\")}')
"
    ;;
  remove)
    if [ ! -f "\$INSTANCES" ]; then echo "No instances paired."; exit 0; fi
    COUNT=\$("\$VENV_DIR/bin/python3" -c "import json; print(len(json.load(open('\$INSTANCES'))))" 2>/dev/null || echo 0)
    if [ "\$COUNT" -eq 0 ]; then
        echo "No instances paired."; exit 0
    elif [ "\$COUNT" -eq 1 ] || [ -n "\$2" ]; then
        TARGET="\$2"
        INFERO_DIR="\$INFERO_DIR" "\$VENV_DIR/bin/python3" -c "
import json, os, sys, asyncio, socket
f = os.environ.get('INFERO_DIR', os.environ['HOME'] + '/.infero') + '/instances.json'
instances = json.load(open(f))
target = sys.argv[1] if len(sys.argv) > 1 else None
if not target:
    to_remove = [instances[0]]
    instances = instances[1:]
else:
    to_remove = [i for i in instances if i['instance_id'].startswith(target)]
    instances = [i for i in instances if not i['instance_id'].startswith(target)]
if not to_remove:
    print(f'[infero] Instance not found: {target}'); sys.exit(1)

import websockets as ws
device_name = socket.gethostname().removesuffix('.local')

async def say_goodbye(cfg):
    try:
        async with ws.connect(cfg['relay_ws'], open_timeout=5) as sock:
            await sock.send(json.dumps({'type':'device_hello','instance_id':cfg['instance_id'],'token':cfg['token'],'device_name':device_name}))
            await sock.send(json.dumps({'type':'device_remove_self','device_name':device_name}))
            await asyncio.sleep(0.5)
    except Exception as e:
        print(f'[infero] Could not notify browser: {e}')

async def main():
    await asyncio.gather(*[say_goodbye(c) for c in to_remove])

asyncio.run(main())
json.dump(instances, open(f, 'w'), indent=2)
print(f'[infero] Removed {len(to_remove)} instance(s).')
if not instances: print('[infero] No instances left.')
" "\$TARGET"
        _restart_agent
    else
        echo "Multiple instances paired. Specify instance ID prefix:"
        "\$BIN_DIR/\$INFERO_CMD" list
        echo ""
        echo "  \$INFERO_CMD remove <instance_id>"
    fi
    ;;
  offline)
    _stop_agent
    echo "[infero] Device offline."
    ;;
  online)
    _restart_agent
    echo "[infero] Device online."
    ;;
  uninstall)
    _stop_agent
    rm -rf "\$INFERO_DIR"
    if [ -f "\$PLIST" ]; then launchctl unload "\$PLIST" 2>/dev/null; rm -f "\$PLIST"; fi
    if [ -f "\$SERVICE" ]; then systemctl --user disable "\$INFERO_CMD-device" 2>/dev/null; rm -f "\$SERVICE"; fi
    rm -f "\$BIN_DIR/\$INFERO_CMD"
    echo "[infero] Uninstalled."
    ;;
  *)
    echo "Usage: $INFERO_CMD <pair CODE | list | remove [id] | online | offline | uninstall>"
    ;;
esac
ENDOFCLI
chmod +x "$BIN_DIR/$INFERO_CMD"

# ── Add to PATH if needed ────────────────────────────────────────────────────
NEEDS_PATH=false
SOURCED_RC=""
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        NEEDS_PATH=true
        SHELL_NAME="$(basename "$SHELL")"
        case "$SHELL_NAME" in
            zsh)  RC="$HOME/.zshrc" ;;
            bash) RC="$HOME/.bashrc" ;;
            fish) RC="$HOME/.config/fish/config.fish" ;;
            *)    RC="$HOME/.profile" ;;
        esac
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$RC"
        SOURCED_RC="$RC"
    ;;
esac

# ── Auto-start on boot ───────────────────────────────────────────────────────
if [ "$(uname -s)" = "Darwin" ]; then
    PLIST="$HOME/Library/LaunchAgents/net.${INFERO_CMD}.device.plist"
    cat > "$PLIST" << ENDOFPLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>net.$INFERO_CMD.device</string>
  <key>ProgramArguments</key><array>
    <string>$VENV_DIR/bin/python3</string>
    <string>-u</string>
    <string>$AGENT</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$INFERO_DIR/agent.log</string>
  <key>StandardErrorPath</key><string>$INFERO_DIR/agent.log</string>
</dict></plist>
ENDOFPLIST
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST"
    echo "[infero] Auto-start registered (launchd)"
else
    SERVICE_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SERVICE_DIR"
    cat > "$SERVICE_DIR/infero-device.service" << ENDOFSERVICE
[Unit]
Description=Infero Device Agent
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 -u $AGENT
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
ENDOFSERVICE
    systemctl --user daemon-reload
    systemctl --user enable infero-device
    systemctl --user restart infero-device
    echo "[infero] Auto-start registered (systemd)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✓ Pairing request sent"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  This device will auto-connect on every boot."
echo ""
if [ "$NEEDS_PATH" = true ]; then
echo "  ⚠  Run this to activate the $INFERO_CMD command:"
echo ""
echo "     \033[1;33m  source $SOURCED_RC  \033[0m"
echo ""
echo "     (or open a new terminal)"
echo ""
fi
echo "  Commands:"
echo "    $INFERO_CMD list            — show paired instances"
echo "    $INFERO_CMD pair CODE       — pair another Genesis instance"
echo "    $INFERO_CMD online          — start device agent"
echo "    $INFERO_CMD offline         — stop device agent"
echo "    $INFERO_CMD remove [id]     — remove an instance"
echo "    $INFERO_CMD uninstall       — remove infero completely"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
"""

def build_script(relay_ws, instance_id, token, key, client_name='Unknown'):
    relay_http = relay_ws.replace('wss://', 'https://').replace('ws://', 'http://').replace('/ws', '')
    script = DEVICE_SCRIPT_TEMPLATE
    script = script.replace('{RELAY_WS}', relay_ws)
    script = script.replace('{RELAY_HTTP}', relay_http)
    script = script.replace('{INSTANCE_ID}', instance_id)
    script = script.replace('{TOKEN}', token)
    script = script.replace('{KEY}', key)
    script = script.replace('{CLIENT_NAME}', client_name)
    script = script.replace('AGENT_PY_PLACEHOLDER', AGENT_PY.strip())
    return script

# ─── HTTP handlers ──────────────────────────────────────────────────────────────

async def handle_pair_create(request):
    try:
        body = await request.json()
        instance_id = body.get('instance_id', '')
        client_name = body.get('client_name', 'Unknown')
        if not instance_id:
            return web.Response(status=400, text='instance_id required')
    except Exception:
        return web.Response(status=400, text='Invalid JSON')

    code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(4))
    key_bytes = os.urandom(32)
    key_b64 = base64.urlsafe_b64encode(key_bytes).decode().rstrip('=')

    pending_pairs[code] = {
        'key_b64': key_b64,
        'instance_id': instance_id,
        'client_name': client_name,
        'expires': time.time() + 300
    }

    # Schedule cleanup
    async def cleanup():
        await asyncio.sleep(300)
        pending_pairs.pop(code, None)
    asyncio.create_task(cleanup())

    return web.json_response({'code': code, 'key': key_b64})


async def handle_pair_get(request):
    code = request.match_info['code'].upper()

    entry = pending_pairs.get(code)
    if not entry or time.time() > entry['expires']:
        pending_pairs.pop(code, None)
        error_script = '#!/usr/bin/env bash\necho "[infero] Error: pairing code not found or expired."\necho "[infero] Please go to Genesis Settings → Add Device to generate a new code."\nexit 1\n'
        return web.Response(text=error_script, content_type='text/x-shellscript')

    instance_id = entry['instance_id']
    client_name = entry.get('client_name', 'Unknown')
    key_b64 = entry['key_b64']
    token = secrets.token_urlsafe(32)

    # Register token (device name will be filled in when device connects via WS)
    device_tokens[token] = f"{instance_id}:__pending__"
    save_tokens()

    # One-time use
    pending_pairs.pop(code, None)

    # Derive WS URL from server's own origin (configured via env or default)
    relay_ws = os.environ.get('RELAY_WS_URL', 'ws://localhost:8081')

    script = build_script(relay_ws, instance_id, token, key_b64, client_name)
    return web.Response(
        text=script,
        content_type='text/x-shellscript',
        headers={'Content-Disposition': 'inline; filename="infero_connect.sh"'}
    )


# ─── WebSocket handler ──────────────────────────────────────────────────────────

async def ws_handler(websocket):
    role = None
    instance_id = None
    device_key = None  # "{instance_id}:{device_name}"

    try:
        # First message is handshake
        raw = await websocket.recv()
        msg = json.loads(raw)
        msg_type = msg.get('type')

        if msg_type == 'browser_hello':
            instance_id = msg.get('instance_id', '')
            browser_conns.setdefault(instance_id, []).append(websocket)
            role = 'browser'
            print(f"[{ts()}] [relay] Browser connected: {instance_id[:12]}... ({len(browser_conns[instance_id])} total)")
            # Push current online devices for this instance
            for key, info in device_conns.items():
                if info['instance_id'] == instance_id:
                    try:
                        await websocket.send(json.dumps({
                            'type': 'device_status',
                            'device_name': info['device_name'],
                            'online': True
                        }))
                    except Exception:
                        pass

        elif msg_type == 'device_hello':
            token = msg.get('token', '')
            device_name = msg.get('device_name', 'unknown')
            device_type = msg.get('device_type', 'shell')
            instance_id = msg.get('instance_id', '')

            if token not in device_tokens:
                await websocket.close(4001, 'Invalid token')
                return

            fresh_pair = device_tokens[token].endswith(':__pending__')
            device_key = f"{instance_id}:{device_name}"
            device_tokens[token] = device_key
            save_tokens()
            device_conns[device_key] = {
                'ws': websocket,
                'instance_id': instance_id,
                'device_name': device_name,
                'device_type': device_type,
                'token': token
            }
            role = 'device'
            print(f"[{ts()}] [relay] Device connected: {device_name} (instance {instance_id[:12]}...)")

            # Notify all nodes (browsers + other devices)
            await broadcast_to_instance(instance_id, json.dumps({
                'type': 'device_status',
                'device_name': device_name,
                'device_type': device_type,
                'online': True,
                'fresh_pair': fresh_pair
            }), exclude_ws=websocket)
        else:
            await websocket.close(4000, 'Unknown handshake type')
            return

        # Message routing loop
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            mtype = msg.get('type', '')

            # ─── Distributed loop messages (any role can send) ────────────
            # Broadcast to all other nodes in this instance
            if mtype in ('stream_token', 'loop_status', 'exec_display', 'settings_update'):
                await broadcast_to_instance(instance_id, raw, exclude_ws=websocket)
                continue
            # Forward to a specific device by name
            if mtype in ('loop_handoff', 'loop_stop', 'exec_request', 'exec_result',
                         'user_input', 'request_device_data', 'device_data_response'):
                target_name = msg.get('device_name') or msg.get('target')
                if target_name:
                    await send_to_device(instance_id, target_name, raw)
                else:
                    await broadcast_to_instance(instance_id, raw, exclude_ws=websocket)
                continue
            # Also forward exec_request/exec_result to browsers (browser as exec target)
            if mtype == 'browser_exec_request':
                await send_to_browsers(instance_id, raw)
                continue
            if mtype == 'browser_exec_result':
                # Forward back to the requesting device
                target_name = msg.get('device_name')
                if target_name:
                    await send_to_device(instance_id, target_name, raw)
                continue
            # consciousness_sync: request → forward to target device, response → broadcast to browsers
            if mtype == 'consciousness_sync':
                if msg.get('action') == 'request':
                    target_name = msg.get('device_name')
                    if target_name:
                        await send_to_device(instance_id, target_name, raw)
                    else:
                        await broadcast_to_instance(instance_id, raw, exclude_ws=websocket)
                else:  # response
                    await send_to_browsers(instance_id, raw)
                continue

            # ─── Legacy messages (role-specific) ──────────────────────────
            if role == 'browser':
                if msg.get('type') == 'ping':
                    try:
                        await websocket.send(json.dumps({'type': 'pong'}))
                    except Exception:
                        pass
                    continue

                if msg.get('type') == 'device_remove':
                    target_key = f"{instance_id}:{msg.get('device_name', '')}"
                    target = device_conns.get(target_key)
                    if target:
                        device_tokens.pop(target['token'], None)
                        save_tokens()
                        try:
                            await target['ws'].close(4002, 'Device removed by user')
                        except Exception:
                            pass
                    continue

                # Forward exec to device
                if msg.get('type') == 'exec':
                    target_key = f"{instance_id}:{msg.get('device_name', '')}"
                    target = device_conns.get(target_key)
                    if target:
                        try:
                            await target['ws'].send(raw)
                        except Exception as e:
                            # Device disconnected; notify browser
                            err = json.dumps({
                                'type': 'result',
                                'req_id': msg.get('req_id', ''),
                                'error': f'Device unreachable: {e}'
                            })
                            try:
                                await websocket.send(err)
                            except Exception:
                                pass
                    else:
                        err = json.dumps({
                            'type': 'result',
                            'req_id': msg.get('req_id', ''),
                            'error': f"Device not connected: {msg.get('device_name')}"
                        })
                        try:
                            await websocket.send(err)
                        except Exception:
                            pass

            elif role == 'device':
                if msg.get('type') == 'device_remove_self':
                    # Device is removing itself — notify all browsers
                    await send_to_browsers(instance_id, json.dumps({
                        'type': 'device_removed',
                        'device_name': msg.get('device_name', '')
                    }))
                    # Revoke token
                    device_tokens.pop(device_conns.get(device_key, {}).get('token', ''), None)
                    save_tokens()
                    continue

                # Forward result to all browsers
                if msg.get('type') == 'result':
                    await send_to_browsers(instance_id, raw)

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[{ts()}] [relay] WS error ({role}): {e}")
    finally:
        # Cleanup on disconnect
        if role == 'browser' and instance_id:
            conns = browser_conns.get(instance_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                browser_conns.pop(instance_id, None)
            print(f"[{ts()}] [relay] Browser disconnected: {instance_id[:12]}... ({len(browser_conns.get(instance_id, []))} remaining)")

        elif role == 'device' and device_key:
            info = device_conns.pop(device_key, None)
            if info:
                print(f"[{ts()}] [relay] Device disconnected: {info['device_name']}")
                await broadcast_to_instance(instance_id, json.dumps({
                    'type': 'device_status',
                    'device_name': info['device_name'],
                    'device_type': info.get('device_type', 'shell'),
                    'online': False
                }))


# ─── Entry point ────────────────────────────────────────────────────────────────

async def main():
    load_tokens()

    # HTTP server
    app = web.Application()
    app.router.add_post('/pair/create', handle_pair_create)
    app.router.add_get('/pair/{code}', handle_pair_get)

    runner = web.AppRunner(app)
    await runner.setup()
    http_port = int(os.environ.get('HTTP_PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', http_port)
    await site.start()
    print(f"[{ts()}] [relay] HTTP listening on :{http_port}")

    # WebSocket server
    ws_port = int(os.environ.get('WS_PORT', 8081))
    async with websockets.serve(ws_handler, '0.0.0.0', ws_port):
        print(f"[{ts()}] [relay] WebSocket listening on :{ws_port}")
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    asyncio.run(main())
