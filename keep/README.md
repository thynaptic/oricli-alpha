# Keep

This directory is a **git submodule** pointing at:

**https://github.com/genoventures-labs/Keep**

Working name: **Keep** (self-hosted cognition runtime).  
Extracted from the former in-tree `ori-capsule/` path.

```bash
git submodule update --init --recursive keep
cd keep && docker compose up --build
```

If the submodule is not initialized yet, clone directly:

```bash
git clone https://github.com/genoventures-labs/Keep.git keep
```
