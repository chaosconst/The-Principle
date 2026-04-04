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
from collections import defaultdict
from datetime import datetime

import websockets
from aiohttp import web

# ─── Rate limiting ──────────────────────────────────────────────────────────────

_rate_buckets = defaultdict(list)  # (ip, endpoint) -> [timestamps]

def _rate_limit_ok(ip, endpoint, max_requests, window_seconds):
    key = (ip, endpoint)
    now = time.time()
    _rate_buckets[key] = [t for t in _rate_buckets[key] if now - t < window_seconds]
    if len(_rate_buckets[key]) >= max_requests:
        return False
    _rate_buckets[key].append(now)
    return True

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ─── In-memory state ───────────────────────────────────────────────────────────

pending_pairs = {}   # code -> {browser_pub, instance_id, client_name, expires}
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

_AGENT_PY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent.py')
def _load_agent_py():
    with open(_AGENT_PY_PATH, 'r') as f:
        return f.read()

AGENT_PY = _load_agent_py()  # loaded once at startup; restart relay to pick up changes


DEVICE_SCRIPT_TEMPLATE = r"""#!/usr/bin/env bash
set -e

RELAY_WS="{RELAY_WS}"
RELAY_HTTP="{RELAY_HTTP}"
INSTANCE_ID="{INSTANCE_ID}"
TOKEN="{TOKEN}"
BROWSER_PUB="{BROWSER_PUB}"
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
echo "[infero] Installing requirements..."
"$VENV_DIR/bin/pip" install -q cryptography websockets python-socks aiohttp
echo "[infero] Dependencies ready"

# ── Download agent.py ────────────────────────────────────────────────────────
curl -fsSL "$RELAY_HTTP/update" -o "$AGENT"
if [ ! -s "$AGENT" ]; then echo "[infero] Failed to download agent.py"; exit 1; fi

# ── Update instances.json (append or update this instance) ───────────────────
INSTANCE_ID="$INSTANCE_ID" TOKEN="$TOKEN" BROWSER_PUB="$BROWSER_PUB" RELAY_WS="$RELAY_WS" CLIENT_NAME="$CLIENT_NAME" INFERO_DIR="$INFERO_DIR" \
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
                  'browser_pub': os.environ['BROWSER_PUB'], 'relay_ws': os.environ['RELAY_WS'],
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
  update)
    echo "[infero] Updating agent..."
    curl -fsSL "\$RELAY_HTTP/update" -o "\$INFERO_DIR/agent.py.new"
    if [ \$? -eq 0 ] && [ -s "\$INFERO_DIR/agent.py.new" ]; then
        mv "\$INFERO_DIR/agent.py.new" "\$AGENT"
        echo "[infero] Agent updated."
        _restart_agent
        echo "[infero] Agent restarted."
    else
        rm -f "\$INFERO_DIR/agent.py.new"
        echo "[infero] Update failed."
        exit 1
    fi
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
    echo "Usage: $INFERO_CMD <pair CODE | list | remove [id] | update | online | offline | uninstall>"
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

# ── Wait for verify words from agent ────────────────────────────────────────
VFILE="$INFERO_DIR/verify_{INSTANCE_ID}.tmp"
rm -f "$VFILE"
echo ""
echo "[infero] Connecting to relay..."
VWORDS=""
for i in $(seq 1 20); do
    sleep 1
    if [ -f "$VFILE" ]; then
        VWORDS=$(cat "$VFILE")
        rm -f "$VFILE"
        break
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✓ Pairing request sent"
if [ -n "$VWORDS" ]; then
echo " 🔑 Verify Words: \033[1;96m$VWORDS\033[0m"
fi
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
echo "    $INFERO_CMD update          — update agent to latest version"
echo "    $INFERO_CMD online          — start device agent"
echo "    $INFERO_CMD offline         — stop device agent"
echo "    $INFERO_CMD remove [id]     — remove an instance"
echo "    $INFERO_CMD uninstall       — remove infero completely"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
"""

def build_script(relay_ws, instance_id, token, browser_pub, client_name='Unknown'):
    relay_http = relay_ws.replace('wss://', 'https://').replace('ws://', 'http://').replace('/ws', '')
    script = DEVICE_SCRIPT_TEMPLATE
    script = script.replace('{RELAY_WS}', relay_ws)
    script = script.replace('{RELAY_HTTP}', relay_http)
    script = script.replace('{INSTANCE_ID}', instance_id)
    script = script.replace('{TOKEN}', token)
    script = script.replace('{BROWSER_PUB}', browser_pub)
    script = script.replace('{CLIENT_NAME}', client_name)
    return script

