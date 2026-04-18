# Sovereign Docker Stack

**Document Type:** Technical Reference  
**Version:** v2.3.0  
**Status:** Active

Oricli-Alpha runs a fully sovereign Docker service stack alongside the Go backbone. Every dependency is local — no external cloud services required for core operation.

---

## Stack Overview

| Container | Image | Port(s) | Purpose |
|---|---|---|---|
| `oricli-searxng` | `searxng/searxng` | `127.0.0.1:8080` | Sovereign web search (CuriosityDaemon primary forager) |
| `oricli-browserless` | `browserless/chrome` | `127.0.0.1:3000` | Headless Chrome CDP endpoint (VDI Manager) |
| `oricli-minio` | `minio/minio` | `127.0.0.1:9000/9001` | S3-compatible local object storage (Ghost Cluster state) |
| `oricli-prometheus` | `prom/prometheus` | `127.0.0.1:9091` | Metrics scraper and time-series store |
| `oricli-grafana` | `grafana/grafana` | `127.0.0.1:9093` | Metrics visualisation (dashboards) |
| `oricli-cadvisor` | `gcr.io/cadvisor/cadvisor` | `127.0.0.1:9092` | Per-container CPU/RAM/network metrics |
| `oricli-neo4j` | `neo4j` | `0.0.0.0:7474/7687` | Persistent knowledge graph |
| `oricli-sandbox-pool-*` | `python:3.11-slim` | — | Gosh secure code execution sandboxes |

---

## Service Management

All containers are managed by systemd units that wrap `docker compose`. They start after `docker.service` and survive reboots.

```bash
# Status of all sovereign services
sudo systemctl status oricli-searxng oricli-browserless oricli-minio oricli-observability

# Restart a single service
sudo systemctl restart oricli-minio

# View logs
sudo docker logs oricli-grafana -f --tail 50
```

---

## 1. SearXNG — Sovereign Web Search

**Path:** `docker/searxng/`  
**Systemd:** `oricli-searxng.service`

Local meta-search engine. Aggregates Google, Bing, DuckDuckGo, and Wikipedia into a single clean JSON API. Used by `CuriosityDaemon` as its primary epistemic forager — no bot detection, no rate limits, no external API keys.

**Query API:**
```bash
curl "http://127.0.0.1:8080/search?q=sovereign+AI&format=json" | jq '.results[0]'
```

**Config:** `docker/searxng/settings.yml` — engines, privacy settings, JSON format.

---

## 2. Browserless / Chrome — Headless CDP

**Path:** `docker/browserless/`  
**Systemd:** `oricli-browserless.service`  
**Env var:** `ORICLI_BROWSERLESS_URL=ws://localhost:3000`

Runs a persistent headless Chrome instance and exposes the Chrome DevTools Protocol (CDP) over WebSocket. The `pkg/vdi/Manager` connects to it via `chromedp.NewRemoteAllocator` when `ORICLI_BROWSERLESS_URL` is set — no Chrome binary needed on the host.

**VDI priority chain:**
1. Remote CDP via `ORICLI_BROWSERLESS_URL` (browserless container) ← active
2. Local `chromedp.NewExecAllocator` (requires host Chrome install)

**Health check:**
```bash
curl http://localhost:3000/json/version | jq '.Browser'
# → "HeadlessChrome/121.0.x"
```

**Max concurrent sessions:** 5 (configurable via `MAX_CONCURRENT_SESSIONS` env).

---

## 3. MinIO — Sovereign S3 Storage

**Path:** `docker/minio/`  
**Systemd:** `oricli-minio.service`  
**S3 API:** `http://127.0.0.1:9000`  
**Web Console:** `http://127.0.0.1:9001` (admin: `oricli-admin`)

S3-compatible local object storage. Used by the JIT and Dream daemon training pipelines via `runpod_bridge.py`. The bridge reads `MAVAIA_S3_ENDPOINT` and passes it as `--endpoint-url` to all AWS CLI / boto3 calls — zero code changes required.

