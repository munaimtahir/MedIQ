# Tech Stack and Architecture

## Stack (Current from manifests)

### Backend

- FastAPI `0.128.0`
- Uvicorn `0.40.0`
- SQLAlchemy `2.0.45`
- Alembic `1.14.0`
- Pydantic `2.12.5`
- Redis `7.1.0`
- Elasticsearch client `9.2.1` (optional path)
- Neo4j `5.28.3` (graph path)
- Prometheus client instrumentation

### Frontend

- Next.js `16.1.4` (App Router)
- React `19.2.3`
- TypeScript `5.9.3`
- Tailwind CSS `3.4.19`
- Zustand `5.0.9`
- TanStack Query `5.62.11`
- Vitest-based test setup

### Supporting services

- PostgreSQL
- Redis
- Optional Elasticsearch
- Optional Neo4j
- `services/ranking-go` microservice (shadow/off by default)

### Infrastructure

- Docker Compose (`dev`, `prod`, `test`)
- Kubernetes manifests with staging overlay
- Observability and ops assets (`infra/ops`, `infra/observability`, `infra/traefik`)
- Snowflake DDL/transforms scaffolding under controlled activation

## Architectural Model

- Monorepo with separated domains:
  - `backend/` API and learning/data services
  - `frontend/` UI and route handlers
  - `infra/` deployment and operations
  - `mobile/` mobile client foundation
  - `services/` specialized supporting service(s)

- API organization:
  - Primary versioned router at `backend/app/api/v1/router.py`
  - 50+ endpoint modules in `backend/app/api/v1/endpoints`

- Runtime control emphasis:
  - profile/override/flag model for algorithm and infra behavior
  - no mid-session behavioral drift via session runtime snapshots

## Notable architectural strengths

- Safety-oriented feature activation (shadow/readiness controls)
- Operational control-plane breadth uncommon in early-stage projects
- Strong versioning and migration discipline (`57` Alembic version files)
