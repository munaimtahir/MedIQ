# Difference from Existing Documentation

This section compares current implementation signals with prominent existing docs.

## High-level difference

Existing docs are rich but distributed across many task/status files. This pack consolidates the current state into one coherent, code-anchored baseline.

## Key drift and mismatch items

### 1) “Skeleton” framing is outdated

- Existing: `README.md` calls mediQ a “production-grade skeleton.”
- Current code reality: large API/module/test/migration surface indicates a substantially advanced platform, not just skeleton scaffolding.

### 2) Frontend version mismatch in architecture doc

- Existing: `docs/architecture.md` states Next.js 14.
- Current manifest: `frontend/package.json` uses Next.js `16.1.4`.

### 3) Security status narrative lags implementation

- Existing: `docs/security.md` describes temporary header-based auth as current state and “NOT PRODUCTION READY” (Phase 1 framing).
- Current code reality: router surface includes OAuth, MFA, token lifecycle, security/admin endpoints, and security middleware.

### 4) API docs underrepresent breadth

- Existing: `docs/api-contracts.md` emphasizes early/basic endpoint contracts.
- Current code reality: backend has 59 endpoint modules and frontend has 156 API route handlers including advanced admin/runtime/warehouse/graph/ranking workflows.

### 5) Runbook/setup command paths are partially legacy

- Existing: some docs use generic `docker-compose` root flows and older project naming patterns.
- Current reality: canonical compose path is centered under `infra/docker/compose/*` with dedicated dev/prod/test files.

### 6) Multiple completion reports create status ambiguity

- Existing: many `*_COMPLETE`, `*_SUMMARY`, `TASK_*` docs can conflict in practical interpretation.
- Current need: a single canonical “current-state” reference per release cut.

## Net-new value delivered by this pack

- One executive narrative for non-technical stakeholders.
- One technical baseline for engineers.
- One stage/maturity view for planning and prioritization.
- Explicit drift list for doc cleanup backlog.
