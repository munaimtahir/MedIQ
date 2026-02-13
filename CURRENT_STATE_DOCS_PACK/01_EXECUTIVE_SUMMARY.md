# Executive Summary

## What mediQ is now

`mediQ` is an actively developed, multi-surface medical exam preparation platform with:

- Student learning experience (practice, analytics, revision, bookmarks, mistakes)
- Admin control plane (content, runtime controls, algorithms, imports, security, warehouse, cohort analytics)
- FastAPI backend with broad v1 API surface
- Next.js frontend with extensive app-router pages and API proxy routes
- Supporting infra for Docker, Kubernetes, observability, and cloud deployment patterns

## Current maturity

- **Stage**: Late-stage platform build / pre-production to production-hardening (module dependent)
- **Confidence**: High
- **Why**: clean repo state, strong CI presence, deep API surface, 100+ backend tests, rich ops/security/runtime-control documentation, and substantial migration history.

## Strategic role

The system is no longer only a “skeleton.” It acts as a **learning operations platform** where educational logic and production controls coexist:

- Learning engine algorithms (BKT/SRS/difficulty/adaptive/mistakes)
- Runtime governance (profiles, overrides, freeze/exam modes, approvals)
- Search/graph/ranking/warehouse systems with safety gates and shadow/active modes

## Key delivery signal snapshot

- Branch: `main`
- Last commit: `2026-01-28` (`b8a7b6f`)
- Working tree: clean (`git status` = 0 changes)
- CI workflows: `.github/workflows/ci.yml`, `.github/workflows/staging.yml`

## Main risk theme

Documentation is extensive but not fully synchronized with implementation depth. Some top-level docs still frame the system as early-phase while the codebase indicates advanced platform capabilities.