# ─── HTTP handlers ──────────────────────────────────────────────────────────────

async def handle_pair_create(request):
    ip = request.remote
    if not _rate_limit_ok(ip, 'pair_create', max_requests=10, window_seconds=600):
        return web.Response(status=429, text='Too many requests')
    try:
        body = await request.json()
        instance_id = body.get('instance_id', '')
        client_name = body.get('client_name', 'Unknown')
        browser_pub = body.get('browser_pub', '')
        if not instance_id:
            return web.Response(status=400, text='instance_id required')
        if not browser_pub:
            return web.Response(status=400, text='browser_pub required')
    except Exception:
        return web.Response(status=400, text='Invalid JSON')

    code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(4))

    pending_pairs[code] = {
        'browser_pub': browser_pub,
        'instance_id': instance_id,
        'client_name': client_name,
        'expires': time.time() + 300
    }

    # Schedule cleanup
    async def cleanup():
        await asyncio.sleep(300)
        pending_pairs.pop(code, None)
    asyncio.create_task(cleanup())

    return web.json_response({'code': code})


async def handle_pair_get(request):
    ip = request.remote
    if not _rate_limit_ok(ip, 'pair_get', max_requests=20, window_seconds=300):
        error_script = '#!/usr/bin/env bash\necho "[infero] Rate limit exceeded. Please wait a few minutes."\nexit 1\n'
        return web.Response(text=error_script, content_type='text/x-shellscript')
    code = request.match_info['code'].upper()

    entry = pending_pairs.get(code)
    if not entry or time.time() > entry['expires']:
        pending_pairs.pop(code, None)
        error_script = '#!/usr/bin/env bash\necho "[infero] Error: pairing code not found or expired."\necho "[infero] Please go to Genesis Settings → Add Device to generate a new code."\nexit 1\n'
        return web.Response(text=error_script, content_type='text/x-shellscript')

    instance_id = entry['instance_id']
    client_name = entry.get('client_name', 'Unknown')
    browser_pub = entry['browser_pub']
    token = secrets.token_urlsafe(32)

    # Register token (device name will be filled in when device connects via WS)
    device_tokens[token] = f"{instance_id}:__pending__"
    save_tokens()

    # One-time use
    pending_pairs.pop(code, None)

    # Derive WS URL from server's own origin (configured via env or default)
    relay_ws = os.environ.get('RELAY_WS_URL', 'ws://localhost:8081')

    script = build_script(relay_ws, instance_id, token, browser_pub, client_name)
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
                'fresh_pair': fresh_pair,
                'device_pub': msg.get('device_pub', '')
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
            # loop_status: device→browsers only (device_name is sender, not target)
            if mtype == 'loop_status':
                await send_to_browsers(instance_id, raw)
                continue
            if mtype in ('stream_token', 'exec_display', 'settings_update'):
                target = msg.get('device_name')
                if target:
                    await send_to_device(instance_id, target, raw)
                else:
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
                action = msg.get('action', '?')
                target_name = msg.get('device_name', '?')
                being = msg.get('being_id', '?')
                conn_key = f"{instance_id}:{target_name}"
                found = conn_key in device_conns if action == 'request' else True
                print(f"[{ts()}] [relay] consciousness_sync {action} from={role} target={target_name} being={being} conn_key={conn_key} found={found}")
                if action == 'request':
                    if target_name and target_name != '?':
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
                    target_name = msg.get('device_name', '')
                    target_key = f"{instance_id}:{target_name}"
                    # Revoke token regardless of whether device is currently connected
                    for tok, val in list(device_tokens.items()):
                        if val == target_key:
                            device_tokens.pop(tok, None)
                            break
                    save_tokens()
                    # Close connection if device is online
                    target = device_conns.get(target_key)
                    if target:
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


async def handle_update(request):
    return web.Response(text=_load_agent_py().strip(), content_type='text/x-python')

_BIP39_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bip39.txt')

async def handle_bip39(request):
    try:
        with open(_BIP39_PATH) as f:
            return web.Response(text=f.read(), content_type='text/plain',
                                headers={'Access-Control-Allow-Origin': '*'})
    except FileNotFoundError:
        return web.Response(status=404, text='bip39.txt not found')


# ─── Entry point ────────────────────────────────────────────────────────────────

async def main():
    load_tokens()

    # HTTP server
    app = web.Application()
    app.router.add_post('/pair/create', handle_pair_create)
    app.router.add_get('/pair/{code}', handle_pair_get)
    app.router.add_get('/update', handle_update)
    app.router.add_get('/bip39', handle_bip39)

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
