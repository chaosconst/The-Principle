# Genesis (Infero) v0.1

A local-first digital life engine. Single HTML file, zero build step, zero server dependency.

## Architecture

**Single file SPA (`index.html`):**
- All state (consciousness stream, settings, snapshots) stored in browser IndexedDB
- Split-screen UI: chat console (left) + visual canvas & living UI (right)
- AI executes JavaScript via `/browser exec` blocks, results feed back into the loop
- Autonomous BIS loop: `perceive() → infer() → act() → loop()`

**Data flow:** Browser → LLM API (SSE) → streamed back to browser. No server-side state.

## Features

- **Multi-model support**: Gemini, GPT, Claude, DeepSeek via configurable providers
- **Vision**: Canvas capture, pageshot (html2canvas), native screen capture (getDisplayMedia)
- **Context compression**: Auto-trims consciousness at 300k tokens, saves logs to IndexedDB
- **Snapshot persistence**: Canvas + HTML UI auto-saved and restored on reload
- **Living UI**: `#html-div` layer for AI-generated interactive HTML elements

## Quick Start

Just open `index.html` in a browser, or visit [infero.net/genesis](https://infero.net/genesis/).

Configure your model and API key in the settings panel (⚙).

## License

MIT — see [LICENSE](LICENSE)
