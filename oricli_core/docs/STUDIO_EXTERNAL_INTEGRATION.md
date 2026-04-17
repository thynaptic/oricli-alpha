# ORI Studio — External Integration Guide (STUDIO)

Status: Implementation Reference

This guide covers Studio-specific integration surfaces: webhooks, the email command interface, OAuth connections, and MCP tool servers.

For the core Go backbone platform reference, see:
- [API.md](/home/mike/Mavaia/docs/API.md)
- [AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)

---

## Overview

ORI Studio exposes five integration surfaces:

| Surface | Use case |
|---|---|
| **Workflow webhooks** | Trigger runs from external events (CI, Zapier, n8n, etc.) |
| **Email commands** | Human-in-the-loop automation via any email client |
| **OAuth connections** | Pull data from Notion, GitHub, Google, HubSpot, Jira |
| **MCP servers** | Attach tool providers to the AI backbone |
| **Direct API** | Full programmatic access via the OpenAI-compatible REST API |

---

## 1. Workflow Webhooks

Assign a `webhookKey` to any workflow in the UI (Settings → Workflow → Trigger), then fire it from any HTTP client.

```bash
POST https://oricli.thynaptic.com/workflows/webhook/<webhook_key>
Content-Type: application/json

{
  "vars": {
    "topic": "EU AI Act",
    "output_format": "bullet_points"
  }
}
```

**Response:**
```json
{ "run_id": "8f3e...", "status": "queued" }
```

**Poll the result:**
```bash
GET https://oricli.thynaptic.com/workflows/runs/8f3e...
```

**When `status == "done"`:**
```json
{
  "id": "8f3e...",
  "status": "done",
  "final_output": "...",
  "triggered_by": "webhook"
}
```

### Example: GitHub Actions

```yaml
- name: Trigger ORI weekly report
  run: |
    curl -s -X POST $ORI_WEBHOOK_URL \
      -H "Content-Type: application/json" \
      -d '{"vars": {"branch": "${{ github.ref_name }}"}}'
```

### Example: n8n / Zapier

Use the **HTTP Request** node with `POST` method and the webhook URL. No auth required for webhook endpoints (key acts as the secret).

---

## 2. Email Command Interface

ORI Studio responds to emails sent to your workspace inbound address:

```
{workspace_slug}@inbound.thynaptic.com
```

You receive this address in your onboarding email. You can also find it under **Settings → Email**.

### How it works

1. You send an email to your inbound address
2. Resend receives it and POSTs to `POST /v1/email/inbound` via Resend's inbound webhook
3. ORI parses the subject line for a command keyword
4. ORI runs the command and replies to you with the result

### Supported commands

| Subject | Action |
|---|---|
| `LIST` | Lists all your workflows with tap-to-run links |
| `RUN <workflow name>` | Triggers a workflow and emails you when done |
| `STATUS` | Last 5 run statuses |
| `STOP <run-id>` | Cancels a running workflow |
| `SUBSCRIBE <workflow> <schedule>` | Auto-run on a cron schedule, email results |
| `UNSUBSCRIBE <workflow>` | Cancel a subscription |
| `SUBSCRIPTIONS` | List all active subscriptions |
| `NOTE <text>` | Save a note to your Notebook |
| `ASK <question>` | AI answer using your notes + run history as context |
| `BRIEF` | Send your on-demand briefing now |
| `REMIND <text> <time>` | Set a one-shot reminder via email |
| `REPORT` | Last 10 runs as a formatted table |
| `HELP` | Full command reference with tap links |

### Reply threading

After a `RUN` completes, ORI sends you a results email. You can **reply to that email** with a follow-up question:

> "What were the key risks mentioned?"

ORI loads the run's full output as context and answers inline in the same thread. Any hard command (`RUN`, `LIST`, etc.) in a reply still executes as a command.

### Schedule syntax (SUBSCRIBE)

```
SUBSCRIBE Weekly Report every monday 9am
SUBSCRIBE Daily Standup daily
SUBSCRIBE News Brief every friday at 5:30pm
SUBSCRIBE Status every weekday 8am
```

Supported patterns:
- `daily` / `every day` → midnight UTC
- `every <DOW>` → weekly on that day (midnight UTC unless time given)
- `every <DOW> <time>` → weekly, specific time
- `every weekday` → Mon–Fri
- `hourly` → every hour

Time formats: `9am`, `9:30am`, `14:00`, `2pm`

### Setting up inbound routing (self-hosted)

1. In Resend, configure an inbound route for `@inbound.yourdomain.com` → your ORI inbound URL
2. Add the Resend webhook signing secret to `.env` as `RESEND_WEBHOOK_SECRET`
3. Caddy (or nginx) must proxy `POST /v1/email/inbound` to Flask on port 5001
4. Add SPF: `include:amazonses.com` to your domain's TXT record (Resend uses SES infrastructure)

