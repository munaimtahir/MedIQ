# Deploy to Existing Ubuntu 24.04 Server

Target layout:
- App repo: `/home/munaim/srv/apps/<app>/`
- Proxy repo: `/home/munaim/srv/proxy/`
- Caddy source-of-truth: `/home/munaim/srv/proxy/caddy/Caddyfile`
- Runtime copy: `/etc/caddy/Caddyfile`

Example app path used below: `/home/munaim/srv/apps/mediq/`

## 1) Prerequisite Checks

```bash
docker --version
docker compose version
sudo systemctl status caddy --no-pager
```

## 2) Repo Placement

```bash
mkdir -p /home/munaim/srv/apps
cd /home/munaim/srv/apps
# Clone/pull repo so code is in:
# /home/munaim/srv/apps/mediq
```

## 3) Create `.env.production`

```bash
cd /home/munaim/srv/apps/mediq
cp infra/env/.env.production.example infra/docker/compose/.env.production
```

Edit values:

```bash
nano infra/docker/compose/.env.production
```

Also create optional shared env file used by compose:

```bash
: > infra/docker/compose/.env
```

## 4) Bring Up Stack

```bash
cd /home/munaim/srv/apps/mediq
docker compose -f infra/docker/compose/docker-compose.prod.yml up -d --build
```

Optional profiles:

```bash
# Elasticsearch
docker compose -f infra/docker/compose/docker-compose.prod.yml --profile elastic up -d

# Neo4j
docker compose -f infra/docker/compose/docker-compose.prod.yml --profile neo4j up -d
```

## 5) Migrations + Seed

Run migrations:

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml exec backend alembic upgrade head
```

Seed demo accounts (only if explicitly needed and allowed):

```bash
# set SEED_DEMO_ACCOUNTS=true in infra/docker/compose/.env.production, then restart backend
# default should remain false in production
```

If demo seed is disabled (recommended), create admin manually:

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml exec backend python scripts/create_admin.py --email admin@example.com --password 'ChangeThisNow123!'
```

## 6) Verify Containers and Local Health

```bash
docker ps

docker logs exam_platform_backend --tail 100
docker logs exam_platform_frontend --tail 100

curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/v1/health
curl -fsS http://127.0.0.1:3000/
```

## 7) Caddy Steps

1. Add site block (from `infra/caddy/Caddyfile.snippet`) into:

```bash
nano /home/munaim/srv/proxy/caddy/Caddyfile
```

2. Sync to runtime path:

```bash
sudo cp /home/munaim/srv/proxy/caddy/Caddyfile /etc/caddy/Caddyfile
```

3. Validate + reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## 8) External Verification

```bash
curl -I https://<domain>/
curl -I https://<domain>/api/health
curl -I https://<domain>/api/v1/health
```

## 9) Rollback Procedure

1. Stop app containers (keep volumes):

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml down
```

2. Revert Caddyfile changes in source-of-truth file:

```bash
nano /home/munaim/srv/proxy/caddy/Caddyfile
```

3. Sync + reload:

```bash
sudo cp /home/munaim/srv/proxy/caddy/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## 10) Minimum Backup Set

- PostgreSQL dump from container:

```bash
docker exec -t exam_platform_postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup_$(date +%F).sql
```

- Caddyfile backup:

```bash
cp /home/munaim/srv/proxy/caddy/Caddyfile /home/munaim/srv/proxy/caddy/Caddyfile.backup.$(date +%F-%H%M%S)
```

- Production env backup:

```bash
cp infra/docker/compose/.env.production infra/docker/compose/.env.production.backup.$(date +%F-%H%M%S)
```
