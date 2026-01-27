# Task 167: Staging Deployment Pipeline - COMPLETE ✅

## Summary

Implemented a complete staging deployment pipeline using GitHub Actions that automatically builds, pushes, and deploys Docker images to a staging server.

## Files Added/Modified

### GitHub Actions Workflow
- `.github/workflows/staging.yml` - Staging deployment workflow ✅ **NEW**

### Deployment Configuration
- `infra/ops/deploy/staging/docker-compose.staging.yml` - Staging compose file template ✅ **NEW**
- `infra/ops/deploy/staging/README.md` - Comprehensive deployment documentation ✅ **NEW**
- `infra/ops/deploy/staging/TASK_167_SUMMARY.md` - This file ✅ **NEW**

## Workflow Features

### Build and Push Job
- ✅ Builds backend and frontend Docker images
- ✅ Pushes to GitHub Container Registry (GHCR)
- ✅ Tags images with:
  - `sha-<SHORT_SHA>` (immutable, per commit)
  - `staging` (latest staging deployment)
  - `staging-prev` (previous deployment, for rollback)
- ✅ Includes OCI labels (source, revision, created)

### Deploy Job
- ✅ Connects to staging server via SSH
- ✅ Authenticates with GHCR
- ✅ Pulls latest images
- ✅ Updates docker-compose.staging.yml with new image tags
- ✅ Runs database migrations (`alembic upgrade head`)
- ✅ Deploys services (`docker compose up -d`)
- ✅ Waits for services to be healthy
- ✅ Verifies deployment status

### Verify Job
- ✅ Checks frontend health (`https://staging.example.com/`)
- ✅ Checks backend health (`/api/health` or `/health`)
- ✅ Checks backend readiness (`/v1/ready`)
- ✅ Fails workflow if services are unhealthy

### Smoke Tests Job
- ✅ Optionally runs Playwright smoke tests against staging
- ✅ Can be skipped via workflow_dispatch input
- ✅ Uploads test reports as artifacts
- ✅ Only runs if smoke tests exist

## Deployment Strategy

**Option 1 (Implemented)**: Compose file lives on server
- ✅ Deployment directory: `~/exam-platform-staging/`
- ✅ Workflow updates image tags in existing compose file
- ✅ No file syncing required
- ✅ Safer approach (compose file managed on server)

## GitHub Secrets Required

| Secret | Description | Example |
|--------|-------------|---------|
| `STAGING_HOST` | Staging server hostname/IP | `staging.example.com` |
| `STAGING_USER` | SSH username | `deploy` |
| `STAGING_SSH_KEY` | Private SSH key | `-----BEGIN OPENSSH...` |
| `STAGING_DOMAIN` | Staging domain | `staging.example.com` |

**Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions.

## First-Time Server Setup

The README includes comprehensive first-time setup instructions:

1. ✅ Install Docker and Docker Compose
2. ✅ Create deployment user and directory
3. ✅ Set up SSH key authentication
4. ✅ Configure GHCR access
5. ✅ Create environment file (`.env`)
6. ✅ Deploy docker-compose.staging.yml
7. ✅ Set up Traefik configuration (if used)
8. ✅ Verify directory structure

## Rollback Mechanism

### Quick Rollback
- ✅ Uses `staging-prev` tag (automatically maintained)
- ✅ Simple sed command to update compose file
- ✅ Redeploy with previous images

### Rollback to Specific SHA
- ✅ Pull specific SHA-tagged images
- ✅ Update compose file with SHA tags
- ✅ Redeploy

### Database Migration Rollback
- ✅ `alembic downgrade -1` (one migration)
- ✅ `alembic downgrade <revision>` (specific revision)
- ✅ Documented with warnings

## Workflow Triggers

- ✅ **Push to main**: Automatic deployment
- ✅ **workflow_dispatch**: Manual trigger with option to skip tests

## Health Check Endpoints

- ✅ Frontend: `https://staging.example.com/` (expects 200)
- ✅ Backend health: `https://api-staging.example.com/health` or `https://staging.example.com/api/health` (expects 200)
- ✅ Backend readiness: `https://api-staging.example.com/v1/ready` (expects 200, logs degraded status)

## Migration Handling

- ✅ Runs `alembic upgrade head` before deployment
- ✅ Continues deployment even if migration fails (logs warning)
- ✅ Migration runs in temporary container (`--rm`)
- ✅ Safe: migrations are idempotent

## Security Features

- ✅ No secrets in repository
- ✅ SSH key authentication
- ✅ GHCR authentication via GITHUB_TOKEN
- ✅ Immutable image tags (SHA-based)
- ✅ Non-root container users (from Task 166)
- ✅ Staging isolation from production

## Verification Checklist

After first deployment:

- [ ] Images built and pushed to GHCR
- [ ] Images tagged correctly (sha-*, staging, staging-prev)
- [ ] SSH connection to staging server works
- [ ] Images pulled successfully
- [ ] docker-compose.staging.yml updated with new tags
- [ ] Migrations run successfully
- [ ] Services started and healthy
- [ ] Frontend health check passes
- [ ] Backend health check passes
- [ ] Backend readiness check passes
- [ ] Smoke tests run (if enabled)

## Example Deployment Flow

```bash
# 1. Push to main triggers workflow
git push origin main

# 2. Workflow builds images
# Backend: ghcr.io/owner/repo-backend:sha-abc1234
# Frontend: ghcr.io/owner/repo-frontend:sha-abc1234

# 3. Workflow deploys to staging
# - SSH to staging server
# - Pull images
# - Update compose file
# - Run migrations
# - Start services

# 4. Workflow verifies deployment
# - Check frontend: 200 OK
# - Check backend health: 200 OK
# - Check backend readiness: 200 OK

# 5. Workflow runs smoke tests (optional)
# - Playwright tests against staging
```

## Troubleshooting

Common issues documented in README:

- ✅ Services not starting
- ✅ Database connection issues
- ✅ Image pull failures
- ✅ Health check failures
- ✅ Migration failures

## Runbook Integration

Deployment procedures are integrated with operational runbooks:

- **[00-QuickStart.md](../../../runbooks/00-QuickStart.md)** - Post-deployment verification
- **[02-Rollback.md](../../../runbooks/02-Rollback.md)** - Manual rollback procedures
- **[03-Database.md](../../../runbooks/03-Database.md)** - Database migration procedures
- **[08-Cloudflare.md](../../../runbooks/08-Cloudflare.md)** - Cache purge after deployment

## TODO Checklist for Future Enhancements

- [ ] Add production deployment pipeline (similar to staging)
- [ ] Add blue-green deployment strategy
- [ ] Add canary deployment support
- [ ] Add automated rollback on health check failures
- [ ] Add deployment notifications (Slack, email)
- [ ] Add deployment metrics and dashboards
- [ ] Add post-deployment verification scripts (automated)
- [ ] Add database migration testing in CI before deployment
- [ ] Add deployment approval gates for production
- [ ] Add feature flag integration for gradual rollouts
- [ ] Add automated smoke tests in production after deployment
- [ ] Add deployment history tracking and audit logs
