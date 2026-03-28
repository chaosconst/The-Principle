# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Genesis (Infero) — a local-first digital life engine. Split-screen web app: chat console (left) + visual canvas (right). The AI can execute JavaScript in the browser via `/browser exec` blocks and self-loop via `/self_continue` or pause via `/call_for_human`.

## Architecture

**Two files, zero build step:**

- **`index.html`** — The entire frontend: UI, state management, IndexedDB storage, SSE streaming, JS sandboxed execution, and the Gemini system prompt. All in one self-contained SPA.
- **`relay_server.py`** — Stateless FastAPI BFF proxy. Injects `GOOGLE_API_KEY` server-side and streams Gemini SSE responses back to the frontend. No database, no logs.

**Data flow:** Browser → `POST /api/relay` → relay injects API key → Google Gemini SSE → streamed back to browser.

**Storage:** All conversation history lives in the browser's IndexedDB (`GenesisDB`, object store `sessions`). The server stores nothing. Legacy localStorage data is auto-migrated on first load.

## Running Locally

```bash
# Requires .env in parent directory (../. env) with GOOGLE_API_KEY=...
# Optional: MODEL=gemini-3.1-pro-preview (default)
python relay_server.py          # starts on 127.0.0.1:8080
```

Dependencies: `fastapi`, `httpx`, `uvicorn`

In production, Nginx serves `index.html` statically and reverse-proxies `/api/relay` to port 8080.

## Key Conventions

- The canvas is Retina-aware: `resizeCanvas()` handles DPR scaling. AI-generated JS must **never** set `canvas.width`/`canvas.height` directly.
- AI output must end with `/call_for_human` or `/self_continue` — this drives the autonomous execution loop.
- The system prompt is defined inline in `SYSTEM_INSTRUCTION` (around line 165 of index.html). Changes there affect all AI behavior.
- Error recovery on failed API calls: the user's message is popped from history and restored to the input field.