**Buckets:**
| Bucket | Purpose |
|---|---|
| `oricli-state` | Ghost Cluster session state, RunPod job artefacts |
| `oricli-models` | LoRA adapter checkpoints, training outputs |

**One-time bucket init:**
```bash
bash docker/minio/init.sh
```

**mc commands:**
```bash
mc ls oricli-local                        # list buckets
mc cp model.tar oricli-local/oricli-models/  # upload
mc ls oricli-local/oricli-state/          # inspect state
```

**Env vars set in `oricli-backbone.service`:**
```
MAVAIA_S3_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=oricli-admin
AWS_SECRET_ACCESS_KEY=oricli-sovereign-2025
AWS_BUCKET_NAME=oricli-state
AWS_DEFAULT_REGION=us-east-1
```

---

## 4. Observability — Prometheus + Grafana + cAdvisor

**Path:** `docker/observability/`  
**Systemd:** `oricli-observability.service`

Three-container stack providing full operational intelligence.

### Prometheus (`:9091`)
Scrapes metrics every 15 seconds from:
- **`oricli_backbone`** → `host.docker.internal:8089/v1/metrics` (Prometheus text format)
- **`cadvisor`** → per-container CPU, RAM, network stats

Config: `docker/observability/prometheus/prometheus.yml`

### Grafana (`:9093`)
Pre-provisioned with the Prometheus datasource. Login: `oricli-admin / oricli-sovereign-2025`.

Add dashboards:
- Import cAdvisor dashboard: ID `14282`
- Import Node Exporter Full: ID `1860` (if node_exporter added later)

### cAdvisor (`:9092`)
Scrapes Docker daemon directly — exposes per-container CPU, RAM, network I/O, and filesystem stats.

### Backbone Metrics (`/v1/metrics`)
Native Prometheus endpoint added to `ServerV2`. Exposes:

| Metric | Type | Description |
|---|---|---|
| `oricli_requests_total{module,operation}` | Counter | Total operation calls per module |
| `oricli_requests_succeeded_total{module,operation}` | Counter | Successful operations |
| `oricli_requests_failed_total{module,operation}` | Counter | Failed operations |
| `oricli_request_duration_avg_seconds{module,operation}` | Gauge | Average op duration |
| `oricli_backbone_info{version}` | Gauge | Static version label |

---

## Ports Reference

| Port | Service | Bound To |
|---|---|---|
| `8080` | SearXNG | `127.0.0.1` |
| `3000` | Browserless CDP | `127.0.0.1` |
| `9000` | MinIO S3 API | `127.0.0.1` |
| `9001` | MinIO Console | `127.0.0.1` |
| `9091` | Prometheus | `127.0.0.1` |
| `9093` | Grafana | `127.0.0.1` |
| `8082` | cAdvisor | `127.0.0.1` |
| `7474` | Neo4j HTTP | `0.0.0.0` |
| `7687` | Neo4j Bolt | `0.0.0.0` |
| `8089` | Backbone API | `0.0.0.0` (Caddy proxied) |

All internal services are bound to `127.0.0.1` — not exposed to the internet. Access via SSH tunnel or Caddy reverse proxy as needed.

---

## Adding a New Sovereign Service

Follow the established pattern:

1. Create `docker/<service>/docker-compose.yml` — bind port to `127.0.0.1:<port>`
2. Create `docker/<service>/oricli-<service>.service` — systemd unit wrapping `docker compose`
3. `sudo cp docker/<service>/oricli-<service>.service /etc/systemd/system/`
4. `sudo systemctl daemon-reload && sudo systemctl enable --now oricli-<service>`
5. Add any required env vars to `oricli-backbone.service` and `sudo systemctl daemon-reload && sudo systemctl restart oricli-backbone`
6. Update this document.
