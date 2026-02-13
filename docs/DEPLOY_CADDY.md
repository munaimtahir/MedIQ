# Caddy Deployment Integration

## Source of Truth

- Primary Caddyfile (edit this file):
  - `/home/munaim/srv/proxy/caddy/Caddyfile`
- Runtime copy used by service manager:
  - `/etc/caddy/Caddyfile`

Use `infra/caddy/Caddyfile.snippet` as the application site-block template.

## Steps

1. Edit source-of-truth file:

```bash
nano /home/munaim/srv/proxy/caddy/Caddyfile
```

2. Sync source -> runtime copy:

```bash
sudo cp /home/munaim/srv/proxy/caddy/Caddyfile /etc/caddy/Caddyfile
```

3. Validate config:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
```

4. Reload Caddy:

```bash
sudo systemctl reload caddy
```

## Verify Routing

Replace `<domain>` with your real host:

```bash
curl -I https://<domain>/
curl -I https://<domain>/api/health
curl -I https://<domain>/api/v1/health
curl -I https://<domain>/admin
```

Expected:
- `/` returns frontend response.
- `/api/health` or `/api/v1/health` returns backend health response.
- `/admin` routes to frontend admin app.
