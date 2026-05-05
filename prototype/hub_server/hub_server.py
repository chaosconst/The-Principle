"""
INFERO Skill Hub server.

Endpoints:
    GET  /hub/list?sort=hot|new&q=...     public, list approved skills
    GET  /hub/skill/{name}                auth, returns skill JSON, bumps install count
    POST /hub/submit                      auth, Gemini-reviewed submission

Storage: SQLite at $HUB_DB (default ./hub.db).
Auth: infero_key from cookie `infero_key` or header `X-Infero-Key`.
      Set HUB_DEV_MODE=1 to allow anonymous (uses caller IP-derived hash).

Run:
    PORT=8089 HUB_DEV_MODE=1 python3 hub_server.py
"""
import os
import re
import json
import time
import hashlib
import sqlite3
import math
import asyncio
from contextlib import contextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# --- env-file loader: try a few candidate paths ---
_here = os.path.dirname(os.path.abspath(__file__))
_env_candidates = [
    os.environ.get("HUB_ENV_FILE", ""),
    os.path.normpath(os.path.join(_here, '..', 'env')),              # prototype/env (local dev — current)
    os.path.normpath(os.path.join(_here, '..', '..', '.env')),       # The-Principle/.env (legacy)
    os.path.normpath(os.path.join(_here, '..', '..', '..', '.env')), # Projects/.env (matches relay_server.py prod path)
]
for env_path in _env_candidates:
    if env_path and os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('export '):
                        line = line[7:]
                    if '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"\''))
        break

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
REVIEW_MODEL = os.environ.get("HUB_REVIEW_MODEL", "gemini-2.5-flash")
DB_PATH = os.environ.get("HUB_DB", os.path.join(os.path.dirname(__file__), "hub.db"))
DEV_MODE = os.environ.get("HUB_DEV_MODE", "0") == "1"
PORT = int(os.environ.get("PORT", "8089"))

MAX_NAME = 64
MAX_INSTRUCTION = 4000
MAX_CODE = 200000
MAX_README = 1000
MAX_TAGS = 8
MAX_CONTACT = 1024
MAX_NOTE = 200000

# --- DB ---
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS skills (
            name TEXT PRIMARY KEY,
            author_hash TEXT NOT NULL,
            instruction TEXT NOT NULL,
            code TEXT,
            code_readme TEXT,
            tags TEXT,
            created_at INTEGER NOT NULL,
            status TEXT NOT NULL,
            severity TEXT,
            score INTEGER DEFAULT 0,
            review TEXT,
            safety_review TEXT,
            reject_reason TEXT,
            installs INTEGER DEFAULT 0,
            being_name TEXT,
            companion_name TEXT
        );
        CREATE TABLE IF NOT EXISTS installs (
            skill_name TEXT NOT NULL,
            user_hash TEXT NOT NULL,
            ts INTEGER NOT NULL,
            PRIMARY KEY (skill_name, user_hash)
        );
        CREATE TABLE IF NOT EXISTS submissions (
            author_hash TEXT NOT NULL,
            ts INTEGER NOT NULL,
            decision TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status);
        CREATE INDEX IF NOT EXISTS idx_subm_author_ts ON submissions(author_hash, ts);
        """)
        for col in ("being_name", "companion_name", "contact", "note"):
            try:
                c.execute(f"ALTER TABLE skills ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass

init_db()

# --- Auth helpers ---
def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

def is_owner(stored: str, current: str) -> bool:
    """Match request identity against stored row author_hash.
    Legacy rows hold an 8-hex prefix; accept if the current full pubkey starts with it.
    Otherwise require strict equality."""
    if not stored or not current:
        return False
    if stored == current:
        return True
    if len(stored) == 8 and len(current) == 66 and current.startswith(stored):
        return True
    return False

def get_user_hash(req: Request) -> str:
    pubkey = (req.headers.get("X-Infero-Pubkey") or "").strip().lower()
    if len(pubkey) == 66 and all(c in "0123456789abcdef" for c in pubkey):
        return pubkey
    key = req.headers.get("X-Infero-Key") or req.cookies.get("infero_key")
    if not key:
        if DEV_MODE:
            ip = (req.client.host if req.client else "0.0.0.0")
            return "dev:" + hash_key(ip)[:16]
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    return hash_key(key)

# --- Cooldown ---
COOLDOWN_LADDER = [
    (0, 10),         # 0 rejected: 10s between submits
    (1, 60),         # 1: 60s
    (2, 360),        # 2: 6 min
    (3, 2160),       # 3: 36 min
    (4, 8640),       # 4+: ~2.4 hours
]

def cooldown_seconds(rejected_24h: int) -> int:
    secs = 60
    for n, s in COOLDOWN_LADDER:
        if rejected_24h >= n:
            secs = s
    return secs

def check_cooldown(c, author_hash: str) -> Optional[int]:
    """Return cooldown_until ts (epoch) if user is on cooldown, else None.
    Cooldown duration ramps with rejected count in last 24h. Reference ts is
    the last submission of any kind, so the 10s base also throttles spam."""
    now = int(time.time())
    cutoff = now - 24 * 3600
    rejected = c.execute(
        "SELECT COUNT(*) FROM submissions WHERE author_hash=? AND ts>=? AND decision='rejected'",
        (author_hash, cutoff),
    ).fetchone()[0]
    last = c.execute(
        "SELECT MAX(ts) FROM submissions WHERE author_hash=?",
        (author_hash,),
    ).fetchone()[0]
    secs = cooldown_seconds(rejected)
    if last and now - last < secs:
        return last + secs
    return None

# --- Gemini review ---
REVIEW_PROMPT_TEMPLATE = """You are an editor at the INFERO Skill Hub — score with the eye of an app-store editor curating the front page.
Your scores are later compared against (a) install counts and (b) a Jobs-level human curator.
Mismatches cost you reputation; a high score you give costs more when the skill flops.

