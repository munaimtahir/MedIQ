# Task 166: Production Docker Images - COMPLETE ✅

## Summary

Created production-ready multi-stage Dockerfiles for both backend and frontend services with security best practices, health checks, and OCI labels.

## Files Added/Modified

### Backend
- `backend/Dockerfile` - Production multi-stage Dockerfile ✅ **UPDATED**
- `backend/.dockerignore` - Build context exclusions ✅ **NEW**

### Frontend
- `frontend/Dockerfile` - Production multi-stage Dockerfile ✅ **UPDATED**
- `frontend/.dockerignore` - Build context exclusions ✅ **NEW**
- `frontend/next.config.js` - Added `output: 'standalone'` for optimized Docker builds ✅ **UPDATED**

### Documentation
- `infra/ops/images/README.md` - Comprehensive build/run documentation ✅ **NEW**

## Backend Dockerfile Features

### Multi-Stage Build
- **Builder stage**: Installs dependencies (gcc, g++ for compiled packages)
- **Runtime stage**: Minimal image with only runtime dependencies

### Security
- ✅ Non-root user (`appuser`)
- ✅ Minimal base image (`python:3.11-slim`)
- ✅ No secrets in image (all via environment variables)
- ✅ Health check included

### Optimization
- ✅ Layer caching: `requirements.txt` copied first
- ✅ User-local pip install (avoids system-wide install)
- ✅ Production environment variables set

### OCI Labels
- `org.opencontainers.image.source`
- `org.opencontainers.image.revision` (from GITHUB_SHA)
- `org.opencontainers.image.created` (from BUILD_DATE)
- `org.opencontainers.image.title`
- `org.opencontainers.image.description`

### Health Check
- Endpoint: `http://localhost:8000/health`
- Interval: 30s
- Timeout: 10s
- Start period: 40s (allows app startup)
- Retries: 3

## Frontend Dockerfile Features

### Multi-Stage Build
- **Builder stage**: Installs dependencies and builds Next.js app
- **Runtime stage**: Minimal Node.js Alpine image with standalone output

### Next.js Standalone Mode
- ✅ Enabled `output: 'standalone'` in `next.config.js`
- ✅ Minimal runtime dependencies (only required Node modules)
- ✅ Significantly reduced image size (~150-200MB vs ~500MB+)

### Security
- ✅ Non-root user (`nextjs`, UID 1001)
- ✅ Minimal base image (`node:20-alpine`)
- ✅ No secrets in image

### Optimization
- ✅ Layer caching: `package.json` and `pnpm-lock.yaml` copied first
- ✅ Frozen lockfile for deterministic builds
- ✅ Standalone output (minimal dependencies)

### OCI Labels
- Same labels as backend for consistency

### Health Check
- Endpoint: `http://localhost:3000/`
- Interval: 30s
- Timeout: 10s
- Start period: 40s
- Retries: 3

## Build Commands

### Build Backend

```bash
cd backend
docker build \
  --build-arg GITHUB_SHA=$(git rev-parse HEAD) \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  -t exam-platform-backend:sha-$(git rev-parse --short HEAD) \
  -f Dockerfile \
  .
```

### Build Frontend

```bash
cd frontend
docker build \
  --build-arg GITHUB_SHA=$(git rev-parse HEAD) \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  -t exam-platform-frontend:sha-$(git rev-parse --short HEAD) \
  -f Dockerfile \
  .
```

### Build Both (Docker Compose)

```bash
cd infra/docker/compose
docker compose -f docker-compose.prod.yml build
```

## Run Commands

### Using Docker Compose

```bash
cd infra/docker/compose

# Start all services
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# Stop services
docker compose -f docker-compose.prod.yml down
```

### Verify Health

```bash
# Backend health (via Traefik or direct)
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Frontend (via Traefik or direct)
curl http://localhost:3000/
# Expected: HTML response (200 OK)

# Check container health status
docker ps
# Look for "healthy" in STATUS column
```

## Image Sizes

Expected sizes (approximate):
- **Backend**: ~200-300MB (depends on dependencies)
- **Frontend**: ~150-200MB (standalone mode significantly reduces size)

## Tagging Strategy

### SHA-based Tags (Recommended)
```bash
docker tag exam-platform-backend:sha-abc1234 exam-platform-backend:sha-abc1234
```

### Staging Tags
```bash
docker tag exam-platform-backend:sha-abc1234 exam-platform-backend:staging
```

### Latest Tags (Use with Caution)
```bash
docker tag exam-platform-backend:sha-abc1234 exam-platform-backend:latest
```

**Best Practice**: Always use SHA-based tags for production. Use `latest` only when explicitly needed.

## Verification Checklist

After building and starting:

- [ ] Backend container is running
- [ ] Frontend container is running
- [ ] Backend health check passes: `curl http://localhost:8000/health`
- [ ] Frontend health check passes: `curl http://localhost:3000/`
- [ ] Containers show "healthy" status: `docker ps`
- [ ] Images have OCI labels: `docker inspect <image> | jq '.[0].Config.Labels'`
- [ ] Containers run as non-root: `docker exec <container> id`
- [ ] Traefik routing works (if configured)

## Integration with docker-compose.prod.yml

The production compose file (`infra/docker/compose/docker-compose.prod.yml`) already references the Dockerfiles:

```yaml
backend:
  build:
    context: ../../../backend
    dockerfile: Dockerfile

frontend:
  build:
    context: ../../../frontend
    dockerfile: Dockerfile
```

No changes needed to compose file - it automatically uses the new Dockerfiles.

## Runbook Integration

Image deployment procedures are documented in:

- **[02-Rollback.md](../../runbooks/02-Rollback.md)** - Rollback procedures for image deployments ✅

## TODO Checklist for Task 167

- [ ] Add image scanning (Trivy, Snyk) to CI/CD pipeline
- [ ] Add image signing (cosign, Notary) for supply chain security
- [ ] Add automated image builds on git push/tag
- [ ] Add image registry integration (Docker Hub, ECR, GCR)
- [ ] Add image versioning strategy documentation
- [ ] Add image size monitoring and alerts
- [ ] Add vulnerability scanning in CI/CD
- [ ] Add image build caching optimization (BuildKit cache mounts)
- [ ] Add multi-architecture builds (amd64, arm64)
