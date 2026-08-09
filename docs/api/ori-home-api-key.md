# ORI Home API Key

## Key

Provision a tenant key via the admin API or app registration — **do not commit live keys**.

```bash
# Owner/admin key from ORICLI_SEED_API_KEY / .oricli/api_key
curl -s -X POST https://glm.thynaptic.com/v1/admin/tenants/app:ori-home/keys \
  -H "Authorization: Bearer $ORICLI_SEED_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scopes":["runtime:chat","runtime:email:send","runtime:models","runtime:spaces","runtime:workspaces"]}'
```

Or on first boot use `POST /v1/app/register` with `ORI_APP_REG_TOKEN` to mint a per-device key.

| Field | Value |
|---|---|
| Base URL | `https://glm.thynaptic.com/v1` |
| Tenant ID | `app:ori-home:ori-home-desktop-v1` |
| Format | `Authorization: Bearer glm.<prefix>.<secret>` |

## Scopes

- `runtime:chat`
- `runtime:email:send`
- `runtime:models`
- `runtime:spaces`
- `runtime:workspaces`

## Notes

- Any previously committed key material in this file has been revoked/rotated — treat historical copies as compromised.
- Session history is surface-isolated.
