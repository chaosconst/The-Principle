# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Genesis (Infero) — a local-first digital life engine. Split-screen web app: chat console (left) + visual canvas (right). The AI can execute JavaScript in the browser via `/browser exec` blocks and self-loop via `/self_continue` or pause via `/call_for_human`.

## Architecture

**Single file, zero build step:**

- **`index.html`** (~900 lines) — The entire frontend: UI, state management, IndexedDB storage, SSE streaming, JS sandboxed execution, and the system prompt. All in one self-contained SPA.
**Data flow:** Browser → LLM API (SSE) → streamed back to browser. Currently calls `https://infero.net/api/relay`, but the backend is interchangeable.

**Storage:** All conversation history lives in the browser's IndexedDB (`GenesisDB`, object store `sessions`). No server-side state. Legacy localStorage data is auto-migrated on first load.

**Core loop (BIS architecture):** The frontend implements a perceive → infer → act loop:
- `perceive(action_result)` — formats environment context + action results into user message
- `infer()` — calls LLM via relay, streams response, extracts `/browser exec` code blocks
- `act(B_out)` — executes extracted JS in a sandboxed iframe, returns results
- `loop()` — orchestrates the cycle; continues if AI output ends with `/self_continue`, stops on `/call_for_human`

## Deployment

```bash
sudo cp index.html /var/www/infero.net/genesis/index.html
```

Nginx serves `index.html` statically. Backend is deployed separately from `infero_api`.

## Key Conventions

- The canvas is Retina-aware: `resizeCanvas()` handles DPR scaling. AI-generated JS must **never** set `canvas.width`/`canvas.height` directly.
- AI output must end with `/call_for_human` or `/self_continue` — this drives the autonomous execution loop.
- The system prompt is defined inline in `SYSTEM_INSTRUCTION` (around line 519 of index.html). Changes there affect all AI behavior.
- Error recovery on failed API calls: the user's message is popped from history and restored to the input field.
