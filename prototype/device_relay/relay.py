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
browser_conns = {}   # instance_id -> websocket
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

# ─── Bash + Python script template ─────────────────────────────────────────────

AGENT_PY = r'''
import asyncio, json, subprocess, base64, os, sys, socket
from datetime import datetime

INFERO_DIR = os.path.expanduser('~/.infero')
INSTANCES_FILE = os.path.join(INFERO_DIR, 'instances.json')
DEVICE_NAME = socket.gethostname().removesuffix('.local')

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
                print(f"[{ts()}] [infero] Connected: {DEVICE_NAME} → {iid}...")
                async def handle_exec(req_id, payload_raw):
                    try:
                        cmd = decrypt(cipher, payload_raw)['cmd']
                        print(f"[{ts()}] [infero] exec ({iid}): {cmd[:60]}")
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

                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get('type') != 'exec': continue
                    asyncio.create_task(handle_exec(msg['req_id'], msg['payload']))
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code == 4002:
                print(f"[{ts()}] [infero] Removed from {iid}. Stopping connection.")
                instances = [i for i in load_instances() if i['instance_id'] != cfg['instance_id']]
                save_instances(instances)
                return
            print(f"[{ts()}] [infero] Disconnected from {iid} ({e.code}). Retry in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as e:
            print(f"[{ts()}] [infero] Error ({iid}): {e}. Retry in {backoff}s...")
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

INFERO_DIR="$HOME/.infero"
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
"$VENV_DIR/bin/pip" install -q cryptography websockets python-socks
echo "[infero] Dependencies ready"

# ── Save agent.py ────────────────────────────────────────────────────────────
cat > "$AGENT" << 'ENDOFAGENT'
AGENT_PY_PLACEHOLDER
ENDOFAGENT

# ── Update instances.json (append or update this instance) ───────────────────
INSTANCE_ID="$INSTANCE_ID" TOKEN="$TOKEN" KEY="$KEY" RELAY_WS="$RELAY_WS" CLIENT_NAME="$CLIENT_NAME" \
"$VENV_DIR/bin/python3" -c "
import json, os
from datetime import datetime
f = os.environ['HOME'] + '/.infero/instances.json'
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
cat > "$BIN_DIR/infero" << ENDOFCLI
#!/usr/bin/env bash
INFERO_DIR="\$HOME/.infero"
VENV_DIR="\$INFERO_DIR/venv"
AGENT="\$INFERO_DIR/agent.py"
INSTANCES="\$INFERO_DIR/instances.json"
BIN_DIR="\$HOME/.local/bin"
PLIST="\$HOME/Library/LaunchAgents/net.infero.device.plist"
SERVICE="\$HOME/.config/systemd/user/infero-device.service"
RELAY_HTTP="$RELAY_HTTP"

_stop_agent() {
    pkill -f "\$AGENT" 2>/dev/null || true
    if [ -f "\$PLIST" ]; then launchctl unload "\$PLIST" 2>/dev/null || true; fi
    if [ -f "\$SERVICE" ]; then systemctl --user stop infero-device 2>/dev/null || true; fi
}

_restart_agent() {
    _stop_agent
    sleep 1
    if [ -f "\$PLIST" ]; then launchctl load "\$PLIST" 2>/dev/null || true
    elif [ -f "\$SERVICE" ]; then systemctl --user start infero-device 2>/dev/null || true
    else nohup "\$VENV_DIR/bin/python3" "\$AGENT" >> "\$INFERO_DIR/agent.log" 2>&1 & fi
}

case "\$1" in
  pair)
    if [ -z "\$2" ]; then echo "Usage: infero pair <CODE>"; exit 1; fi
    curl -fsSL "\$RELAY_HTTP/pair/\$2" | sh
    ;;
  list)
    if [ ! -f "\$INSTANCES" ]; then echo "No instances paired."; exit 0; fi
    "\$VENV_DIR/bin/python3" -c "
import json, os, socket
f = os.environ['HOME'] + '/.infero/instances.json'
try: instances = json.load(open(f))
except: instances = []
if not instances: print('No instances paired.'); exit()
print(f'Device: {socket.gethostname().removesuffix(\".local\")}')
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
        "\$VENV_DIR/bin/python3" -c "
import json, os, sys, asyncio, socket
f = os.environ['HOME'] + '/.infero/instances.json'
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
        "\$BIN_DIR/infero" list
        echo ""
        echo "  infero remove <instance_id>"
    fi
    ;;
  uninstall)
    _stop_agent
    rm -rf "\$INFERO_DIR"
    if [ -f "\$PLIST" ]; then launchctl unload "\$PLIST" 2>/dev/null; rm -f "\$PLIST"; fi
    if [ -f "\$SERVICE" ]; then systemctl --user disable infero-device 2>/dev/null; rm -f "\$SERVICE"; fi
    rm -f "\$BIN_DIR/infero"
    echo "[infero] Uninstalled."
    ;;
  *)
    echo "Usage: infero <pair CODE | list | remove [id] | uninstall>"
    ;;
esac
ENDOFCLI
chmod +x "$BIN_DIR/infero"

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
    PLIST="$HOME/Library/LaunchAgents/net.infero.device.plist"
    cat > "$PLIST" << ENDOFPLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>net.infero.device</string>
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
echo " ✓ Device connected to Genesis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  This device will auto-connect on every boot."
echo ""
if [ "$NEEDS_PATH" = true ]; then
echo "  ⚠  Run this to activate the infero command:"
echo "     source $SOURCED_RC"
echo "     (or open a new terminal)"
echo ""
fi
echo "  Commands:"
echo "    infero list            — show paired instances"
echo "    infero pair CODE       — pair another Genesis instance"
echo "    infero remove [id]     — remove an instance"
echo "    infero uninstall       — remove infero completely"
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
            browser_conns[instance_id] = websocket
            role = 'browser'
            print(f"[{ts()}] [relay] Browser connected: {instance_id[:12]}...")
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

            # Notify browser
            browser_ws = browser_conns.get(instance_id)
            if browser_ws:
                try:
                    await browser_ws.send(json.dumps({
                        'type': 'device_status',
                        'device_name': device_name,
                        'device_type': device_type,
                        'online': True,
                        'fresh_pair': fresh_pair
                    }))
                except Exception:
                    pass
        else:
            await websocket.close(4000, 'Unknown handshake type')
            return

        # Message routing loop
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

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
                    # Device is removing itself — notify browser
                    browser_ws = browser_conns.get(instance_id)
                    if browser_ws:
                        try:
                            await browser_ws.send(json.dumps({
                                'type': 'device_removed',
                                'device_name': msg.get('device_name', '')
                            }))
                        except Exception:
                            pass
                    # Revoke token
                    device_tokens.pop(device_conns.get(device_key, {}).get('token', ''), None)
                    save_tokens()
                    continue

                # Forward result to browser
                if msg.get('type') == 'result':
                    browser_ws = browser_conns.get(instance_id)
                    if browser_ws:
                        try:
                            await browser_ws.send(raw)
                        except Exception:
                            pass

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[{ts()}] [relay] WS error ({role}): {e}")
    finally:
        # Cleanup on disconnect
        if role == 'browser' and instance_id:
            browser_conns.pop(instance_id, None)
            print(f"[{ts()}] [relay] Browser disconnected: {instance_id[:12]}...")

        elif role == 'device' and device_key:
            info = device_conns.pop(device_key, None)
            if info:
                print(f"[{ts()}] [relay] Device disconnected: {info['device_name']}")
                browser_ws = browser_conns.get(instance_id)
                if browser_ws:
                    try:
                        await browser_ws.send(json.dumps({
                            'type': 'device_status',
                            'device_name': info['device_name'],
                            'device_type': info.get('device_type', 'shell'),
                            'online': False
                        }))
                    except Exception:
                        pass


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
