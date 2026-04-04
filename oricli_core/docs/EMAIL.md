# ORI Studio — Email Command System

ORI Studio ships a fully sovereign two-way email interface built on [Resend](https://resend.com).  
Control ORI from any email client — no app, no dashboard, no login required.

---

## Architecture

```
Outbound:  workflow step / command reply  →  _send_email()  →  Resend  →  recipient inbox
Inbound:   user email  →  inbound.thynaptic.com MX  →  Resend webhook  →  /v1/email/inbound  →  ORI
```

| Component | Value |
|-----------|-------|
| Sending domain | `thynaptic.com` (Resend-verified, SPF includes `amazonses.com`) |
| Inbound domain | `inbound.thynaptic.com` (MX → Resend; subdomain avoids apex MX conflict) |
| From address | `ori@thynaptic.com` (configurable via `EMAIL_FROM`) |
| Reply-To | `ori@inbound.thynaptic.com` |
| Webhook security | Svix HMAC (`RESEND_WEBHOOK_SECRET`) |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RESEND_API_KEY` | ✅ | Resend API key |
| `EMAIL_FROM` | — | From address. Default: `ORI Studio <ori@thynaptic.com>` |
| `RESEND_WEBHOOK_SECRET` | Recommended | Svix signing secret (`whsec_...`) from Resend webhook settings |

---

## Inbound Address

Every workspace gets a unique inbound address: **`{slug}@inbound.thynaptic.com`**

- Generated from the workspace owner's name on signup
- Stored in `.oricli/email_clients.json`
- The shared address `ori@inbound.thynaptic.com` also works (resolves by sender email)

---

## Commands

Send any command as the **email subject line**. Variables can be passed in the body (see below).

### Workflow Commands

| Subject | Description |
|---------|-------------|
| `LIST` | ORI replies with all available workflows as tap-to-run links |
| `RUN <workflow-name>` | Triggers workflow by name (case-insensitive) or ID prefix |
| `STATUS` | Last 5 run statuses |
| `STOP <run-id>` | Cancels a run (use first 8 chars of run ID) |
| `REPORT` | HTML table of last 10 runs with status + timing |

### Knowledge & Notes

| Subject | Description |
|---------|-------------|
| `NOTE <text>` | Saves a note to the server-side Notebook. ORI generates a 2–3 word title. |
| `ASK <question>` | ORI answers using your notes + recent run history as context |
| `BRIEF` | ORI sends your daily briefing immediately (same as the scheduled morning email) |

### Subscriptions

| Subject | Description |
|---------|-------------|
| `SUBSCRIBE <workflow> <schedule>` | Auto-run a workflow on a schedule. Results emailed. |
| `SUBSCRIPTIONS` | List all active subscriptions with cancel links |
| `UNSUBSCRIBE <workflow>` | Cancel a subscription |

**Schedule formats:**
```
SUBSCRIBE Claude Overview daily
SUBSCRIBE Claude Overview every monday
SUBSCRIBE Claude Overview every monday 9am
SUBSCRIBE My Report every friday at 5pm
SUBSCRIBE Status Check weekly
```
Defaults to `daily at 09:00` if no schedule is specified.

### Scheduling & Help

| Subject | Description |
|---------|-------------|
| `REMIND <text> <time>` | Sets a reminder. ORI emails you at the specified time. |
| `HELP` | Full command reference with tap-to-send mailto links |

**REMIND formats:**
```
REMIND call Acme tomorrow 9am
REMIND review proposal friday 2pm
REMIND check metrics today 3:30
```

---

## Passing Variables to Workflows

Include `key: value` pairs in the email body (one per line). These become `{{variables}}` in the workflow:

```
Subject: RUN client-invoice

client: Acme Corp
amount: $4,200
due_date: April 15
```

These inject into the workflow as `user_vars` and are accessible as `{{client}}`, `{{amount}}`, `{{due_date}}`.

---

## Reply Mode — Three Behaviors

When ORI sends you an email, it tracks the Resend message ID. Replying to any ORI email triggers one of three paths:

### 1. Approve / Reject (workflow approval loop)

| Reply (first line) | Action |
|--------------------|--------|
| `APPROVE`, `YES`, `OK`, `CONFIRM` | Sets `email_approved: true` on the run |
| `REJECT`, `NO`, `CANCEL`, `DENY` | Cancels the run |

Use this for human-in-the-loop workflows — ORI sends a notification step, you reply to approve or halt.

### 2. Contextual follow-up question

Reply with any question about the results — ORI loads the full run output as context and answers inline in the same thread via Ollama.

```
[ORI results email about "Claude Overview"]

You reply: "Can you give me the 3 most important points from this?"

ORI replies: "Based on the Claude Overview results: 1) ..."
```

### 3. New command in a reply

Start your reply with any known command (`RUN`, `LIST`, `SUBSCRIBE`, etc.) and ORI treats it as a fresh command regardless of the thread.

---

## Thread Store

Sent email threads are stored in `.oricli/email_threads.json`:
```json
{
  "<resend-message-id>": {
    "wf_id": "...",
    "run_id": "...",
    "sender": "client@example.com",
    "created": "2026-04-04T00:00:00Z"
  }
}
```

---

## Subscription Store

Active subscriptions are stored in `.oricli/subscriptions.json` and re-registered with APScheduler on every server boot:

```json
[
  {
    "id": "uuid",
    "client_email": "user@example.com",
    "wf_id": "wf-uuid",
    "wf_name": "Claude Overview",
    "cron_expr": "0 9 * * mon",
    "schedule_desc": "every Monday at 09:00",
    "created": "2026-04-04T00:00:00Z"
  }
]
```

---

## Client Management (REST API)

### Register a client

```http
POST /v1/email/clients
Authorization: Bearer <MAVAIA_API_KEY>
Content-Type: application/json

{ "email": "owner@theirbusiness.com", "name": "Jane" }
```

### Auto-register on signup (called by frontend)

```http
POST /v1/email/register
Content-Type: application/json

{ "email": "user@example.com", "name": "Mike", "workspace_id": "pb-record-id" }
```

Returns the assigned inbound address and fires an onboarding email.

### List clients

```http
GET /v1/email/clients
Authorization: Bearer <MAVAIA_API_KEY>
```

### Remove a client

```http
DELETE /v1/email/clients/owner@theirbusiness.com
Authorization: Bearer <MAVAIA_API_KEY>
```

### Trigger a briefing manually

```http
POST /v1/email/briefing/owner@theirbusiness.com
Authorization: Bearer <MAVAIA_API_KEY>
```

---

## Outbound — Send from a Workflow Step

In any `notify` step, use the `email:` prefix:

```
email: recipient@example.com | Subject line | Body text
```

If subject/body are omitted, the previous step's output is used.

### Via REST API

```http
POST /v1/email/send
Authorization: Bearer <MAVAIA_API_KEY>
Content-Type: application/json

{
  "to": "client@example.com",
  "subject": "Weekly Report",
  "body": "Plain text content",
  "html": "<p>Optional HTML override</p>"
}
```

---

## Inbound Webhook (Resend → ORI)

```
POST /v1/email/inbound
```

Resend posts a JSON payload. ORI processes in order:

1. **Svix signature verification** (if `RESEND_WEBHOOK_SECRET` set)
2. **Resolve inbound client** — by slug from `to` address, then by sender email
3. **Reply detection** — checks `In-Reply-To` header against thread store
4. **Command dispatch** — parses subject → command → handler

Unknown senders receive a friendly "you found ORI" email with the product pitch.

---

## Caddy Routing

`/v1/email/*` routes to Flask (5001) before the Go backbone rule:

```caddy
handle /v1/email/* {
    reverse_proxy 127.0.0.1:5001 { ... }
}
handle /v1/* {
    reverse_proxy 127.0.0.1:8089 { ... }
}
```

---

## SPF Record

`thynaptic.com` TXT record must include:
```
include:amazonses.com
```
(Resend uses SES infrastructure. Without this, Gmail will mark ORI emails as spam.)
