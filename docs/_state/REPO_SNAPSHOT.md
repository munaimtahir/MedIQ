# Repository Snapshot (Ground Truth)

Date: 2026-02-13

## Stack Versions

- Frontend framework: Next.js `^16.1.4` (`frontend/package.json`)
- Frontend runtime libs: React `^19.2.3`, React DOM `^19.2.3` (`frontend/package.json`)
- Backend framework: FastAPI `0.128.0` (`backend/requirements.txt`)
- Python runtime: `python:3.11-slim` (`backend/Dockerfile`)
- Node runtime: `node:20-alpine` (`frontend/Dockerfile`)

## Official Default Profile (Dev/DE)

- Core dependencies for app runtime: Postgres + Redis.
- App services: `backend`, `frontend`, `postgres`, `redis`.
- Source evidence:
  - `infra/docker/compose/docker-compose.dev.yml`
  - `backend/app/core/config.py` (defaults: `NEO4J_ENABLED=false`, `ELASTICSEARCH_ENABLED=false`)

## Optional Services and Enablement

- Elasticsearch (optional)
  - Service present in compose: `elasticsearch`
  - Runtime flag: `ELASTICSEARCH_ENABLED=true`
  - Dev compose profile: `--profile elastic`
  - Files: `infra/docker/compose/docker-compose.dev.yml`, `backend/app/core/config.py`

- Neo4j (optional, off by default)
  - Service present in compose: `neo4j`
  - Runtime flag: `NEO4J_ENABLED=true`
  - Dev compose profile: `--profile neo4j`
  - Files: `infra/docker/compose/docker-compose.dev.yml`, `backend/app/core/config.py`

- Ranking Go (optional)
  - Service present in compose: `ranking-go`
  - Runtime flag: `GO_RANKING_ENABLED=true`
  - Dev compose profile: `--profile ranking-go`
  - Files: `infra/docker/compose/docker-compose.dev.yml`, `backend/app/core/config.py`

- Warehouse/Snowflake (feature-gated, off)
  - Runtime flags default false (`SNOWFLAKE_ENABLED`, `FEATURE_ALLOW_SNOWFLAKE_CONNECT`)
  - File: `backend/app/core/config.py`

## Primary Commands (Run / Seed / Test)

### Run (Dev)

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml up -d --build
```

### Seed Demo Users (JWT login path)

- Enable demo seed in env: `SEED_DEMO_ACCOUNTS=true` and `ENV=dev`
- Restart backend (or full stack).
- Seeded users (if missing):
  - `admin@example.com` / `Admin123!`
  - `student@example.com` / `Student123!`
  - `reviewer@example.com` / `Reviewer123!`
- Files:
  - `backend/app/main.py`
  - `backend/app/core/seed_auth.py`

### Tests

- Backend unit/integration:

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m pytest tests -v
```

- Frontend Playwright smoke:

```bash
cd frontend
pnpm test:e2e
```

## Environment Variables Overview (No Secrets)

- Runtime mode and routing
  - `ENV`: runtime env (`dev|staging|prod|test`)
  - `API_PREFIX`: backend API prefix
  - `API_V1_STR`: alias prefix used by backend settings

- Database/cache
  - `DATABASE_URL`: SQLAlchemy database DSN
  - `REDIS_URL`: Redis connection URL
  - `REDIS_ENABLED`, `REDIS_REQUIRED`: Redis behavior

- Auth/JWT
  - `JWT_SIGNING_KEY_CURRENT`, `JWT_SIGNING_KEY_PREVIOUS`, `JWT_SECRET` (legacy fallback)
  - `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
  - `AUTH_TOKEN_PEPPER_CURRENT`, `AUTH_TOKEN_PEPPER_PREVIOUS`, `AUTH_TOKEN_PEPPER`, `TOKEN_PEPPER`

- Frontend/BFF/cookies
  - `BACKEND_URL`: Next server-side BFF target
  - `NEXT_PUBLIC_API_BASE_URL`: browser API base path
  - `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN`
  - `ACCESS_COOKIE_MAXAGE_SECONDS`, `REFRESH_COOKIE_MAXAGE_SECONDS`

- Optional service flags
  - `ELASTICSEARCH_ENABLED`, `ELASTICSEARCH_URL`, `ELASTICSEARCH_INDEX_PREFIX`
  - `NEO4J_ENABLED`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
  - `GO_RANKING_ENABLED`, `RANKING_GO_URL`

- CORS and frontend URLs
  - `CORS_ALLOW_ORIGINS_PUBLIC`, `CORS_ALLOW_ORIGINS_APP`
  - `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`, `CORS_EXPOSE_HEADERS`, `CORS_ALLOW_CREDENTIALS`
  - `FRONTEND_URL`, `FRONTEND_BASE_URL`
