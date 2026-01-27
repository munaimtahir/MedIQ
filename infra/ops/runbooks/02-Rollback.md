# Rollback Runbook

**Purpose**: Safely rollback to a previous working version when a deployment causes issues.

## Prerequisites

- Access to staging server via SSH
- Docker and Docker Compose installed
- Previous image tags available in GHCR (staging-prev or sha-*)

## Rollback Procedure

### Step 1: Identify Current and Previous Versions

```bash
# SSH to staging server
ssh <STAGING_USER>@<STAGING_HOST>

# Navigate to deployment directory
cd ~/exam-platform-staging

# Check current image tags in docker-compose.staging.yml
grep "image:" docker-compose.staging.yml

# Check what images are available locally
docker images | grep -E "(backend|frontend)" | head -10

# Check what's tagged as staging-prev (if available)
docker images | grep "staging-prev"
```

### Step 2: Determine Rollback Target

**Option A: Rollback to staging-prev tag** (if available)

```bash
# staging-prev tag should point to the previous deployment
# This is automatically updated by the CI/CD pipeline
BACKEND_IMAGE="ghcr.io/<OWNER>/<REPO>-backend:staging-prev"
FRONTEND_IMAGE="ghcr.io/<OWNER>/<REPO>-frontend:staging-prev"
```

**Option B: Rollback to specific SHA tag** (if you know the working SHA)

```bash
# Use a known-good SHA from previous deployment
WORKING_SHA="abc1234"  # Replace with actual SHA
BACKEND_IMAGE="ghcr.io/<OWNER>/<REPO>-backend:sha-${WORKING_SHA}"
FRONTEND_IMAGE="ghcr.io/<OWNER>/<REPO>-frontend:sha-${WORKING_SHA}"
```

**Option C: Rollback to latest tag** (if staging-prev not available)

```bash
# Pull latest images (may not be the previous version)
docker pull ghcr.io/<OWNER>/<REPO>-backend:latest
docker pull ghcr.io/<OWNER>/<REPO>-frontend:latest
BACKEND_IMAGE="ghcr.io/<OWNER>/<REPO>-backend:latest"
FRONTEND_IMAGE="ghcr.io/<OWNER>/<REPO>-frontend:latest"
```

### Step 3: Pull Rollback Images

```bash
# Login to GHCR (if not already logged in)
echo "<GITHUB_TOKEN>" | docker login ghcr.io -u <GITHUB_ACTOR> --password-stdin

# Pull backend image
docker pull ${BACKEND_IMAGE}

# Pull frontend image
docker pull ${FRONTEND_IMAGE}

# Verify images are available
docker images | grep -E "(backend|frontend)" | grep -E "(staging-prev|sha-|latest)"
```

### Step 4: Update docker-compose.staging.yml

```bash
# Backup current compose file
cp docker-compose.staging.yml docker-compose.staging.yml.backup.$(date +%Y%m%d_%H%M%S)

# Update image tags in compose file
sed -i "s|image:.*backend.*|image: ${BACKEND_IMAGE}|g" docker-compose.staging.yml
sed -i "s|image:.*frontend.*|image: ${FRONTEND_IMAGE}|g" docker-compose.staging.yml

# Verify changes
grep "image:" docker-compose.staging.yml | grep -E "(backend|frontend)"
```

### Step 5: Stop Current Services

```bash
# Stop frontend first (to avoid serving stale data)
docker compose -f docker-compose.staging.yml stop frontend_staging

# Stop backend
docker compose -f docker-compose.staging.yml stop backend_staging

# Verify services are stopped
docker compose -f docker-compose.staging.yml ps
```

### Step 6: Start Services with Rollback Images

```bash
# Start backend first
docker compose -f docker-compose.staging.yml up -d backend_staging

# Wait for backend to be healthy (30 seconds)
sleep 30

# Verify backend is responding
curl -I https://<STAGING_DOMAIN>/api/v1/health

# Start frontend
docker compose -f docker-compose.staging.yml up -d frontend_staging

# Wait for frontend to be ready (10 seconds)
sleep 10

# Verify frontend is responding
curl -I https://<STAGING_DOMAIN>/
```

### Step 7: Verify Rollback

Run the verification checklist below.

## Database Migration Rollback

**⚠️ WARNING**: Database migrations are generally NOT reversible. Only rollback database changes if:

1. You have a backup from before the migration
2. The migration was designed to be reversible
3. You have tested the rollback in a non-production environment

