# ORI Dev Deploy Notes

## Current state

- `https://oridev.thynaptic.com` is live and serving the built ORI Dev app.
- The live route was patched into Caddy through the local admin API.
- That means the route works now, but it is not guaranteed to survive a future Caddy restart until the same block is written into `/etc/caddy/Caddyfile`.

Saved live config snapshot:

- [.tmp_oridev_caddy_config.json](/home/mike/Mavaia/.tmp_oridev_caddy_config.json)

## Permanent Caddy block

Add this block to `/etc/caddy/Caddyfile`:

```caddy
oridev.thynaptic.com {
    tls /etc/caddy/certs/cf_origin.crt /etc/caddy/certs/cf_origin.key

    header {
        Cache-Control "no-store, no-cache, must-revalidate"
    }

    root * /home/mike/Mavaia/products/ori-dev-web/dist
    file_server
    try_files {path} /index.html
}
```

## Developer portal host

`dev.thynaptic.com` is the public developer portal for ORI integration. It should not be used as the ORI Dev product domain. A static portal block is:

```caddy
dev.thynaptic.com {
    tls /etc/caddy/certs/cf_origin.crt /etc/caddy/certs/cf_origin.key

    header {
        Cache-Control "no-store, no-cache, must-revalidate"
    }

    root * /home/mike/Mavaia/dev-portal
    file_server
    try_files {path} /index.html
}
```

## App build path

Build ORI Dev from its nested repo:

```bash
cd /home/mike/Mavaia/products/ori-dev-web
npm run build
```

This writes the deployed SPA output to:

- `products/ori-dev-web/dist/`

## Optional local service path

If you want ORI Dev served by a local process instead of direct file serving in Caddy:

- startup script: [scripts/start_ori_dev.sh](/home/mike/Mavaia/scripts/start_ori_dev.sh)
- unit file: [ori-dev-ui.service](/home/mike/Mavaia/ori-dev-ui.service)

That path serves the built SPA on `127.0.0.1:5002`.
