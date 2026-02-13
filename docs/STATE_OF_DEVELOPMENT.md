# State of Development

## Stage Declaration: Early Beta

Justification:
- Core auth/session lifecycle is implemented with JWT + refresh + revoke flows (`backend/app/api/v1/endpoints/auth.py`).
- Major student/admin paths exist and are covered by backend tests (`backend/tests/**`) and frontend smoke tests (`frontend/tests/smoke/**`).
- Deployment path existed but had major doc/ops drift (Traefik-first docs vs current Caddy target), which is now being normalized.
- Several advanced subsystems remain feature-flagged and optional (Neo4j, Elastic, ranking-go, warehouse activation).

## Production-Ready Now

- JWT auth path (login/refresh/logout/session revoke)
- Postgres + Redis core runtime
- Core student session/revision/mistake/analytics routes
- Core admin question CMS + workflow routes
- Containerized deployment via Compose with healthchecks and restart policies

## Beta-Ready but Incomplete

- End-to-end operational runbook consistency across all existing docs
- OAuth provider setup hardening for production identity tenants
- Search rollout playbooks (Elastic enablement readiness and rollback)
- Full observability dashboard/alert policy standardization

## Experimental / Flagged Off by Default

- Neo4j graph activation (`NEO4J_ENABLED=false` default)
- Elasticsearch activation (`ELASTICSEARCH_ENABLED=false` default)
- Ranking Go runtime (`GO_RANKING_ENABLED=false` default)
- Snowflake/warehouse connect path (hard-gated and readiness-gated)

## Top 10 Gaps to Reach Production

1. Resolve API prefix consistency and enforce one canonical value across backend settings and frontend BFF env.
2. Add CI checks to fail on doc drift for auth/deploy instructions.
3. Add dedicated production smoke pipeline (domain + local loopback checks) as release gate.
4. Standardize migration + seed process for prod/staging with explicit one-command scripts.
5. Add stronger secret validation for all auth/OAuth/email env variables at startup in prod.
6. Add rate-limit/load tests tied to expected VPS sizing and concurrency budgets.
7. Add synthetic uptime checks for `/`, `/api/health`, `/api/v1/health`, and auth refresh flow.
8. Add formal backup/restore drills for Postgres and Caddy config snapshots.
9. Add role-based access regression suite for all admin endpoints in CI.
10. Add mobile/offline end-to-end automation (sync conflict, retries, offline replay).
