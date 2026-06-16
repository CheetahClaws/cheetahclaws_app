# CheetahClaws Desktop (P1 MVP)

A thin native-window shell around CheetahClaws' existing, production-ready web
UI. It launches `cheetahclaws --web --no-auth` as a localhost-only **sidecar**
and points a webview at its `/chat` page — so the browser UI (WebSocket
streaming chat, xterm terminal, permission approval, themes) *becomes* the
desktop app, with nothing reimplemented.

```
┌─ Desktop shell (Electron) ─────────────────────────────┐
│  loading.html  →  spawn `cheetahclaws --web --no-auth`  │
│                   (127.0.0.1, auto-picked free port)    │
│                ↓ parse the printed "Chat UI: …/chat"    │
│  BrowserWindow.loadURL(http://127.0.0.1:<port>/chat)    │
└─────────────────────────────────────────────────────────┘
```

The server binds to `127.0.0.1` only and runs as you, with your own API key —
no network exposure, no multi-tenancy. This is the local, bring-your-own-key
model; the hard SaaS problems (sandboxing, billing) are deliberately out of
scope for P1.

## Status

- ✅ **Sidecar integration is verified** — `npm run smoke` launches the real
  server, discovers its port, and confirms `/chat`, `/`, `/health` all serve.
  This is the load-bearing part and it works.
- ⛏️ The Electron window code (`src/main.js`) is written but needs a machine
  with a display to run/build (this was developed headless).

## Prerequisites

- **Node.js 18+** and npm.
- The **`cheetahclaws` CLI on your PATH, with the web extra**:
  ```bash
  pip install 'cheetahclaws[web]'
  cheetahclaws --version    # should print a version
  ```
  (Point at a different binary with `CHEETAHCLAWS_BIN=/path/to/cheetahclaws`.)

## Run

```bash
cd desktop
npm install        # pulls Electron (~150 MB first time)
npm start          # opens the window
```

Verify just the sidecar wiring (no GUI, no Electron needed):

```bash
npm run smoke      # DEBUG=1 npm run smoke  to echo server logs
```

## Package a distributable (later)

`npm run dist` (electron-builder) produces a DMG / NSIS / AppImage. **But note
the open item below before shipping.**

## Known open items (next steps, not done in this MVP)

1. **Bundle the Python sidecar.** Today the app assumes `cheetahclaws[web]` is
   pip-installed and on PATH. To ship to non-Python users, freeze the server
   with PyInstaller/Nuitka and spawn the bundled binary instead of the global
   `cheetahclaws`. Define a lean `core` install profile first (agent + web UI;
   trading/voice/video optional) so the bundle stays small.
2. **Code signing + notarization.** macOS Gatekeeper / Windows SmartScreen will
   block an unsigned build. Real (paid) prerequisite for public distribution.
3. **First-run onboarding.** A GUI provider/API-key step (the CLI's setup
   wizard, as a screen) — the main lever for reaching non-CLI users.
4. **Auto-update.** Wire electron-updater (or Tauri's updater) so users don't
   stay pinned to old builds.

## Why Electron here (and Tauri later)

This MVP is Electron because it only needs Node, which let the sidecar
integration be **actually run and verified** on the dev box (no Rust toolchain
was available). For the *shipped* product, **Tauri** is the better target — a
~5 MB Rust shell vs Electron's ~150 MB — and the sidecar logic in
[`src/sidecar.js`](src/sidecar.js) is intentionally framework-agnostic so it
ports across with only the window code rewritten.
