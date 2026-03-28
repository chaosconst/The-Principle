import os
import json
import time
import re
import httpx
import redis
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# --- .env 解析 ---
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('export '):
                    line = line[7:]
                if '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip().strip('"\'')

API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL = os.environ.get("MODEL", "gemini-3.1-pro-preview")
QUOTA_PER_CLIENT = int(os.environ.get("QUOTA_PER_CLIENT", "5"))   # 测试用，正式改 50
QUOTA_PER_IP = int(os.environ.get("QUOTA_PER_IP", "20"))         # 测试用，正式改 2000
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

# 从 index.html 读取 SYSTEM_INSTRUCTION，保持前后端统一
_html_path = os.path.join(os.path.dirname(__file__), 'index.html')
with open(_html_path, 'r', encoding='utf-8') as f:
    _match = re.search(r'const SYSTEM_INSTRUCTION = `(.*?)`', f.read(), re.DOTALL)
SYSTEM_PROMPT_FULL = _match.group(1).replace('\\`', '`').replace('\\n', '\n').replace('\\\\', '\\') if _match else None

# --- Redis 限流 ---
rdb = redis.from_url(REDIS_URL, decode_responses=True)

def get_identity(request: Request):
    """提取 IP 和 clientID，分开返回"""
    ip = request.headers.get("x-forwarded-for", request.client.host)
    if "," in ip:
        ip = ip.split(",")[0].strip()
    client_id = request.headers.get("x-client-id", "unknown")
    return ip, client_id

def check_rate_limit(ip, client_id):
    """IP 和 clientID 分别限流，两个都得过。返回 (allowed, remaining, reset_at)"""
    def check(key, quota):
        count = rdb.incr(key)
        if count == 1:
            rdb.expire(key, 86400)
        ttl = rdb.ttl(key)
        reset_at = int(time.time()) + max(ttl, 0)
        remaining = max(quota - count, 0)
        return count <= quota, remaining, reset_at

    ip_ok, ip_remaining, ip_reset = check(f"rl:ip:{ip}", QUOTA_PER_IP)
    cid_ok, cid_remaining, cid_reset = check(f"rl:cid:{client_id}", QUOTA_PER_CLIENT)

    if not ip_ok or not cid_ok:
        # 回退：不该扣的额度还回去
        if not ip_ok and cid_ok:
            rdb.decr(f"rl:cid:{client_id}")
        if not cid_ok and ip_ok:
            rdb.decr(f"rl:ip:{ip}")
        if not ip_ok and not cid_ok:
            rdb.decr(f"rl:ip:{ip}")
            rdb.decr(f"rl:cid:{client_id}")
        reset_at = max(ip_reset, cid_reset)
        return False, 0, reset_at

    remaining = min(ip_remaining, cid_remaining)
    reset_at = max(ip_reset, cid_reset)
    return True, remaining, reset_at

# --- App ---
app = FastAPI()
app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Quota-Remaining", "X-Quota-Reset"],
)

@app.post("/api/relay")
async def relay_request(request: Request):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key missing on server")

    # 限流
    ip, client_id = get_identity(request)
    allowed, remaining, reset_at = check_rate_limit(ip, client_id)
    if not allowed:
        return JSONResponse(status_code=429, content={
            "error": "Rate limit exceeded",
            "reset_at": reset_at,
            "message": "Free quota exhausted. Configure your own API key to continue."
        }, headers={
            "X-Quota-Remaining": "0",
            "X-Quota-Reset": str(reset_at),
        })

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # System prompt 校验：必须与 index.html 中定义的 SYSTEM_INSTRUCTION 完全一致
    if SYSTEM_PROMPT_FULL:
        try:
            sys_text = payload["systemInstruction"]["parts"][0]["text"]
            if sys_text != SYSTEM_PROMPT_FULL:
                raise HTTPException(status_code=403, detail="Invalid system prompt")
        except (KeyError, IndexError, TypeError):
            raise HTTPException(status_code=403, detail="Missing system prompt")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:streamGenerateContent?alt=sse&key={API_KEY}"

    async def stream_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, timeout=120.0) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    yield f"data: {json.dumps({'error': err.decode()})}\n\n".encode('utf-8')
                    return
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "X-Quota-Remaining": str(remaining),
            "X-Quota-Reset": str(reset_at),
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
