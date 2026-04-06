# ORI Studio — Changelog

All notable changes to the ORI Studio Flask UI layer (`ui_app.py`, `ui_sovereignclaw/`).  
Newest first. Dates are UTC.

---

## [Unreleased]

---

## 2026-04-04

### Added — Email Subscriptions
- `SUBSCRIBE <workflow> <schedule>` command — auto-runs a workflow on a cron schedule and emails results
- `SUBSCRIPTIONS` command — lists all active subscriptions with cancel links
- `UNSUBSCRIBE <workflow>` command — cancels a subscription
- Subscription store: `.oricli/subscriptions.json`, persisted across restarts
- `_schedule_subscription()`, `_fire_subscription()`, `_boot_subscriptions()` helpers
- `_boot_subscriptions()` called on Flask startup to re-register all active subs with APScheduler
- Schedule parser supports: `daily`, `every day`, `weekly`, `every monday`, `every friday at 5pm`, `every monday 8:30`, etc.

### Added — Contextual Reply Threading
- Replying to any ORI results email with a question now triggers a contextual Ollama answer
- ORI loads the run's full `final_output` as context and answers inline in the same email thread
- Hard commands (`RUN`, `LIST`, `SUBSCRIBE`, etc.) in a reply still fall through to command mode
- `APPROVE`/`REJECT` replies still handled as before (workflow approval loop)
- Fixed: completion emails now pass `wf_id=` and `run_id=` to `_send_email()` so the thread is registered and replies are matchable

### Added — Board Page (server-side)
- `GET /api/board` endpoint — returns all `done` runs with `final_output`, type classification, source badge
- Smart title inference from output when `wf_name` is missing (strips markdown, skips TL;DR/URL lines)
- `BoardPage.jsx` fully rewritten — fetches from `/api/board`, no more localStorage dependency
- Auto-refresh every 30 seconds
- Sort: Newest / Oldest / A→Z
- Filter pills: source (email / manual / scheduled) + type (report / research / summary / draft / other)
- Per-card dismiss (hidden list in localStorage), "Restore N hidden" pill to undo
- "via email" badge with Mail icon on email-triggered cards
- Click card → full output modal with markdown rendering (react-markdown + remark-gfm)
- Markdown modal: headers, bold, lists, code blocks, tables, links, blockquotes, HR — all dark-themed

### Added — `wf_name` stored at run creation
- `/workflows/<wf_id>/run` now stores `wf_name` in the run record at creation time
- `triggered_by` field now included in manual API-triggered runs
- Board and REPORT now show correct workflow names even after workflows are deleted

### Fixed — HELP command updated
- Added SUBSCRIBE / UNSUBSCRIBE / SUBSCRIPTIONS to the HELP reference email with tap links

---

## 2026-04-03

### Added — SUBSCRIBE groundwork (KNOWN_CMDS)
- `SUBSCRIBE`, `UNSUBSCRIBE`, `SUBSCRIPTIONS` added to `KNOWN_CMDS` set in inbound handler

---

## 2026-04-02

### Added — NOTE / ASK / BRIEF / REMIND / REPORT / HELP commands
- `NOTE <text>` — saves to server-side Notebook, Ollama generates a 2–3 word title
- `ASK <question>` — Ollama answers using notes + recent run history as context
- `BRIEF` — triggers `_send_briefing()` immediately on demand
- `REMIND <text> <time>` — regex time parser + APScheduler one-shot job
- `REPORT` — last 10 runs as HTML table with status icons and colour coding
- `HELP` — full command reference with tap-to-send mailto links

### Added — Server-side Notebook API
- `GET/POST/PATCH/DELETE /api/notes` — persisted to `.oricli/notes.json`
- `NotebookPage.jsx` migrated from localStorage to server API
- Auto-migrates existing localStorage notes on first load
- 800ms debounce save with "Saving…" indicator

### Added — Per-user inbound address
- Each client gets a unique `{slug}@inbound.thynaptic.com` at registration
- Inbound handler resolves by slug first, then sender email as fallback
- Slug generated from display name, deduplicated against existing slugs

### Added — Auto-register on signup
- `POST /v1/email/register` — public endpoint, called from `store.js` after PocketBase register
- Generates workspace slug, assigns inbound address, fires onboarding email

### Added — Onboarding email
- Sent via `/v1/email/register` to new users
- Personalised with their inbound address + 3 tap-to-try mailto links

### Added — Timezone-aware greetings
- `_local_now()`, `_greeting()`, `_fmt_local()` helpers using `zoneinfo`
- Briefing greeting (Good morning / afternoon / evening) derived from client's stored timezone
- Falls back to UTC on any error

### Fixed — REPORT shows deleted workflow names
- Run records now store `wf_name` at creation via the RUN command handler
- REPORT uses `wf_map.get(wf_id, r.get("wf_name", "Deleted workflow"))` pattern
- No more `?` in REPORT output for workflows that have since been deleted

---

## 2026-04-01

### Added — RUN end-to-end via email
- `RUN <workflow>` command — triggers workflow, emails confirmation, emails results on completion
- Completion email added to `_run_workflow_job` when `status=done` and `triggered_by=email:`
- HTML content extraction via BeautifulSoup (strips nav/header/footer/aside, prefers `<main>/<article>`)
- Lines < 40 chars filtered before Ollama summarisation
- Ollama summarises to 3–5 sentences for clean email output; falls back to raw truncated text

### Added — Two-way email threading
- Thread store: `.oricli/email_threads.json` (message-ID → run context)
- `_register_email_thread()` called when any ORI email is sent with `wf_id` + `run_id`
- Inbound handler checks `In-Reply-To` header to match reply to run

### Fixed — Flask env loading
- Created `scripts/start_ui.sh` — sources `.env` before `exec python3 ui_app.py`
- Fixes `RESEND_API_KEY` not being available in nohup grandchild processes
- Canonical restart method: `nohup /home/mike/Mavaia/scripts/start_ui.sh >> /tmp/oristudio_ui.log 2>&1 &`

### Fixed — SPF / Gmail spam
- Added `include:amazonses.com` to `thynaptic.com` TXT DNS record
- Resend uses SES infrastructure; without this Gmail marked ORI emails as spam

### Fixed — Email threading / reply detection
- `In-Reply-To` check now runs before command parsing
- If first word of reply body is a known command, `thread = None` to fall through to command mode
- Watch/mobile reply (empty body, Re: subject) handled by self-contained mailto footer on every email

---

## 2026-03-31

### Added — Email command system (initial)
- `LIST` command — replies with all workflows as tap-to-run mailto links
- `STATUS` command — last 5 run statuses
- `STOP <run-id>` command — cancels a running workflow
- Authorized client store: `.oricli/email_clients.json`
- `GET/POST/DELETE /v1/email/clients` — manage authorized senders
- `POST /v1/email/inbound` — Resend inbound webhook with Svix signature verification
- `_ori_action_footer()` — standard tap-link footer appended to every outbound email
- `_body_to_html()` — auto-converts plain text to HTML with clickable `label → mailto:` links
- `_send_email()` — Resend sender, always sends multipart text+HTML

---

## Earlier

See `conductor/workflow.md` and git history for pre-email-system changes.
