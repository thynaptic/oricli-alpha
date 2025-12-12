---
name: flask-chat-ui
overview: Add a Claude-like local Flask chat UI wired to the existing OpenAI-compatible chat endpoint for testing Mavaia end-to-end, including message edit/resend, regenerate, inline citation display, theme toggle, history, and attachment passthrough.
todos:
  - id: bootstrap-flask
    content: Add Flask UI app, static routes, proxy /chat
    status: completed
  - id: build-frontend
    content: Implement HTML/CSS/JS Claude-like chat UI
    status: completed
  - id: attachments
    content: Add attachment picker and base64 passthrough
    status: completed
  - id: history
    content: Persist chat thread, support new thread/reset
    status: completed
  - id: stream-test
    content: Test end-to-end against local API
    status: completed
---

# Flask Chat UI Plan

## Scope

Build a Claude-like local Flask chat UI that calls the existing OpenAI-compatible chat endpoint on localhost:8000. Support SSE streaming, message edit/resend, regenerate, inline citation/tool-call display, light/dark themes, thread persistence, attachment passthrough (base64), settings panel, and stub events hook.

## Steps

1) Backend (Flask)

- Add Flask app (e.g., `ui_app.py` or `mavaia_core/ui/app.py`) with routes: `/` SPA HTML, `/static/*` assets, `/chat` proxy → `http://localhost:8000/v1/chat/completions` with SSE and AbortController support, `/models` proxy → `/v1/models`, `/health` returning `{ "ok": true }`, and stub `/events` for future logs/traces.
- Implement backoff + retry in proxy for network errors; enforce attachment size cap.

2) Frontend layout & theming

- Single-page HTML with Claude-like bubbles, typing indicator, fade-in on completion, optional resizable sidebar. Light/dark theme via CSS vars persisted in localStorage.

3) Chat interactions

- Vanilla JS managing state: messages array with states (pending/streaming/complete/error), thread metadata, settings persisted in localStorage. Functions: `sendMessage`, `streamResponse`, `stopGeneration` (AbortController), `retryLast` with backoff, `editAndResend`, `regenerate` (resend last user). Streaming renderer token-by-token, auto-scroll with user-controlled lock.

4) Attachments

- File input → base64, inline preview for images, attach as OpenAI-format content blocks in message payload. Enforce small size limit; show chips in UI.

5) Threads & settings panel

- Store full conversation threads in localStorage; thread list with IDs/titles, rename, auto-restore last thread, new-thread reset. Settings panel for endpoint URL, model dropdown (fetched from `/models`), temperature slider, system prompt editor, all synced to localStorage.

6) Testing hooks

- Document how to run (`python ui_app.py`), verify chat end-to-end vs local API, and leave `/events` stub ready for future CoT/module tracing.

## Notes

- Minimal deps: Flask + vanilla JS/CSS only. Mirror Claude UX (bubbles, inline citations, regenerate/edit affordances, smooth scroll anchoring, streaming placeholder, typing indicator). Handle CORS/JSON streaming in proxy route.
- Keep code ASCII and concise.
- Add small attachment limit and basic error box with Retry button.