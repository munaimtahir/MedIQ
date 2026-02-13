# Evidence and Method

## Evidence used

- Repo status and recency:
  - `git log -1`
  - `git status --short`
  - `.github/workflows/*`

- Core docs reviewed:
  - `README.md`
  - `SETUP.md`
  - `TEST_COVERAGE_SUMMARY.md`
  - `docs/architecture.md`
  - `docs/api-contracts.md`
  - `docs/data-model.md`
  - `docs/runbook.md`
  - `docs/algorithms.md`
  - `docs/security.md`
  - `docs/runtime-control.md`
  - `docs/observability.md`

- Implementation signals reviewed:
  - `backend/requirements.txt`
  - `frontend/package.json`
  - `backend/app/main.py`
  - `backend/app/api/v1/router.py`
  - `backend/app/api/v1/endpoints/*`
  - `frontend/app/api/**/route.ts`
  - `infra/docker/compose/*.yml`
  - `infra/k8s/**/*`
  - `services/ranking-go/*`

## Method

- Prioritized code/manifests over narrative claims.
- Counted module/test/migration surfaces to estimate maturity.
- Identified documentation drift where explicit claims conflict with current manifests or route/module breadth.

## Limits

- No runtime execution, integration test run, or deployment verification was performed in this documentation pass.
- Stage/maturity labels are evidence-based heuristics, not certification.
