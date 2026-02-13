# Major Expected Functions

## Student functions

- Account lifecycle: signup/login/logout/refresh/reset/verify flows
- Onboarding and profile/preferences management
- Practice session creation, answering, submission, and review
- Adaptive/revision assistance and mistake-oriented learning
- Progress analytics by block/theme and session history
- Bookmarks and notifications workflows

## Admin functions

- Question CMS lifecycle (draft/in-review/approved/published controls)
- Bulk import schemas/jobs and review of rejected imports
- Syllabus hierarchy management (years/blocks/themes and ordering)
- User administration (enable/disable/password reset)
- Audit, performance, and runtime status monitoring
- System safety controls (exam mode, freeze updates, readiness checks)

## Learning intelligence and runtime functions

- Runtime profile switching and per-module overrides
- Algorithm module operations: mastery, revision, adaptive, difficulty, mistakes, BKT
- Shadow/activation pathways for IRT, graph revision, and ranking subsystems
- Approval-gated changes and operational guardrails

## Data/search/graph/warehouse functions

- Postgres baseline search with optional Elasticsearch runtime
- Graph capabilities (neighbors/prerequisites/suggestions/path + sync controls)
- Warehouse exports (incremental/backfill) and run history
- Snowflake readiness gating before activation
- Cohort analytics APIs gated by warehouse/runtime state

## Security and operability functions

- Security headers and abuse/rate-limit middleware
- MFA and OAuth-related auth paths
- Structured logging, request timing, Prometheus metrics endpoint
- CI + staging deployment workflows