=== background: what INFERO is ===
INFERO is a digital-life engine. Each user runs a Being — an LLM-driven agent that may live in a browser SPA
or on a server (agent.py), following the loop:
  State -> Infer(State) -> Being -> Act/Perceive(Being) -> State'
A browser-hosted Being executes JavaScript via `/browser exec`; a server-hosted Being executes shell. Both
mutate the same memory model (`{{beingId}}/...` key namespace, mirrored via handoff). A Being installs skills
voluntarily into its own context; there is no separate end-user being served by the LLM.

=== background: what a skill is ===
A skill is one record at key "{{beingId}}/skill/{{name}}", with fields:
- instruction: natural-language description. When enabled, every loop splices it into the Being's own system context.
- code: optional cache. Either null, or an object `{{ js, shell, python, ... }}` keyed by runtime — each host eval's
  the variant it can run, missing variants simply mean "no cache for this runtime".
- code_readme: how the Being should call the cached `code`.
- contact: optional public author contact (email, npub, url). Visible on the hub; not injected into ctx.
- note: optional long-form prose for hub readers (changelog, design notes, examples, even literature). Visible on the hub; not injected into ctx.
A skill is a description by default; `code` is an optional per-runtime cache. The Being is both the author of the
install decision and the audience of the instruction text. `contact` and `note` are author-public fields shown
on the hub page — review them for abuse (spam, dox, illegal content, harassment), but don't reject solely for being
literary or off-tool: long-form notes / changelogs / dedications are legitimate uses.

=== submission ===
name: {name}
tags: {tags}
contact: {contact}

instruction:
{instruction}

code:
{code}

code_readme:
{code_readme}

note:
{note}

=== output ===
Reply in markdown, sections in this exact order:

## Safety Review
Analyze the actual behavior of code and any safety concerns in instruction (including prompt-injection risk). Note whether instruction, code, and code_readme are mutually consistent. Also screen `contact` and `note` for abuse — spam, dox, illegal content, harassment — but treat literary / personal / changelog content as legitimate.

## Risk
safe | caution | danger

## Verdict
approved | rejected

---

## Skill Review
One sentence, under 140 characters, helping other users decide whether to install.

## Score
0-10 integer. 0 = strongly do not recommend installing, basically never useful. 10 = strongly recommend installing, must-have on every device.
"""

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

FAKE_REVIEW = os.environ.get("HUB_FAKE_REVIEW", "0") == "1"

FAKE_TEMPLATE = """## Safety Review
Code is attached to window.{name_safe}; does not read sensitive storage and makes no outbound requests. {safety_note}

## Risk
{severity}

## Verdict
{verdict}

---

## Skill Review
{review_text}

