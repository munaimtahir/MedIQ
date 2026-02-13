# Deployment Profiles

## Default Profile (Official)

Services:
- `backend`
- `frontend`
- `postgres`
- `redis`

Command:

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml up -d --build
```

Required flags/env:
- `ENV=prod`
- `DATABASE_URL` (pointing to `postgres` service)
- `REDIS_URL` (pointing to `redis` service)
- JWT signing + pepper vars

Expected behavior:
- Full app works with Postgres-backed data.
- Cache/rate-limit/session protections use Redis.

Failure modes:
- Postgres down: backend unhealthy, API requests fail.
- Redis down with `REDIS_REQUIRED=true`: backend readiness fails/degraded or startup may fail in strict configs.

## Optional Profile: Elasticsearch

Enable service:

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml --profile elastic up -d
```

Enable app usage:
- `ELASTICSEARCH_ENABLED=true`
- `ELASTICSEARCH_URL=http://elasticsearch:9200`

Expected behavior:
- Search paths can use ES-backed features.

Failure modes:
- If ES unavailable and `ELASTICSEARCH_ENABLED=true`, ES-specific operations degrade/fail depending on endpoint logic.
- Keep `ELASTICSEARCH_ENABLED=false` to run fallback/non-ES behavior.

## Optional Profile: Neo4j (Off by Default)

Enable service:

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml --profile neo4j up -d
```

Enable app usage:
- `NEO4J_ENABLED=true`
- `NEO4J_URI=bolt://neo4j:7687`
- `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`

Expected behavior:
- Graph/revision/graph-readiness features can use Neo4j.

Failure modes:
- If `NEO4J_ENABLED=true` without healthy Neo4j, graph endpoints degrade/fail.
- If `NEO4J_ENABLED=false`, graph paths remain feature-flagged off/degraded by design.

## Optional Profile: Ranking Go

Enable service:

```bash
docker compose -f infra/docker/compose/docker-compose.prod.yml --profile ranking-go up -d
```

Enable app usage:
- `GO_RANKING_ENABLED=true`
- `RANKING_GO_URL=http://ranking-go:8080`

Expected behavior:
- Ranking runtime can call Go implementation.

Failure modes:
- If enabled but service unavailable, ranking calls fail and runtime should remain in safe mode.
