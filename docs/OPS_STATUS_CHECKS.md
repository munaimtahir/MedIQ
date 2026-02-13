# Ops Status Checks

## Container Health

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

docker inspect --format='{{.Name}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
  exam_platform_backend exam_platform_frontend exam_platform_postgres exam_platform_redis
```

## Resource Stats

```bash
docker stats --no-stream

df -h
free -h
```

Interpretation:
- Sustained high CPU on backend/frontend: check request spikes and slow endpoints.
- Memory near limits: tune container limits or reduce worker counts.
- Disk pressure: rotate logs and prune old images/volumes carefully.

## Postgres Stats

Connection test:

```bash
docker exec -it exam_platform_postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'SELECT 1;'
```

Database size:

```bash
docker exec -it exam_platform_postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;"
```

## Redis Stats

```bash
docker exec -it exam_platform_redis redis-cli INFO memory
```

## App Stats

Backend health example:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/v1/health
```

Latency locations:
- Backend logs: `docker logs exam_platform_backend`
- If OTel configured: traces in your collector/backend

## Caddy Stats

```bash
sudo journalctl -u caddy --since "10 min ago" --no-pager
```

## Smoke Script (Frontend + API)

```bash
FRONTEND_URL="https://<domain>/" \
BACKEND_DOMAIN_HEALTH_URL="https://<domain>/api/health" \
BACKEND_LOCAL_HEALTH_URL="http://127.0.0.1:8000/health" \
sh infra/ops/smoke_server.sh
```
