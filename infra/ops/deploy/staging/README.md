# Staging Deployment Guide

This guide covers the staging deployment pipeline, server setup, and operational procedures.

## Overview

The staging environment is automatically deployed via GitHub Actions when code is pushed to the `main` branch. The pipeline:

1. Builds Docker images for backend and frontend
2. Pushes images to GitHub Container Registry (GHCR)
3. Deploys to staging server via SSH
4. Runs database migrations
5. Verifies deployment health
6. Optionally runs Playwright smoke tests

## GitHub Secrets Required

Configure the following secrets in your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `STAGING_HOST` | Staging server hostname or IP | `staging.example.com` or `192.0.2.1` |
| `STAGING_USER` | SSH username for staging server | `deploy` |
| `STAGING_SSH_KEY` | Private SSH key for authentication | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `STAGING_DOMAIN` | Staging domain (for health checks) | `staging.example.com` |

**Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions and has the necessary permissions for GHCR.

## First-Time Server Preparation

### Prerequisites

- Ubuntu 22.04 LTS or similar Linux distribution
- Docker and Docker Compose installed
- SSH access with sudo privileges
- Domain DNS configured (A/AAAA records pointing to server)

### Step 1: Install Docker and Docker Compose

```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (replace $USER with your username)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker compose version

# Log out and back in for group changes to take effect
```

### Step 2: Create Deployment User and Directory

```bash
# Create deployment user (if not using existing user)
sudo adduser deploy
sudo usermod -aG docker deploy

# Create deployment directory
sudo mkdir -p /home/deploy/exam-platform-staging
sudo chown deploy:deploy /home/deploy/exam-platform-staging
cd /home/deploy/exam-platform-staging
```

### Step 3: Set Up SSH Key Authentication

On your local machine, generate an SSH key pair if you don't have one:

```bash
ssh-keygen -t ed25519 -C "github-actions-staging" -f ~/.ssh/staging_deploy_key
```

Copy the **private key** (`staging_deploy_key`) to GitHub Secrets as `STAGING_SSH_KEY`.

Copy the **public key** to the staging server:

```bash
# On local machine
ssh-copy-id -i ~/.ssh/staging_deploy_key.pub deploy@staging.example.com

# Or manually on server
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PUBLIC_KEY_CONTENT" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 4: Configure GitHub Container Registry Access

The deployment user needs to be able to pull images from GHCR. The CI/CD pipeline handles authentication during deployment, but for manual operations:

```bash
# Login to GHCR (requires GitHub Personal Access Token with `read:packages` permission)
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### Step 5: Create Environment File

Create `.env` file in the deployment directory:

```bash
cd /home/deploy/exam-platform-staging
nano .env
```

Minimum required variables:

```bash
# Domain
DOMAIN=example.com

# Database
POSTGRES_DB_STAGING=exam_platform_staging
POSTGRES_USER_STAGING=exam_user_staging
POSTGRES_PASSWORD_STAGING=CHANGE_ME_STRONG_PASSWORD

# JWT Secrets
JWT_SECRET_STAGING=CHANGE_ME_STRONG_RANDOM_SECRET
AUTH_TOKEN_PEPPER_STAGING=CHANGE_ME_STRONG_RANDOM_PEPPER
MFA_ENCRYPTION_KEY_STAGING=CHANGE_ME_STRONG_RANDOM_KEY

# Traefik
TRAEFIK_ACME_EMAIL=admin@example.com
STAGING_BASIC_AUTH_USERS=admin:$apr1$... (htpasswd output)

# Optional: OAuth
OAUTH_GOOGLE_CLIENT_ID_STAGING=...
OAUTH_GOOGLE_CLIENT_SECRET_STAGING=...
OAUTH_MICROSOFT_CLIENT_ID_STAGING=...
OAUTH_MICROSOFT_CLIENT_SECRET_STAGING=...

# Optional: Email (use shadow mode for staging)
EMAIL_BACKEND_STAGING=shadow
EMAIL_FROM_STAGING=noreply-staging@example.com
```

Generate secure passwords and secrets:

```bash
# Generate random passwords
openssl rand -base64 32

# Generate htpasswd for Basic Auth
htpasswd -nb admin password | sed 's/\$/\$\$/g'
```

### Step 6: Deploy Docker Compose File

Copy the staging docker-compose file to the server:

```bash
# From your local machine (after cloning the repo)
scp infra/ops/deploy/staging/docker-compose.staging.yml deploy@staging.example.com:~/exam-platform-staging/
```

Or create it manually on the server:

```bash
cd /home/deploy/exam-platform-staging
# Copy content from infra/ops/deploy/staging/docker-compose.staging.yml
nano docker-compose.staging.yml
```

**Important**: Update the image placeholders in `docker-compose.staging.yml`:
- Replace `OWNER` with your GitHub username or organization
- Replace `REPO` with your repository name
- The CI/CD pipeline will update the SHA tags automatically

### Step 7: Set Up Traefik Configuration

If using Traefik, copy the Traefik configuration:

```bash
mkdir -p /home/deploy/exam-platform-staging/traefik
# Copy traefik.yml from your repo or create it
```

### Step 8: Verify Directory Structure

```bash
cd /home/deploy/exam-platform-staging
ls -la
# Should have:
# - docker-compose.staging.yml
# - .env
# - traefik/ (if using Traefik)
```

### Step 9: Test Manual Deployment (Optional)

Before enabling CI/CD, test a manual deployment:

```bash
cd /home/deploy/exam-platform-staging

# Pull images (replace with actual image tags)
docker pull ghcr.io/OWNER/REPO-backend:sha-abc1234
docker pull ghcr.io/OWNER/REPO-frontend:sha-abc1234

# Update docker-compose.staging.yml with image tags
# Then start services
docker compose -f docker-compose.staging.yml up -d

# Check status
docker compose -f docker-compose.staging.yml ps
docker compose -f docker-compose.staging.yml logs -f
```

## Deployment Process

### Automatic Deployment

When code is pushed to `main`:

1. **Build and Push**: Images are built and pushed to GHCR with tags:
   - `sha-<SHORT_SHA>` (immutable, for this commit)
   - `staging` (latest staging deployment)
   - `staging-prev` (previous staging deployment, for rollback)

2. **Deploy**: The pipeline:
   - Connects to staging server via SSH
   - Logs in to GHCR
   - Pulls latest images
   - Updates `docker-compose.staging.yml` with new image tags
   - Runs database migrations (`alembic upgrade head`)
   - Starts/updates services (`docker compose up -d`)

3. **Verify**: Health checks verify:
   - Frontend responds at `https://staging.example.com/`
   - Backend health at `https://api-staging.example.com/health` or `https://staging.example.com/api/health`
   - Backend readiness at `https://api-staging.example.com/v1/ready`

4. **Smoke Tests**: Optionally runs Playwright smoke tests against staging

### Manual Deployment

If needed, deploy manually:

```bash
ssh deploy@staging.example.com
cd ~/exam-platform-staging

# Pull latest images
docker pull ghcr.io/OWNER/REPO-backend:staging
docker pull ghcr.io/OWNER/REPO-frontend:staging

# Update docker-compose.staging.yml with image tags
# Then deploy
docker compose -f docker-compose.staging.yml up -d

# Run migrations
docker compose -f docker-compose.staging.yml run --rm backend_staging alembic upgrade head

# Check status
docker compose -f docker-compose.staging.yml ps
```

## Rollback Procedure

### Quick Rollback to Previous Version

The pipeline maintains a `staging-prev` tag pointing to the previous deployment:

```bash
ssh deploy@staging.example.com
cd ~/exam-platform-staging

# Pull previous images
docker pull ghcr.io/OWNER/REPO-backend:staging-prev
docker pull ghcr.io/OWNER/REPO-frontend:staging-prev

# Update docker-compose.staging.yml to use staging-prev tags
sed -i 's/:sha-[a-f0-9]*/:staging-prev/g' docker-compose.staging.yml

# Deploy previous version
docker compose -f docker-compose.staging.yml up -d

# Verify
curl https://staging.example.com/
curl https://api-staging.example.com/health
```

### Rollback to Specific SHA

If you know the SHA of a previous working deployment:

```bash
ssh deploy@staging.example.com
cd ~/exam-platform-staging

# Pull specific SHA images
SHA=abc1234
docker pull ghcr.io/OWNER/REPO-backend:sha-${SHA}
docker pull ghcr.io/OWNER/REPO-frontend:sha-${SHA}

# Update docker-compose.staging.yml
sed -i "s|image:.*backend.*|image: ghcr.io/OWNER/REPO-backend:sha-${SHA}|g" docker-compose.staging.yml
sed -i "s|image:.*frontend.*|image: ghcr.io/OWNER/REPO-frontend:sha-${SHA}|g" docker-compose.staging.yml

# Deploy
docker compose -f docker-compose.staging.yml up -d
```

### Database Migration Rollback

If a migration caused issues:

