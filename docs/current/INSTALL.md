# Oricli-Alpha Installation Guide

**Version:** 2.1.0 — Go-native backbone

---

## System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Linux (Ubuntu 22.04+) | Ubuntu 22.04 LTS |
| CPU | 4 cores | 32-core AMD EPYC |
| RAM | 8 GB | 32 GB |
| Go | 1.21+ | 1.25+ |
| Python | 3.11+ | 3.11 or 3.12 |
| Ollama | Any | Latest |

---

## 1. Install Go

```bash
# Download and install Go 1.25+
wget https://go.dev/dl/go1.25.0.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.25.0.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
go version
```

---

## 2. Install Ollama (embeddings only)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull all-minilm
ollama pull nomic-embed-text
```

Ollama is used for semantic embeddings only (memory recall, response cache dedup, SCL indexing, TCD drift). All reasoning goes through Oracle (Copilot SDK).

---

## 3. Clone & Build

```bash
git clone https://github.com/thynaptic/oricli-alpha.git
cd oricli-alpha

# Build the Go backbone
go build -o bin/oricli-go-v2 ./cmd/backbone
```

---

## 4. Python Environment (UI + Sidecars)

The Python stack is only required for the UI proxy and optional training pipelines.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e .
```

For training pipelines and ML sidecars:
```bash
pip install -e ".[ml,data,train_neural]"
```

---

## 5. Infrastructure Services (Optional but Recommended)

### Neo4j (Knowledge Vault)
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=none \
  neo4j:latest
```

### Caddy (TLS Reverse Proxy)
```bash
sudo apt install -y caddy
# Copy the Caddyfile from the repo:
sudo cp oricli-backbone.service /etc/systemd/system/
sudo cp oricli-ui.service /etc/systemd/system/
sudo systemctl daemon-reload
```

---

## 6. Install systemd Services

```bash
sudo cp oricli-backbone.service /etc/systemd/system/
sudo cp oricli-ui.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable oricli-backbone oricli-ui
sudo systemctl start oricli-backbone oricli-ui
```

---

## 7. Verify

```bash
# Check services
sudo systemctl status oricli-backbone oricli-ui

# Health check (should return {"status":"ready",...})
curl http://localhost:8089/v1/health

# Get the auto-generated API key
cat /home/mike/Mavaia/.oricli/api_key
```

---

## Environment Variables

The backbone reads from `.env` in the project root. Key variables:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama inference endpoint (VPS local) |
| `OLLAMA_MODEL` | `all-minilm` | Embedding model (semantic memory, cache dedup) |
| `ORICLI_ENCRYPTION_KEY` | (auto) | Base64 AES key for LMDB encryption |
| `OricliAlpha_Key` | (auto) | Override API key (optional) |

---

## Quick Start After Install

See [`QUICKSTART.md`](QUICKSTART.md) for first API calls and client setup.  
See [`docs/API.md`](docs/API.md) for the full API reference.
