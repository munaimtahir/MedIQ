# Onboarding in 15 Minutes

## 1) Start the stack

```bash
cp .env.example .env
```

Set in `.env`:

```bash
ENV=dev
API_PREFIX=/v1
API_V1_STR=/v1
SEED_DEMO_ACCOUNTS=true
```

Run:

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml up -d --build
```

## 2) Verify services

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/v1/health
curl -fsS http://localhost:3000
```

## 3) Login with demo JWT users

- Admin: `admin@example.com` / `Admin123!`
- Student: `student@example.com` / `Student123!`

Open `http://localhost:3000/login` and sign in.

## 4) Run backend tests

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m pytest tests -v
```

## 5) Run frontend smoke

```bash
cd frontend
pnpm install
pnpm test:e2e
```

## 6) Optional profiles

- Elastic:

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml --profile elastic up -d
```

- Neo4j:

```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml --profile neo4j up -d
```