```bash
ssh deploy@staging.example.com
cd ~/exam-platform-staging

# Rollback one migration
docker compose -f docker-compose.staging.yml run --rm backend_staging alembic downgrade -1

# Or rollback to specific revision
docker compose -f docker-compose.staging.yml run --rm backend_staging alembic downgrade <revision>
```

**Warning**: Only rollback migrations if you're certain it's safe. Some migrations may not be reversible.

## Monitoring and Troubleshooting

### Check Service Status

```bash
ssh deploy@staging.example.com
cd ~/exam-platform-staging

# View running containers
docker compose -f docker-compose.staging.yml ps

# View logs
docker compose -f docker-compose.staging.yml logs -f backend_staging
docker compose -f docker-compose.staging.yml logs -f frontend_staging

# Check health
docker compose -f docker-compose.staging.yml ps | grep healthy
```

### Common Issues

#### Services Not Starting

```bash
# Check logs for errors
docker compose -f docker-compose.staging.yml logs backend_staging
docker compose -f docker-compose.staging.yml logs frontend_staging

# Check if images exist
docker images | grep ghcr.io

# Verify environment variables
docker compose -f docker-compose.staging.yml config
```

#### Database Connection Issues

```bash
# Check PostgreSQL is running
docker compose -f docker-compose.staging.yml ps postgres_staging

# Test connection
docker compose -f docker-compose.staging.yml exec backend_staging python -c "from app.db.engine import engine; engine.connect()"
```

#### Image Pull Failures

```bash
# Verify GHCR authentication
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Check image exists
docker pull ghcr.io/OWNER/REPO-backend:staging
```

#### Health Check Failures

```bash
# Test endpoints manually
curl https://staging.example.com/
curl https://api-staging.example.com/health
curl https://api-staging.example.com/v1/ready

# Check Traefik routing
docker compose -f docker-compose.staging.yml logs traefik
```

## Maintenance

### Update Environment Variables

```bash
ssh deploy@staging.example.com
cd ~/exam-platform-staging

# Edit .env file
nano .env

# Restart services to apply changes
docker compose -f docker-compose.staging.yml up -d
```

### Clean Up Old Images

```bash
# Remove unused images (keeps last 5)
docker image prune -a --filter "until=168h" --force

# Or manually remove specific images
docker rmi ghcr.io/OWNER/REPO-backend:sha-old-sha
```

### Database Backup

```bash
# Create backup
docker compose -f docker-compose.staging.yml exec postgres_staging pg_dump -U exam_user_staging exam_platform_staging > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker compose -f docker-compose.staging.yml exec -T postgres_staging psql -U exam_user_staging exam_platform_staging < backup_YYYYMMDD_HHMMSS.sql
```

## Security Considerations

1. **SSH Keys**: Store private keys securely in GitHub Secrets, never in code
2. **Environment Variables**: Keep `.env` file secure, use strong passwords
3. **Basic Auth**: Use strong passwords for staging Basic Auth
4. **Image Tags**: Use immutable SHA tags for deployments
5. **Network**: Staging should be isolated from production networks
6. **Secrets Rotation**: Rotate JWT secrets, database passwords regularly

## Files Reference

- `.github/workflows/staging.yml` - GitHub Actions workflow
- `infra/ops/deploy/staging/docker-compose.staging.yml` - Staging compose file template
- `infra/ops/deploy/staging/README.md` - This file

## Runbook Integration

For operational procedures related to deployments, see the [Runbooks](../../runbooks/) directory:

- **[00-QuickStart.md](../../runbooks/00-QuickStart.md)** - Quick status checks and restarts
- **[01-Incident-Checklist.md](../../runbooks/01-Incident-Checklist.md)** - Incident triage if deployment fails
- **[02-Rollback.md](../../runbooks/02-Rollback.md)** - Rollback procedures (manual and automated)
- **[03-Database.md](../../runbooks/03-Database.md)** - Database migration procedures
- **[06-Observability.md](../../runbooks/06-Observability.md)** - How to verify deployment using observability tools
- **[08-Cloudflare.md](../../runbooks/08-Cloudflare.md)** - Cache purge after deployment

### Post-Deployment Verification

After deployment, verify using the checklist from [00-QuickStart.md](../../runbooks/00-QuickStart.md):

1. Check containers are running: `docker compose ps`
2. Verify backend health: `curl https://<STAGING_DOMAIN>/api/v1/health`
3. Verify frontend: `curl https://<STAGING_DOMAIN>/`
4. Check logs for errors: `docker compose logs --since=5m backend_staging`
5. Purge Cloudflare cache if needed: See [08-Cloudflare.md](../../runbooks/08-Cloudflare.md)

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
