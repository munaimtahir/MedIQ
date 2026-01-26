# Traefik Reverse Proxy Configuration

This directory contains the Traefik static configuration for production deployments.

## Files

- `traefik.yml` - Static configuration file loaded by Traefik at startup

## Configuration Overview

### Entrypoints
- **web** (port 80): HTTP traffic (redirects to HTTPS)
- **websecure** (port 443): HTTPS traffic with TLS termination

### Providers
- **Docker**: Auto-discovers services with `traefik.enable=true` label
- **Network**: Uses `app` network for service discovery
- **Exposed by default**: `false` (only labeled services are exposed)

### Certificates
- **Let's Encrypt**: Automatic HTTPS certificate issuance and renewal
- **Storage**: `/letsencrypt/acme.json` (persisted in Docker volume)
- **Challenge**: HTTP-01 challenge via port 80

### Logging
- **Level**: INFO
- **Format**: JSON
- **Access Logs**: JSON format at `/var/log/traefik/access.log`

### Dashboard
- **Enabled**: Yes (localhost-only)
- **Public Access**: Disabled (security best practice)
- **Binding**: `127.0.0.1:8080` (OS-level isolation)
- **Access**: Via SSH tunnel only
  ```bash
  ssh -L 8080:127.0.0.1:8080 <user>@<server_ip>
  # Then open: http://localhost:8080/dashboard/
  ```

## Environment Variables

Required environment variable:
- `TRAEFIK_ACME_EMAIL`: Email address for Let's Encrypt certificate notifications

## Usage

This configuration is used by `docker-compose.prod.yml`:

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml up -d
```

The configuration file is mounted as a read-only volume:
```yaml
volumes:
  - ../../traefik/traefik.yml:/etc/traefik/traefik.yml:ro
```

## Middlewares

Reusable middlewares are defined via Docker labels on the Traefik service:
- `redirect-to-https@docker`: Redirects HTTP to HTTPS
- `sec-headers@docker`: Applies security headers (HSTS, X-Frame-Options, etc.)
- `compress@docker`: Enables response compression

These middlewares are referenced by frontend and backend services.

## Troubleshooting

### View Configuration
```bash
docker exec exam_platform_traefik cat /etc/traefik/traefik.yml
```

### Check Logs
```bash
docker logs exam_platform_traefik -f
```

### Verify Routers
```bash
docker logs exam_platform_traefik | grep -i router
```

### Test Configuration
```bash
docker exec exam_platform_traefik traefik version
```

## Security Notes

- Docker socket mounted read-only (`:ro`)
- Dashboard not exposed publicly
- Forwarded headers validation enabled
- Only services with explicit labels are exposed
