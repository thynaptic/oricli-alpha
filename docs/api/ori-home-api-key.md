# ORI Home API Key

Generated: 2026-04-10

## Key

```
glm.SVqzMhu2.rJUGN2mQvYkaXd6FKhGM8r7oJ5LIp7E3
```

## Details

| Field | Value |
|---|---|
| Base URL | `https://glm.thynaptic.com/v1` |
| Tenant ID | `app:ori-home:ori-home-desktop-v1` |
| Format | `Authorization: Bearer glm.SVqzMhu2.rJUGN2mQvYkaXd6FKhGM8r7oJ5LIp7E3` |

## Scopes

- `runtime:chat`
- `runtime:email:send`
- `runtime:models`
- `runtime:spaces`
- `runtime:workspaces`

## Notes

- Re-register on first boot via `POST /v1/app/register` with `ORI_APP_REG_TOKEN` if you need a per-device key (change `device_id`).
- Session history is surface-isolated