### If Migration Rollback is Required

```bash
# Connect to backend container
docker compose -f docker-compose.staging.yml exec backend_staging bash

# List migration history
alembic history

# Rollback to previous migration (if reversible)
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade <revision_id>

# Exit container
exit
```

**⚠️ Always test migration rollbacks in staging first!**

## Verification Checklist

After rollback:

1. **Containers are running with correct images**:
   ```bash
   docker compose -f docker-compose.staging.yml ps
   docker compose -f docker-compose.staging.yml images | grep -E "(backend|frontend)"
   ```

2. **Backend health endpoint returns 200**:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://<STAGING_DOMAIN>/api/v1/health
   # Expected: 200
   ```

3. **Backend readiness endpoint returns 200**:
   ```bash
   curl -s https://<STAGING_DOMAIN>/api/v1/ready | jq -r '.status'
   # Expected: "ok" or "degraded" (not "down")
   ```

4. **Frontend returns 200**:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://<STAGING_DOMAIN>/
   # Expected: 200
   ```

5. **No critical errors in logs**:
   ```bash
   docker compose -f docker-compose.staging.yml logs --since=2m backend_staging | grep -iE "(error|exception|traceback)" | wc -l
   # Expected: 0 or very low
   ```

## Automated Rollback Script

For faster rollback, you can use this script:

```bash
#!/bin/bash
set -e

# Configuration
STAGING_DIR="~/exam-platform-staging"
BACKEND_IMAGE="${1:-ghcr.io/<OWNER>/<REPO>-backend:staging-prev}"
FRONTEND_IMAGE="${2:-ghcr.io/<OWNER>/<REPO>-frontend:staging-prev}"
GITHUB_TOKEN="${GITHUB_TOKEN}"
GITHUB_ACTOR="${GITHUB_ACTOR}"

cd ${STAGING_DIR}

# Login to GHCR
echo "${GITHUB_TOKEN}" | docker login ghcr.io -u "${GITHUB_ACTOR}" --password-stdin

# Pull images
docker pull ${BACKEND_IMAGE}
docker pull ${FRONTEND_IMAGE}

# Backup compose file
cp docker-compose.staging.yml docker-compose.staging.yml.backup.$(date +%Y%m%d_%H%M%S)

# Update image tags
sed -i "s|image:.*backend.*|image: ${BACKEND_IMAGE}|g" docker-compose.staging.yml
sed -i "s|image:.*frontend.*|image: ${FRONTEND_IMAGE}|g" docker-compose.staging.yml

# Stop services
docker compose -f docker-compose.staging.yml stop frontend_staging backend_staging

# Start services
docker compose -f docker-compose.staging.yml up -d backend_staging
sleep 30
docker compose -f docker-compose.staging.yml up -d frontend_staging
sleep 10

# Verify
echo "Verifying rollback..."
curl -I https://<STAGING_DOMAIN>/api/v1/health
curl -I https://<STAGING_DOMAIN>/

echo "Rollback complete. Verify services are healthy."
```

**Usage:**
```bash
# Rollback to staging-prev
./rollback.sh

# Rollback to specific SHA
./rollback.sh ghcr.io/<OWNER>/<REPO>-backend:sha-abc1234 ghcr.io/<OWNER>/<REPO>-frontend:sha-abc1234
```

## Post-Rollback Actions

1. **Document rollback**:
   - Record which version was rolled back from
   - Record which version was rolled back to
   - Record reason for rollback
   - Record time of rollback

2. **Investigate root cause**:
   - Review logs from failed deployment
   - Identify what caused the issue
   - Create ticket for fix

3. **Update team**:
   - Notify team of rollback
   - Share findings
   - Schedule post-mortem if SEV-1/SEV-2

4. **Prevent recurrence**:
   - Update CI/CD if needed
   - Add tests if issue was testable
   - Update runbooks if gaps found

## Prevention

To reduce need for rollbacks:

1. **Test in staging first**: Always deploy to staging before production
2. **Canary deployments**: Roll out to small percentage first
3. **Feature flags**: Use feature flags to disable problematic features
4. **Database migrations**: Test migrations thoroughly, use reversible migrations when possible
5. **Monitoring**: Set up alerts for error rates, latency, etc.

## Related Runbooks

- [01-Incident-Checklist.md](./01-Incident-Checklist.md) - Incident triage
- [03-Database.md](./03-Database.md) - Database migration procedures
- [00-QuickStart.md](./00-QuickStart.md) - Quick health checks