**Example Caddyfile:**
```
oricli.yourdomain.com {
  reverse_proxy /v1/email/* localhost:5001
  reverse_proxy * localhost:8089
}
```

---

## 3. OAuth Connections

ORI Studio supports OAuth-based read access to external services. Connected sources are indexed into the RAG store and automatically injected as context in `/chat` calls.

### Supported providers

| Provider | Scopes | What gets indexed |
|---|---|---|
| **Google Workspace** | `gmail.readonly`, `drive.readonly` | Emails, Drive docs |
| **Notion** | `read_content` | Pages, databases |
| **GitHub** | `repo`, `read:org` | Issues, PRs, READMEs |
| **HubSpot** | `contacts`, `crm.objects.deals.read` | Contacts, deals |
| **Jira** | `read:jira-work` | Issues, sprints |

### OAuth flow

1. Navigate to **Settings → Connections** in the UI
2. Click **Connect** on your provider
3. Complete the OAuth consent screen
4. ORI stores the access token and begins indexing

**Manual index trigger:**
```bash
POST /api/connections/<conn_id>/index
```

**Index status:**
```bash
GET /api/connections/index/status
```

**Test a connection:**
```bash
POST /api/connections/<conn_id>/test
```

### Google OAuth (self-hosted setup)

1. Create a Google Cloud project
2. Enable Gmail API + Drive API
3. Create OAuth 2.0 credentials (web app)
4. Set callback URI: `https://oricli.yourdomain.com/api/connections/oauth/callback/google`
5. Add to `.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=https://oricli.yourdomain.com/api/connections/oauth/callback/google
   ```

---

## 4. MCP Tool Servers

The Model Context Protocol (MCP) lets you attach external tool providers to ORI's AI backbone. ORI loads the active MCP config from `oricli_core/mcp_config.json` at startup.

### Add via API

```bash
POST /mcp/servers
Content-Type: application/json

{
  "id": "github",
  "name": "GitHub MCP",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": { "GITHUB_TOKEN": "ghp_..." },
  "enabled": true
}
```

### Add via config file

Edit `.oricli/mcp_servers.json` (or `oricli_core/mcp_config.json` directly):

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/mike/Mavaia"]
    },
    "brave_search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": { "BRAVE_API_KEY": "BSA..." }
    }
  }
}
```

Then reload:
```bash
POST /mcp/reload
```

### Common MCP servers

| Package | Purpose |
|---|---|
| `@modelcontextprotocol/server-github` | GitHub issues, PRs, code |
| `@modelcontextprotocol/server-filesystem` | Local file read/write |
| `@modelcontextprotocol/server-brave-search` | Web search via Brave |
| `@modelcontextprotocol/server-slack` | Slack messages |
| `@modelcontextprotocol/server-postgres` | Direct DB queries |

---

## 5. Telegram

ORI Studio supports a Telegram webhook for direct-message interactions.

```bash
POST /api/connections/telegram/webhook
```

Configure your Telegram bot to POST updates to this URL. The handler extracts the message text, processes it as a chat message, and sends the response back via the Telegram API.

**Setup:**
```
TELEGRAM_BOT_TOKEN=...
```

---

## 6. Notion Builder

ORI can generate and push Notion pages from templates.

```bash
POST /api/notion/build
Content-Type: application/json

{
  "template_id": "weekly_report",
  "vars": {
    "title": "Week 14 Report",
    "content": "..."
  }
}
```

**List available templates:**
```bash
GET /api/notion/templates
```

---

## 7. Slack & Teams

Slack and Teams integrations are available for reading/sending messages and triggering workflows from channel messages.

```bash
GET /api/slack-integrations
GET /api/teams-integrations
```

Full setup is covered in `ONBOARDING.md` under the Connections section.

---

## Environment Variables

| Variable | Description |
|---|---|
| `RESEND_API_KEY` | Resend API key for outbound + inbound email |
| `RESEND_WEBHOOK_SECRET` | Svix signing secret for inbound webhook verification |
| `RESEND_FROM_EMAIL` | From address for outbound email (e.g. `ori@thynaptic.com`) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Google OAuth callback URL |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `MAVAIA_API_BASE` | Go backbone URL (default: `http://localhost:8089`) |
| `MAVAIA_API_KEY` | Bearer token for backbone auth |
| `MAVAIA_REQUIRE_AUTH` | Enable auth enforcement (`true`/`false`) |

---

## Security notes

- **Webhook keys** act as the secret — treat them like API keys. Rotate them in the workflow settings.
- **Inbound email** is verified via Svix HMAC signature before processing. Never disable `RESEND_WEBHOOK_SECRET` in production.
- **OAuth tokens** are stored in `.oricli/connections.json`. This file must not be committed to source control (it is in `.gitignore`).
- **MCP `env` fields** may contain secrets. `.oricli/mcp_servers.json` is also gitignored. Prefer loading secrets from the environment at MCP server startup rather than storing them in the config JSON.
