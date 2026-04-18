# SMB Tenant Constitution

ORI Studio supports a **Tenant Constitution** — a per-deployment behavioral layer that lets operators customize Oricli's identity, add rules, and define banned topics without modifying code.

---

## Security Model

The constitution system has three layers, stacked in order of precedence:

```
┌──────────────────────────────────────────┐
│  Tenant Constitution  (.ori file)        │  ← operator-editable
│  @persona, @company, <rules>, <banned>   │
├──────────────────────────────────────────┤
│  Living Constitution  (learned prefs)    │  ← dynamic, per-user
│  learned from interactions via Imprint   │
├──────────────────────────────────────────┤
│  Core Sovereign Rules (compiled binary)  │  ← immutable
│  anti-sycophancy, identity integrity,    │
│  injection resistance, fabrication bans  │
└──────────────────────────────────────────┘
```

**The compiled core always wins.** The Tenant Constitution can:
- ✅ Add a custom identity/persona on top of the sovereign layer
- ✅ Add operator-specific behavioral rules
- ✅ Add banned topics that Ori will decline gracefully
- ❌ Cannot remove or override core anti-sycophancy rules
- ❌ Cannot enable prompt injection or social engineering vulnerabilities
- ❌ Cannot make Ori claim to be human or fabricate system status

---

## Deployment

1. Copy `constitution.example.ori` to your deployment path:
   ```bash
   cp constitution.example.ori /etc/oricli/constitution.ori
   ```

2. Edit the file with your company details (see [Format](#format) below).

3. Set the environment variable:
   ```bash
   ORICLI_TENANT_CONSTITUTION=/etc/oricli/constitution.ori
   ```
   Or in your systemd service file:
   ```ini
   Environment=ORICLI_TENANT_CONSTITUTION=/etc/oricli/constitution.ori
   ```

4. Restart the backbone:
   ```bash
   sudo systemctl restart oricli-api
   ```

The constitution is loaded once at startup. To apply changes, restart the service.

---

## Format

The `.ori` format uses `@key: value` directives and `<block>...</block>` sections.

### Directives

| Directive | Description |
|-----------|-------------|
| `@name` | Display name for this deployment |
| `@persona` | Custom assistant name shown to users |
| `@company` | Company/organization name |

### Blocks

#### `<identity_override>`
Replaces the "presented as" persona. The sovereign core identity (Ori's reasoning engine, rules, memory) is unchanged — this only affects how Ori introduces itself to users.

```
<identity_override>
You are Aria, the internal AI assistant for Acme Corp.
When users ask who you are, say you're Aria, Acme's assistant.
</identity_override>
```

#### `<rules>`
Additive behavioral constraints. These are injected as hard operator rules into every system prompt.

```
<rules>
- Always respond in formal English
- Do not answer questions outside of HR, Finance, and IT
- Never discuss competitor products by name
</rules>
```

Lines must start with `- ` or `* ` (bullet format).

#### `<banned_topics>`
Topics Ori will decline gracefully without engaging, lecturing, or explaining in detail.

```
<banned_topics>
- salary negotiation
- personal legal advice
- political commentary
</banned_topics>
```

---

## Full Example

```
@name: Acme Corp AI Assistant
@persona: Aria
@company: Acme Corp

<identity_override>
You are Aria, the internal AI assistant for Acme Corp.
</identity_override>

<rules>
- Always respond in formal English
- Scope responses to HR, Finance, and IT topics only
- Refer legal questions to the Legal department
</rules>

<banned_topics>
- salary negotiation
- personal medical advice
- political opinions
</banned_topics>
```

See `constitution.example.ori` at the repo root for the full annotated template.

---

## Character Budget

The tenant layer is capped at **600 characters** in the injected system prompt to protect context window efficiency. Long identity overrides and rule lists are truncated cleanly at the cap. Keep rules concise.

---

## Troubleshooting

**Constitution not loading:**
- Check the path is correct and the file is readable by the oricli process
- Check logs: `journalctl -u oricli-api | grep TenantConstitution`
- If the file fails to parse, the tenant layer is disabled (core rules still apply)

**Rules not taking effect:**
- Restart the service — the constitution is loaded once at boot
- Verify the rules appear in the `<rules>` block with `- ` bullet format
- Check character budget: rules beyond ~600 chars total are truncated
