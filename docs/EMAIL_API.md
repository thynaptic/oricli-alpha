# ORI Email API

ORI Studio ships a fully sovereign two-way email interface built on [Resend](https://resend.com).  
SMB clients and workspace owners can **send emails** from ORI workflows and **control ORI via email replies** — no app required.

---

## Architecture

```
Outbound:  ORI workflow step  →  _send_email()  →  Resend  →  recipient inbox
Inbound:   recipient email    →  inbound.thynaptic.com MX  →  Resend webhook  →  /v1/email/inbound  →  ORI
```

- **Sending domain:** `thynaptic.com` (verified in Resend)
- **Inbound domain:** `inbound.thynaptic.com` (MX → Resend, subdomain — no conflict with Hostinger MX on apex)
- **From address:** `ori@thynaptic.com` (configurable via `EMAIL_FROM` env var)
- **Webhook security:** Svix HMAC signature verification (`RESEND_WEBHOOK_SECRET`)

---

## Environment Variables

| Variable | Description |
|---|---|
| `RESEND_API_KEY` | Resend API key (required for sending) |
| `EMAIL_FROM` | From address, e.g. `ORI Studio <ori@thynaptic.com>` |
| `RESEND_WEBHOOK_SECRET` | Svix signing secret from Resend webhook settings (`whsec_...`) |

---

## Outbound — Send Email

### From a workflow step

In any workflow `notify` step, use the `email:` prefix:

```
email: recipient@example.com | Subject line | Body text
```

If the subject/body are omitted, the previous step's output is used as the body.

### Via REST API

```http
POST /v1/email/send
Authorization: Bearer <MAVAIA_API_KEY>
Content-Type: application/json

{
  "to": "client@example.com",
  "subject": "Weekly Report",
  "body": "Plain text fallback",
  "html": "<p>Optional HTML version</p>"
}
```

`to` accepts a string or array of addresses.

**Response:**
```json
{ "ok": true, "message": "Email sent (id=abc123)", "message_id": "abc123" }
```

---

## Inbound — Email Command Interface

SMB clients and authorized users can operate ORI directly from their inbox.  
Send any email to **any address `@inbound.thynaptic.com`**.

### Authorization

Only registered senders are processed. Unknown senders are silently ignored.

**Register a client:**
```http
POST /v1/email/clients
Authorization: Bearer <MAVAIA_API_KEY>
Content-Type: application/json

{ "email": "owner@theirbusiness.com", "name": "Jane" }
```

**List clients:**
```http
GET /v1/email/clients
Authorization: Bearer <MAVAIA_API_KEY>
```

**Remove a client:**
```http
DELETE /v1/email/clients/owner@theirbusiness.com
Authorization: Bearer <MAVAIA_API_KEY>
```

### Commands (Subject line)

| Subject | Action |
|---|---|
| `LIST` | ORI replies with all available workflows |
| `RUN <workflow-name>` | Triggers workflow by name (case-insensitive) or ID prefix |
| `STATUS` | ORI replies with 5 most recent run statuses |
| `STOP <run-id>` | Cancels a running workflow (use first 8 chars of run ID) |
| Anything else | ORI replies with the command reference |

### Passing variables to a workflow

Include `key: value` pairs in the email body (one per line):

```
Subject: RUN client-invoice

client: Acme Corp
amount: $4,200
due_date: April 15
```

These are injected as `user_vars` into the workflow run context and accessible as `{{client}}`, `{{amount}}`, etc. in step inputs.

### Example session

```
You  →  ori@inbound.thynaptic.com   Subject: LIST
ORI  →  You                         "Available workflows: • Weekly Report • Client Invoice..."

You  →  ori@inbound.thynaptic.com   Subject: RUN Weekly Report
ORI  →  You                         "Workflow 'Weekly Report' has started. Run ID: a1b2c3d4..."

You  →  ori@inbound.thynaptic.com   Subject: STATUS
ORI  →  You                         "Recent runs: • Weekly Report: done (run a1b2c3d4…)"
```

---

## Reply Mode — Workflow Approval Loop

When a workflow `notify` step sends an email, ORI tracks the Resend message ID.  
If the recipient **replies** to that email, ORI matches the `In-Reply-To` header and processes the reply:

| Reply (first line) | Action |
|---|---|
| `APPROVE`, `YES`, `OK`, `CONFIRM` | Sets `email_approved: true` on the run |
| `REJECT`, `NO`, `CANCEL`, `DENY` | Cancels the run |
| Anything else | Logged as a free-form reply on the run |

This enables **async human-in-the-loop workflows** — ORI sends a notification, the SMB owner replies to approve or reject, ORI continues or halts. No app login required.

---

## Thread Store

Sent email threads are stored in `.oricli/email_threads.json`:
```json
{
  "<resend-message-id>": {
    "wf_id": "...",
    "run_id": "...",
    "sender": "client@example.com",
    "created": "2026-04-03T21:00:00Z"
  }
}
```

Authorized email clients are stored in `.oricli/email_clients.json`.

---

## Caddy Routing

`/v1/email/*` is carved out before the `/v1/*` → Go backbone rule in `oristudio.thynaptic.com`, routing to Flask (5001):

```caddy
handle /v1/email/* {
    reverse_proxy 127.0.0.1:5001 { ... }
}
handle /v1/* {
    reverse_proxy 127.0.0.1:8089 { ... }  # Go backbone
}
```

---

## Roadmap (Option C)

Move email send/receive natively into the Go backbone (`pkg/api/server.go`) calling Resend REST API directly — no Python SDK, no Flask dependency. Tracked as backburner.
