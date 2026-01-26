# Runtime Control Framework

## Overview

The Runtime Control Framework provides a **generic, reusable control plane** for:

- **Learning algorithms** (v0, v1, v2…): mastery, revision, adaptive, difficulty, mistakes
- **Infra features**: Elasticsearch, Neo4j, Snowflake exports, IRT shadow
- **Safety modes**: `EXAM_MODE`, `FREEZE_UPDATES`

## Concepts

### Flags vs profiles vs overrides

| Concept | Description | Example |
|--------|-------------|---------|
| **Flags** | Global boolean/system switches | `EXAM_MODE`, `FREEZE_UPDATES` |
| **Profiles** | Named runtime modes with default module versions | `primary` (v1), `fallback` (v0), `shadow` |
| **Overrides** | Per-module version or enable/disable | `mastery` → `v1`, `search` → `v0` |

- **Profile** sets default `module → version` for all modules.
- **Overrides** beat profile defaults for specific modules.
- **Resolver** computes effective runtime: flags + active profile + overrides.

### No mid-session changes

- At **session creation**, we snapshot: active profile, resolved modules, `exam_mode_at_start`, `freeze_updates_at_start`.
- All **session endpoints** (answer, submit, etc.) use the **snapshot**, not the live resolver.
- Changing profile or flags **does not** affect in-flight sessions.

### Cached reads and safe fallback

- Resolver and flags use **in-memory cache** (TTL 5–10s, configurable).
- **DB failure**: return last known runtime, or **conservative fallback** (profile=`fallback`, `freeze_updates=true`, infra toggles off).
- Never raise; always return a valid runtime.

## Database

- **`system_flags`**: `EXAM_MODE`, `FREEZE_UPDATES` (and future flags).
- **`runtime_profiles`**: `primary`, `fallback`, `shadow` with `config` JSONB (module defaults).
- **`module_overrides`**: per-module `version_key`, `is_enabled`.
- **`switch_audit_log`**: append-only audit for flag/profile/override changes.
- **`session_runtime_snapshot`**: per-session snapshot (profile, resolved modules, flags).

## Admin API

Base path: **`/v1/admin/runtime`**.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Current flags, profile, overrides, resolved runtime |
| POST | `/flags` | Set `EXAM_MODE` or `FREEZE_UPDATES` (police-mode) |
| POST | `/profile` | Set active profile: `primary` \| `fallback` \| `shadow` |
| POST | `/override` | Set module override (version or is_enabled) |

All mutations require **ADMIN**, **police-mode confirmation** (exact phrase + reason), and **admin freeze** check.

## Police-mode phrases

| Action | Phrase |
|--------|--------|
| Enable exam mode | `ENABLE EXAM MODE` |
| Disable exam mode | `DISABLE EXAM MODE` |
| Enable freeze updates | `ENABLE FREEZE UPDATES` |
| Disable freeze updates | `DISABLE FREEZE UPDATES` |
| Set profile primary | `SET PROFILE PRIMARY` |
| Set profile fallback | `SET PROFILE FALLBACK` |
| Set profile shadow | `SET PROFILE SHADOW` |
| Override module | `OVERRIDE MODULE <module> TO <version>` |

## Freeze updates

- When **`FREEZE_UPDATES`** is true:
  - **Decision reads** (e.g. next question, plan) are allowed.
  - **State writes** (mastery updates, queue writes, etc.) are blocked with **423 Locked** (`FREEZE_UPDATES_ACTIVE`).
- Use `require_mutations_allowed(module_key)` on mutation endpoints.

## Adding a new module or v2

1. **Module key**: Add to `ModuleKey` in `runtime_control/contracts.py` and to profile `config` defaults.
2. **Registry**: Implement your module’s v0/v1 (etc.) and call `register(module_key, version_key, impl)`.
3. **Bridge**: Implement `bridge_state(module_key, from_version, to_version, user_id)` if you need version-agnostic state migration.
4. **Audit**: Flag/profile/override changes are logged to `switch_audit_log`; no extra work.

## Operator runbook: emergency fallback

1. **Disable heavy work during exam**: Set **Exam Mode** via Admin → System (or `/v1/admin/system/exam-mode`). Blocks recompute, bulk import, etc. Session create/answer/submit keep working.
2. **Stop all learning writes**: Set **Freeze updates** via Admin → Runtime (`POST /flags`) with phrase `ENABLE FREEZE UPDATES`.
3. **Revert to v0 algorithms**: Set profile **fallback** via `POST /admin/runtime/profile` with `profile_name=fallback` and phrase `SET PROFILE FALLBACK`.
4. **Restore**: Disable exam mode, disable freeze, set profile **primary** when ready.

## Session snapshot

- Stored in **`session_runtime_snapshot`** and in **`test_sessions`** (`exam_mode_at_start`, `freeze_updates_at_start`).
- Filled once at **session creation**; never updated later.
- Answer/submit and learning logic use **snapshot** for that session, not live resolver.
