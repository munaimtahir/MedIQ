# Documentation Drift Report

Date: 2026-02-13

## README.md


- Reality in code:
  - JWT auth dependency requires `Authorization: Bearer <access_token>`: `backend/app/core/dependencies.py`
  - Login endpoint issues tokens: `backend/app/api/v1/endpoints/auth.py`
  - Demo users are email/password seeded: `backend/app/core/seed_auth.py`
- Action: Rewrite README auth section to JWT login flow only; remove legacy header-auth references.

- Claim: "database seeded via `POST /seed`"
- Reality in code:
  - Canonical backend app has no `/seed` endpoint in `backend/app/main.py`
  - Demo seeding is startup-driven and env-gated (`SEED_DEMO_ACCOUNTS`): `backend/app/main.py`, `backend/app/core/seed_auth.py`
- Action: Replace with startup seed guidance and explicit env flags.

## docs/architecture.md

- Claim: Backend structure is `backend/main.py`, `database.py`, `models.py`, `seed.py` and legacy temporary auth assumptions.
- Reality in code:
  - Canonical backend is modular under `backend/app/**` with app factory in `backend/app/main.py`
  - API router aggregation in `backend/app/api/v1/router.py`
  - JWT auth implemented in `backend/app/core/dependencies.py`, `backend/app/core/security.py`
- Action: Rewrite architecture doc around actual module structure and JWT-based auth.

- Claim: Next.js version is 14.
- Reality in code:
  - `frontend/package.json` uses Next.js `^16.1.4` and React `^19.2.3`.
- Action: Update version statements.



## Ops Docs (`docs/runbook.md`, `infra/docker/README.md`)

- Claim: Production path assumes Traefik and legacy paths/commands.
- Reality in code/target ops:
  - Target deployment uses external Caddy at `/home/munaim/srv/proxy/caddy/Caddyfile` (server convention provided by user).
  - Existing `infra/docker/compose/docker-compose.prod.yml` has now been aligned for Caddy-first (no Traefik service).
- Action: Add Caddy-specific deployment runbook and retire Traefik-first instructions from primary docs.

- Claim: Docker docs mix legacy/local assumptions and services not required for baseline deploy.
- Reality in code:
  - Baseline deploy profile now centers on `backend + frontend + postgres + redis` with optional `elastic`/`neo4j` profiles.
- Action: add explicit profile documentation and production env template references.

## Precision Notes (Investigate)

- API prefix consistency still needs explicit env pinning by environment (`/v1` vs `/api/v1` defaults):
  - Default in settings: `backend/app/core/config.py`
  - Frontend BFF assumptions: `frontend/lib/server/backendClient.ts`
- Action: enforce prefix via deployment env (`API_PREFIX=/v1`, `API_V1_STR=/v1`) and document this explicitly.
