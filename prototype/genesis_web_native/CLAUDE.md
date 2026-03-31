# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Genesis (Infero) v0.1 — a local-first digital life engine. Split-screen web app: chat console (left) + visual canvas & living UI (right). The AI can execute JavaScript in the browser via `/browser exec` blocks and self-loop via `/self_continue` or pause via `/call_for_human`.

## Architecture

**Single file, zero build step:**

- **`index.html`** — The entire frontend: UI, state management, IndexedDB storage, SSE streaming, JS execution, and the system prompt. All in one self-contained SPA.
- **`models.json`** — Model and provider configuration, loaded from remote (`https://infero.net/genesis/models.json`).

**Data flow:** Browser → LLM API (SSE) → streamed back to browser. Provider/endpoint configurable in settings (Gemini, OpenAI, Anthropic, DeepSeek, OpenRouter, custom).

**Storage:** All data lives in browser IndexedDB (`GenesisDB`, object store `beings`). No server-side state.

**Core loop (BIS architecture):**
- `perceive()` — formats environment context + user input
- `infer()` — calls LLM, streams response, extracts `/browser exec` code blocks
- `act(B)` — executes extracted JS, writes result to consciousness (15s timeout)
- `loop()` — orchestrates the cycle; continues on `/self_continue`, stops on `/call_for_human`

## Deployment

Static file hosting. No server required for core functionality.

```bash
# Production (infero.net)
sudo cp index.html /var/www/infero.net/genesis/index.html
sudo cp models.json /var/www/infero.net/genesis/models.json
```

Also works from GitHub Pages, Vercel, or local `file://`.

## Key Conventions

- The canvas is Retina-aware: AI-generated JS must **never** set `canvas.width`/`canvas.height` directly.
- `#html-div` overlays canvas with transparent background. AI can place interactive HTML elements there. Content is auto-saved/restored via snapshots.
- AI output must end with `/call_for_human` or `/self_continue` — this drives the autonomous execution loop.
- The system prompt is defined inline in `SYSTEM_INSTRUCTION` at the top of index.html.
- Settings (model, provider, token, vision mode) stored in `localStorage.genesis_settings`.
- Context compression triggers at 300k tokens, saves trimmed middle to IndexedDB.