## Score
{score}
"""

def fake_review(payload: dict) -> str:
    name = payload.get("name", "skill")
    code = payload.get("code", "") or ""
    # crude heuristic for testing rejection path
    bad = any(p in code for p in ["localStorage.getItem('genesis_settings", "document.cookie", "eval(", "new Function("])
    if bad:
        return FAKE_TEMPLATE.format(
            name_safe=name, safety_note="Sensitive API detected; rejected.",
            severity="danger", verdict="rejected",
            review_text="Code reads sensitive fields or executes dynamically; rejected.",
            score=1)
    return FAKE_TEMPLATE.format(
        name_safe=name, safety_note="Safe.",
        severity="safe", verdict="approved",
        review_text=f"{name} is concise, matches the instruction, fits a demo.",
        score=6)

async def call_gemini(prompt: str, payload: Optional[dict] = None) -> str:
    if FAKE_REVIEW:
        return fake_review(payload or {})
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="server misconfigured: GOOGLE_API_KEY not set (or run with HUB_FAKE_REVIEW=1 for offline testing)")
    url = GEMINI_URL.format(model=REVIEW_MODEL, key=GOOGLE_API_KEY)
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    async with httpx.AsyncClient(timeout=60.0) as cli:
        r = await cli.post(url, json=body)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"gemini error {r.status_code}: {r.text[:200]}")
        data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail=f"gemini malformed: {json.dumps(data)[:300]}")

def section(text: str, header: str) -> Optional[str]:
    """Extract content under '## <header>' until next '## ' or end."""
    pat = re.compile(r"^##\s+" + re.escape(header) + r"\s*$", re.MULTILINE | re.IGNORECASE)
    m = pat.search(text)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + nxt.start() if nxt else len(text)
    return text[start:end].strip()

def parse_review(md: str) -> dict:
    def first_word(s: str) -> Optional[str]:
        m = re.search(r"[a-zA-Z]+", s or "")
        return m.group().lower() if m else None
    safety = section(md, "Safety Review")
    severity = first_word(section(md, "Risk") or section(md, "Severity") or "")
    verdict = first_word(section(md, "Verdict") or "")
    review = section(md, "Skill Review")
    score_raw = (section(md, "Score") or "").strip()
    score_match = re.search(r"\d+", score_raw)
    score = int(score_match.group()) if score_match else None

    if severity not in ("safe", "caution", "danger"):
        severity = None
    if verdict not in ("approved", "rejected"):
        verdict = None
    if score is None or not (0 <= score <= 10):
        score = None

    return {
        "safety_review": safety,
        "severity": severity,
        "verdict": verdict,
        "review": review,
        "score": score,
        "raw": md,
    }

# --- Validation ---
def validate_submission(payload: dict) -> tuple[bool, str]:
    name = (payload.get("name") or "").strip()
    if not name or len(name) > MAX_NAME:
        return False, f"name must be 1-{MAX_NAME} chars"
    if not re.match(r"^[\w\-]+$", name):
        return False, "name may contain only letters, digits, underscore, or dash"
    instruction = (payload.get("instruction") or "").strip()
    if not instruction or len(instruction) > MAX_INSTRUCTION:
        return False, f"instruction must be 1-{MAX_INSTRUCTION} chars"
    code = payload.get("code")
    if code is None or code == "":
        pass
    elif isinstance(code, str):
        if len(code) > MAX_CODE:
            return False, f"code must not exceed {MAX_CODE} chars"
    elif isinstance(code, dict):
        for k, v in code.items():
            if not isinstance(k, str) or not isinstance(v, str):
                return False, "code object keys and values must all be strings"
        if len(json.dumps(code)) > MAX_CODE:
            return False, f"code serialized form must not exceed {MAX_CODE} chars"
    else:
        return False, "code must be null, a string, or a { runtime: source } object"
    readme = payload.get("code_readme") or ""
    if readme and len(readme) > MAX_README:
        return False, f"code_readme must not exceed {MAX_README} chars"
    tags = payload.get("tags") or []
    if not isinstance(tags, list) or len(tags) > MAX_TAGS:
        return False, f"tags must be a list of at most {MAX_TAGS} items"
    for t in tags:
        if not isinstance(t, str) or len(t) > 32:
            return False, "tag entries must be strings, each ≤ 32 chars"
    contact = payload.get("contact") or ""
    if contact and (not isinstance(contact, str) or len(contact) > MAX_CONTACT):
        return False, f"contact must be a string ≤ {MAX_CONTACT} chars"
    note = payload.get("note") or ""
    if note and (not isinstance(note, str) or len(note) > MAX_NOTE):
        return False, f"note must be a string ≤ {MAX_NOTE} chars"
    return True, ""

# --- App ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

def skill_to_dict(row, include_code=True):
    d = {
        "name": row["name"],
        "author_hash_short": row["author_hash"][:8],
        "being_name": (row["being_name"] if "being_name" in row.keys() else None) or "",
        "companion_name": (row["companion_name"] if "companion_name" in row.keys() else None) or "",
        "contact": (row["contact"] if "contact" in row.keys() else None) or "",
        "note": (row["note"] if "note" in row.keys() else None) or "",
        "instruction": row["instruction"],
        "code_readme": row["code_readme"],
        "tags": json.loads(row["tags"] or "[]"),
        "created_at": row["created_at"],
        "severity": row["severity"],
        "score": row["score"],
        "review": row["review"],
        "installs": row["installs"],
    }
    if include_code:
        raw = row["code"] or ""
        parsed = None
        if raw.startswith("{"):
            try:
                p = json.loads(raw)
                if isinstance(p, dict):
                    parsed = p
            except Exception:
                pass
        d["code"] = parsed if parsed is not None else raw
        d["safety_review"] = row["safety_review"]
    return d

def hn_rank(score, installs, created_at, now):
    age_h = max(0, (now - created_at) / 3600.0)
    return ((score or 0) + (installs or 0) + 1) / ((age_h + 2) ** 1.8)

@app.get("/hub/list")
async def hub_list(sort: str = "hot", q: Optional[str] = None, limit: int = 5, offset: int = 0):
    limit = max(1, min(100, limit))
    offset = max(0, offset)
    now = int(time.time())
    with db() as c:
        rows = c.execute("SELECT * FROM skills WHERE status='approved'").fetchall()
    items = [skill_to_dict(r, include_code=True) for r in rows]
    rows_with = list(zip(items, rows))
    if q:
        def blob(i):
            return (i["name"] + " " + " ".join(i["tags"]) + " " + (i["instruction"] or "") + " " + (i.get("being_name") or "") + " " + (i.get("companion_name") or "") + " " + (i.get("contact") or "") + " " + (i.get("note") or "")).lower()
        q_low = q.lower().strip()
        full = [(i, r) for (i, r) in rows_with if q_low in blob(i)]
        if full:
            rows_with = full
        else:
            words = [w for w in q_low.split() if w]
            if words:
                rows_with = [(i, r) for (i, r) in rows_with if any(w in blob(i) for w in words)]
            else:
                rows_with = full
    if sort == "new":
        rows_with.sort(key=lambda ir: -ir[1]["created_at"])
    else:
        rows_with.sort(key=lambda ir: -hn_rank(ir[1]["score"], ir[1]["installs"], ir[1]["created_at"], now))
    total = len(rows_with)
    page = rows_with[offset:offset + limit]
    return {
        "version": 1,
        "updated": now,
        "total": total,
        "limit": limit,
        "offset": offset,
        "skills": [i for i, _ in page],
    }

@app.get("/hub/skill/{name}")
async def hub_skill(name: str, request: Request):
    user_hash = get_user_hash(request)
    with db() as c:
        row = c.execute(
            "SELECT * FROM skills WHERE name=? AND status='approved'", (name,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="skill not found")
        # bump install count, dedup by user, skip self-install
        if not is_owner(row["author_hash"], user_hash):
            try:
                c.execute(
                    "INSERT INTO installs (skill_name, user_hash, ts) VALUES (?, ?, ?)",
                    (name, user_hash, int(time.time())),
                )
                c.execute("UPDATE skills SET installs = installs + 1 WHERE name=?", (name,))
                c.commit()
                row = c.execute("SELECT * FROM skills WHERE name=?", (name,)).fetchone()
            except sqlite3.IntegrityError:
                pass  # already counted for this user
    return skill_to_dict(row, include_code=True)

@app.post("/hub/submit")
async def hub_submit(request: Request):
    author_hash = get_user_hash(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="body must be JSON")
    ok, err = validate_submission(payload)
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    name = payload["name"].strip()
    instruction = payload["instruction"].strip()
    raw_code = payload.get("code")
    if isinstance(raw_code, dict):
        code = json.dumps(raw_code, ensure_ascii=False)
    elif isinstance(raw_code, str):
        code = raw_code.strip()
    else:
        code = ""
    code_readme = (payload.get("code_readme") or "").strip()
    tags = payload.get("tags") or []
    being_name = (payload.get("being_name") or "").strip()[:32]
    companion_name = (payload.get("companion_name") or "").strip()[:32]
    contact = (payload.get("contact") or "").strip()[:MAX_CONTACT]
    note = (payload.get("note") or "").strip()[:MAX_NOTE]

    with db() as c:
        existing = c.execute("SELECT author_hash FROM skills WHERE name=?", (name,)).fetchone()
        if existing and not is_owner(existing["author_hash"], author_hash):
            owner_short = (existing["author_hash"] or "")[:8]
            self_short = (author_hash or "")[:8]
            raise HTTPException(
                status_code=409,
                detail=f"skill name '{name}' is owned by another Being (owner author={owner_short}, you={self_short}). "
                       f"If that other Being is also yours, re-upload from it to update. "
                       f"If it belongs to someone else, pick a different skill name.",
            )
        is_own_update = bool(existing and is_owner(existing["author_hash"], author_hash))
        if not is_own_update:
            cu = check_cooldown(c, author_hash)
            if cu:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "cooldown active", "cooldown_until": cu},
                )

    if isinstance(raw_code, dict):
        code_for_review = "\n\n".join(f"--- runtime: {k} ---\n{v}" for k, v in raw_code.items()) or "(no code)"
    else:
        code_for_review = code or "(no code provided — pure instruction skill)"
    prompt = REVIEW_PROMPT_TEMPLATE.format(
        name=name,
        tags=", ".join(tags) if tags else "(none)",
        instruction=instruction,
        code=code_for_review,
        code_readme=code_readme or "(none)",
        contact=contact or "(none)",
        note=note or "(none)",
    )
    md = await call_gemini(prompt, {"name": name, "code": code})
    parsed = parse_review(md)

    if not parsed["verdict"]:
        # parse failure: hard reject, count as rejected for cooldown
        decision = "rejected"
        reject_reason = "Review output format error; please retry"
    elif parsed["verdict"] == "rejected":
        decision = "rejected"
        # prefer pithy skill review; fall back to first line of safety review
        reason_src = parsed["review"] or parsed["safety_review"] or ""
        reject_reason = reason_src.strip().split("\n\n")[0][:300] if reason_src else "Review rejected"
    else:
        decision = "approved"
        reject_reason = None

    now = int(time.time())
    with db() as c:
        c.execute(
            "INSERT INTO submissions (author_hash, ts, decision) VALUES (?, ?, ?)",
            (author_hash, now, decision),
        )
        if decision == "approved":
            c.execute("""
                INSERT INTO skills (name, author_hash, being_name, companion_name, contact, note, instruction, code, code_readme, tags,
                                    created_at, status, severity, score, review, safety_review,
                                    reject_reason, installs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?, ?, ?, ?, NULL, COALESCE((SELECT installs FROM skills WHERE name=?), 0))
                ON CONFLICT(name) DO UPDATE SET
                    author_hash=excluded.author_hash,
                    being_name=excluded.being_name,
                    companion_name=excluded.companion_name,
                    contact=excluded.contact,
                    note=excluded.note,
                    instruction=excluded.instruction,
                    code=excluded.code,
                    code_readme=excluded.code_readme,
                    tags=excluded.tags,
                    severity=excluded.severity,
                    score=excluded.score,
                    review=excluded.review,
                    safety_review=excluded.safety_review,
                    status='approved',
                    reject_reason=NULL
            """, (name, author_hash, being_name, companion_name, contact, note, instruction, code, code_readme, json.dumps(tags),
                  now, parsed["severity"], parsed["score"], parsed["review"],
                  parsed["safety_review"], name))
        c.commit()

    cu = check_cooldown(db(), author_hash)
    return {
        "decision": decision,
        "reject_reason": reject_reason,
        "severity": parsed["severity"],
        "score": parsed["score"],
        "review": parsed["review"],
        "safety_review": parsed["safety_review"],
        "raw": parsed["raw"],
        "cooldown_until": cu,
    }

@app.delete("/hub/skill/{name}")
async def hub_delete(name: str, request: Request):
    """Soft-delete: status -> 'removed'. Only the original author can do this.
    Soft delete keeps the name reserved so nobody can re-claim it later."""
    author_hash = get_user_hash(request)
    with db() as c:
        row = c.execute("SELECT author_hash, status FROM skills WHERE name=?", (name,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        if not is_owner(row["author_hash"], author_hash):
            raise HTTPException(status_code=403, detail="not your skill")
        if row["status"] == "removed":
            return {"ok": True, "already_removed": True}
        c.execute("UPDATE skills SET status='removed' WHERE name=?", (name,))
        c.commit()
    return {"ok": True, "name": name}

@app.get("/hub/health")
async def health():
    return {"ok": True, "dev_mode": DEV_MODE, "model": REVIEW_MODEL, "db": DB_PATH}


if __name__ == "__main__":
    print(f"[hub] listening on :{PORT}  dev_mode={DEV_MODE}  model={REVIEW_MODEL}  db={DB_PATH}")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
