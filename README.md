# Medical Exam Platform

Developer + deployment/engineering guide for the current repository state.

## Happy Path (Dev)

1. Copy env file:

```bash
cp .env.example .env
```

2. Set/confirm these local values in `.env`:

```bash
ENV=dev
API_PREFIX=/v1
API_V1_STR=/v1
SEED_DEMO_ACCOUNTS=true
```

3. Start stack (default profile: app + Postgres + Redis):

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml up -d --build
```

4. Open apps:
- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`
- Backend API health: `http://localhost:8000/v1/health`

## Seed and Login (JWT path only)

Demo users are created on backend startup when `ENV=dev` and `SEED_DEMO_ACCOUNTS=true`.

- Admin: `admin@example.com` / `Admin123!`
- Student: `student@example.com` / `Student123!`
- Reviewer: `reviewer@example.com` / `Reviewer123!`

Login flow:
- Frontend posts credentials to `POST /api/auth/login` (BFF route).
- BFF calls backend `POST /v1/auth/login`.
- Access/refresh tokens are stored as `httpOnly` cookies.

## Tests

### Backend tests

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m pytest tests -v
```

### Frontend Playwright smoke

```bash
cd frontend
pnpm install
pnpm test:e2e
```

## Service Profiles

- Default: Postgres + Redis (with backend/frontend)
- Elastic optional:

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml --profile elastic up -d
```

- Neo4j optional (off by default):

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml --profile neo4j up -d
```

- Ranking Go optional:

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml --profile ranking-go up -d
```

## Key Paths

- Backend app factory: `backend/app/main.py`
- Backend router wiring: `backend/app/api/v1/router.py`
- JWT dependencies: `backend/app/core/dependencies.py`
- Frontend auth BFF: `frontend/app/api/auth/*`
- Production compose: `infra/docker/compose/docker-compose.prod.yml`
