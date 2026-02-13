# Major Directories and Modules

## Top-level directories

- `backend/`
- `frontend/`
- `infra/`
- `docs/`
- `mobile/`
- `services/`
- `scripts/`

## Directory role map

| Path | Role | Current scale signal |
|---|---|---|
| `backend/app` | Core backend business and API logic | ~352 files |
| `backend/tests` | Backend validation suite | 100+ files |
| `backend/alembic/versions` | DB evolution history | 57 migrations |
| `frontend/app` | Next.js pages + API route handlers | ~225 files |
| `frontend/components` | Admin/student/auth/UI component library | ~190 files |
| `infra` | Docker/K8s/ops/observability/snowflake | ~128 files |
| `docs` | Product/ops/security/task/verification docs | 82 files |
| `services/ranking-go` | Ranking microservice support | Go service + tests |
| `mobile` | Mobile app shell and assets | React Native-style package |

## Major backend module clusters

- `app/api/v1/endpoints/*`
  - health, auth, onboarding, syllabus, sessions, analytics, notifications
  - large admin surface: questions, imports, runtime, security, audit, users, queues, settings
  - advanced subsystems: warehouse, graph, rank/ranking, mocks, IRT, search

- `app/learning_engine/*`
  - mastery, revision, adaptive, difficulty, mistakes, BKT, IRT, graph revision, ranking bridges

- `app/search/*`, `app/graph/*`, `app/warehouse/*`, `app/cohorts/*`
  - optional and staged advanced capabilities with dedicated services

## Major frontend module clusters

- `frontend/app/admin/*`: broad admin pages (algorithms, search, ranking, users, warehouse, etc.)
- `frontend/app/student/*`: learning experience pages (dashboard, blocks, revision, analytics, concepts)
- `frontend/app/api/*`: server route handlers bridging to backend APIs
- `frontend/components/admin/*`, `frontend/components/student/*`, `frontend/components/ui/*`

## Module breadth interpretation

The directory and module structure indicates a platform with deep operational and algorithmic scope, not a narrow MVP implementation.
