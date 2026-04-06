# Product Topology

This repo is the shared ORI platform plus multiple product clients. Do not infer product identity from legacy folder names alone.

## Canonical products

| Product | Canonical ID | Current Path | App Type | Repo Mode | Status |
|---|---|---|---|---|---|
| ORI Studio | `studio` | `ui_sovereignclaw/` | Web | `in_tree` | Active |
| ORI Dev | `dev` | `products/ori-dev-web/` | Web | `nested_repo` | Active |
| ORI Home | `home` | `ORI-Home/` | Desktop (Electron) | `nested_repo` | Active |
| ORI Red | `red` | `vuln.ai/` | Web + backend | `nested_repo` | Active |
| oricli | `cli` | `cmd/oricli-cli/` | CLI | `in_tree` | Active |

## Deployment Notes

- ORI Studio is still served by the legacy Flask shell on `ui_app.py`, backed by `ui_static/`.
- ORI Dev is intended to be served as a built SPA from `products/ori-dev-web/dist/` using [scripts/start_ori_dev.sh](/home/mike/Mavaia/scripts/start_ori_dev.sh) and [ori-dev-ui.service](/home/mike/Mavaia/ori-dev-ui.service).
- The current live `oridev.thynaptic.com` route was patched into Caddy through its admin API and should be made persistent in `/etc/caddy/Caddyfile`. Permanent config is documented in [ORI_DEV_DEPLOY.md](/home/mike/Mavaia/docs/ORI_DEV_DEPLOY.md).
- ORI Home and ORI Red manage their own product-specific runtime inside their nested repos.

## Public brand aliases

| Product | Public brand |
|---|---|
| ORI Red | `vuln.ai` |

Internally, treat `vuln.ai` as the public brand for `ORI Red`, not as a separate unrelated product.

## Canonical Domains

| Surface | Domain | Role |
|---|---|---|
| ORI Studio | `oristudio.thynaptic.com` | Customer-facing Studio product |
| ORI Dev | `oridev.thynaptic.com` | Customer-facing Dev product |
| ORI Home | `home.thynaptic.com` | Reserved public-facing Home surface |
| ORI Red | `red.thynaptic.com` | Customer-facing Red product |
| Shared API / auth / runtime | `glm.thynaptic.com` | Shared API surface already used for JIT auth and first-party clients |
| Docs | `docs.thynaptic.com` | Documentation |
| Generic dev / staging / scratch | `dev.thynaptic.com` | Non-product infra domain |
| Demo | `demo.thynaptic.com` | Demos |

Current shared origin behind Cloudflare: `85.31.233.157`

### Domain rules

- Product domains should use explicit product names, not generic nouns.
- `dev.thynaptic.com` is reserved for infra, staging, previews, or scratch services, not the ORI Dev product.
- `glm.thynaptic.com` stays stable as the neutral API/auth/runtime endpoint.
- Public brand aliases like `vuln.ai` can coexist with canonical product domains.

## Legacy surfaces

| Surface | Paths | Notes |
|---|---|---|
| Studio Flask layer | `ui_app.py`, `oricli_core/`, `ui_static/` | Older Python/Flask Studio shell still wired into services, scripts, and docs. Migrate-first, not removable yet |

## Rules

- Use `config/products.json` as the machine-readable source of truth.
- Prefer canonical product names in docs, config, and code comments.
- Treat legacy folder names such as `ui_sovereignclaw` as transitional, not architectural.
- `oricli` is a tool/runtime surface, not a peer end-user product to Studio, Dev, Home, and Red.

## Nested Repo Policy

- `products/ori-dev-web/`, `ORI-Home/`, and `vuln.ai/` are currently nested Git repos inside the platform workspace.
- Make code changes and commits inside those repos when the change belongs to the product client itself.
- Do not flatten or absorb those repos into the platform repo by accident.
- If we later choose submodules or a full flattening migration, that should be a deliberate history-preserving move, not incidental cleanup.

## Dead Code Sweep Order

1. `oricli_ui/` has been retired from the repo.
   Any remaining `oricli_ui` mentions should be treated as stale text, not a live dependency.
2. `oricli.py` and `oricli_client.py` have been retired from the repo.
   Any remaining mentions should be treated as historical notes, not live dependencies.
3. Keep `ui_app.py`, `oricli_core/`, and `ui_static/` until replacement work is complete.
   They are still invoked by service units and startup scripts.
