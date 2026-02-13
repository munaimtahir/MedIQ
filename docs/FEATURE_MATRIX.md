# Feature Matrix

| Feature Area | Documented (Y/N) | Implemented (Y/N) | Tested (Y/N) | Evidence Links | Notes |
|---|---|---|---|---|---|
| Auth (JWT + refresh + session revoke) | Y | Y | Y | `docs/AUTH_JWT.md`, `backend/app/api/v1/endpoints/auth.py`, `backend/app/core/dependencies.py`, `backend/tests/auth/test_login.py`, `backend/tests/auth/test_refresh_token.py`, `backend/tests/auth/test_token_revocation.py` | JWT bearer for API, opaque refresh tokens, per-session revoke flows. |
| MFA (TOTP + backup codes) | Y | Y | Y | `backend/app/api/v1/endpoints/mfa.py`, `backend/tests/auth/test_mfa.py` | MFA endpoints exist and are guarded by auth context. |
| OAuth (Google/Microsoft start/callback/exchange/link) | Y | Y | Y | `backend/app/api/v1/endpoints/oauth.py`, `backend/tests/auth/test_oauth.py` | Provider credentials remain env-dependent for real integration. |
| Student: revision | Y | Y | Y | `backend/app/api/v1/endpoints/revision.py`, `backend/app/api/v1/endpoints/revision_today.py`, `frontend/app/student/revision/page.tsx`, `backend/tests/test_revision_v0.py` | Includes queue + today endpoints. |
| Student: mistakes | Y | Y | Y | `backend/app/api/v1/endpoints/mistakes.py`, `backend/app/api/v1/endpoints/mistakes_v1.py`, `frontend/app/student/mistakes/page.tsx`, `backend/tests/test_mistakes_v1.py` | Legacy + v1 tracks are both present. |
| Student: analytics | Y | Y | Y | `backend/app/api/v1/endpoints/analytics.py`, `frontend/app/student/analytics/page.tsx`, `backend/tests/analytics/test_analytics_endpoints.py` | Block/theme/recent analytics APIs implemented. |
| Admin: question lifecycle (draft->review->approve->publish) | Y | Y | Y | `backend/app/api/v1/endpoints/admin_questions_cms.py`, `frontend/app/admin/questions/page.tsx`, `backend/tests/cms/test_question_workflow.py` | Includes version history and status transitions. |
| Admin: syllabus manager | Y | Y | Y | `backend/app/api/v1/endpoints/admin_syllabus.py`, `frontend/app/admin/syllabus/page.tsx`, `backend/tests/test_question_cms.py` | CRUD + enable/disable + reorder endpoints. |
| Admin: import jobs/schemas | Y | Y | Y | `backend/app/api/v1/endpoints/admin_import.py`, `frontend/app/admin/import/questions/page.tsx`, `backend/tests/test_api_endpoints.py` | CSV import pipeline with job tracking is present. |
| Search (Elastic + fallback posture) | Y | Y | Y | `backend/app/core/config.py`, `backend/app/api/v1/endpoints/admin_search.py`, `backend/tests/test_search_health.py`, `backend/tests/test_search_readiness.py` | ES toggle is implemented; fallback behavior is feature/runtime dependent. |
| Observability (OTel + metrics endpoints) | Y | Y | Y | `backend/app/observability/otel.py`, `backend/app/main.py`, `backend/tests/test_telemetry.py` | `/metrics` endpoint + OTel instrumentation hooks present. |
| Warehouse export | Y | Y | Y | `backend/app/api/v1/endpoints/admin_warehouse.py`, `backend/app/warehouse/exporter.py`, `backend/tests/test_warehouse_export.py` | Feature-gated readiness + export pipeline exists. |
| Mobile offline shell | Y | Y | N | `mobile/`, `backend/app/api/v1/endpoints/sync.py` | Mobile module and sync APIs exist; dedicated automated mobile E2E evidence not found. |
