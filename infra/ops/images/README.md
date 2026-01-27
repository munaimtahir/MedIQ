# Production Docker Images

This directory contains documentation for building and managing production Docker images for the Exam Prep Platform.

## Overview

The platform consists of two main services:
- **Backend**: FastAPI (Python 3.11) - API server
- **Frontend**: Next.js (Node.js 20) - Web application

Both services use multi-stage Docker builds for optimized production images.

## Image Build Strategy

### Tagging Strategy

Images should be tagged with the following strategy:

1. **SHA-based tags** (recommended for production):
   ```bash
   docker build -t exam-platform-backend:sha-${GITHUB_SHA} ./backend
   docker build -t exam-platform-frontend:sha-${GITHUB_SHA} ./frontend
   ```

2. **Staging tags**:
   ```bash
   docker build -t exam-platform-backend:staging ./backend
   docker build -t exam-platform-frontend:staging ./frontend
   ```

3. **Latest tags** (use with caution, only for explicit deployments):
   ```bash
   docker build -t exam-platform-backend:latest ./backend
   docker build -t exam-platform-frontend:latest ./frontend
   ```

**Best Practice**: Always use SHA-based tags for production deployments. Use `latest` only for development or when explicitly needed.

## Building Images

### Prerequisites

- Docker and Docker Compose installed
- Access to the repository
- Environment variables configured (see `.env.example`)

### Build Commands

#### Build Backend Image

```bash
# From repository root
cd backend
docker build \
  --build-arg GITHUB_SHA=${GITHUB_SHA:-$(git rev-parse HEAD)} \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  -t exam-platform-backend:sha-${GITHUB_SHA:-$(git rev-parse --short HEAD)} \
  -f Dockerfile \
  .
```

#### Build Frontend Image

```bash
# From repository root
cd frontend
docker build \
  --build-arg GITHUB_SHA=${GITHUB_SHA:-$(git rev-parse HEAD)} \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  -t exam-platform-frontend:sha-${GITHUB_SHA:-$(git rev-parse --short HEAD)} \
  -f Dockerfile \
  .
```

#### Build Both Images

```bash
# From repository root
GITHUB_SHA=${GITHUB_SHA:-$(git rev-parse HEAD)}
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

docker build \
  --build-arg GITHUB_SHA=${GITHUB_SHA} \
  --build-arg BUILD_DATE=${BUILD_DATE} \
  -t exam-platform-backend:sha-${GITHUB_SHA:0:7} \
  -f backend/Dockerfile \
  backend/

docker build \
  --build-arg GITHUB_SHA=${GITHUB_SHA} \
  --build-arg BUILD_DATE=${BUILD_DATE} \
  -t exam-platform-frontend:sha-${GITHUB_SHA:0:7} \
  -f frontend/Dockerfile \
  frontend/
```

### Using Docker Compose

The production compose file automatically builds images:

```bash
cd infra/docker/compose

# Build images
docker compose -f docker-compose.prod.yml build

# Build with specific tags
GITHUB_SHA=$(git rev-parse HEAD) \
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
docker compose -f docker-compose.prod.yml build \
  --build-arg GITHUB_SHA=${GITHUB_SHA} \
  --build-arg BUILD_DATE=${BUILD_DATE}
```

## Running Images

### Using Docker Compose (Recommended)

```bash
cd infra/docker/compose

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Start specific services
docker compose -f docker-compose.prod.yml up -d backend frontend

# View logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# Stop services
docker compose -f docker-compose.prod.yml down
```

### Standalone Docker Run

**Backend:**
```bash
docker run -d \
  --name exam-platform-backend \
  --network exam_platform_network \
  -e DATABASE_URL=postgresql+psycopg2://user:pass@postgres:5432/dbname \
  -e JWT_SECRET=your-secret \
  -e AUTH_TOKEN_PEPPER=your-pepper \
  -e ENV=prod \
  exam-platform-backend:sha-abc1234
```

**Frontend:**
```bash
docker run -d \
  --name exam-platform-frontend \
  --network exam_platform_network \
  -e NEXT_PUBLIC_API_BASE_URL=https://api.example.com/v1 \
  -e NODE_ENV=production \
  exam-platform-frontend:sha-abc1234
```

## Health Checks

Both images include health checks:

### Backend Health Check

```bash
# Check health endpoint
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Check readiness endpoint
curl http://localhost:8000/v1/ready
# Expected: {"status":"ok","checks":{...}}
```

### Frontend Health Check

```bash
# Check frontend root
curl http://localhost:3000/
# Expected: HTML response (200 OK)
```

### Using Docker Health Check

```bash
# Check container health status
docker ps
# Look for "healthy" status in STATUS column

# Inspect health check details
docker inspect --format='{{json .State.Health}}' exam-platform-backend | jq
```

## Image Metadata

Both images include OCI labels for traceability:

```bash
# View image labels
docker inspect exam-platform-backend:sha-abc1234 | jq '.[0].Config.Labels'

# Expected labels:
# - org.opencontainers.image.source
# - org.opencontainers.image.revision
# - org.opencontainers.image.created
# - org.opencontainers.image.title
# - org.opencontainers.image.description
```

## Image Optimization

### Backend Image

- **Base**: `python:3.11-slim` (minimal Python image)
- **Multi-stage**: Dependencies built in builder stage
- **Non-root user**: Runs as `appuser` (UID/GID 1000)
- **Size**: ~200-300MB (depending on dependencies)

### Frontend Image

- **Base**: `node:20-alpine` (Alpine Linux, minimal)
- **Multi-stage**: Build in builder, runtime in minimal image
- **Standalone mode**: Next.js standalone output (minimal dependencies)
- **Non-root user**: Runs as `nextjs` (UID 1001)
- **Size**: ~150-200MB (standalone mode significantly reduces size)

## Build Cache Optimization

Both Dockerfiles are optimized for layer caching:

1. **Dependency files copied first** (requirements.txt, package.json, pnpm-lock.yaml)
2. **Dependencies installed before source code**
3. **Source code copied last** (changes most frequently)

This ensures dependency installation layers are cached and only rebuilt when dependencies change.

## Troubleshooting

### Build Failures

**Backend:**
```bash
# Check Python version compatibility
python --version  # Should be 3.11+

# Verify requirements.txt is valid
pip install --dry-run -r backend/requirements.txt

# Check for missing system dependencies
docker build --progress=plain -f backend/Dockerfile backend/ 2>&1 | grep -i error
```

**Frontend:**
```bash
# Check Node.js version
node --version  # Should be 20.x

# Verify pnpm lockfile is valid
cd frontend && pnpm install --frozen-lockfile

# Check for build errors
docker build --progress=plain -f frontend/Dockerfile frontend/ 2>&1 | grep -i error
```

### Runtime Issues

**Backend not starting:**
```bash
# Check logs
docker logs exam-platform-backend

# Verify database connectivity
docker exec exam-platform-backend python -c "from app.db.engine import engine; engine.connect()"

# Check health endpoint
curl http://localhost:8000/health
```

**Frontend not starting:**
```bash
# Check logs
docker logs exam-platform-frontend

# Verify Next.js server is running
docker exec exam-platform-frontend ps aux | grep node

# Check if port is listening
docker exec exam-platform-frontend netstat -tlnp | grep 3000
```

### Image Size Issues

```bash
# Analyze image layers
docker history exam-platform-backend:sha-abc1234

# Check for large files
docker run --rm exam-platform-backend:sha-abc1234 du -sh /*

# Compare image sizes
docker images | grep exam-platform
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Build Backend Image
  run: |
    docker build \
      --build-arg GITHUB_SHA=${{ github.sha }} \
      --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
      -t exam-platform-backend:sha-${{ github.sha }} \
      -f backend/Dockerfile \
      backend/

- name: Build Frontend Image
  run: |
    docker build \
      --build-arg GITHUB_SHA=${{ github.sha }} \
      --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
      -t exam-platform-frontend:sha-${{ github.sha }} \
      -f frontend/Dockerfile \
      frontend/
```

### Pushing to Registry

```bash
# Tag for registry
docker tag exam-platform-backend:sha-abc1234 registry.example.com/exam-platform-backend:sha-abc1234
docker tag exam-platform-frontend:sha-abc1234 registry.example.com/exam-platform-frontend:sha-abc1234

# Push to registry
docker push registry.example.com/exam-platform-backend:sha-abc1234
docker push registry.example.com/exam-platform-frontend:sha-abc1234
```

## Security Best Practices

1. **Non-root users**: Both images run as non-root users
2. **Minimal base images**: Using slim/alpine variants
3. **No secrets in images**: All secrets via environment variables
4. **Health checks**: Enable container orchestration health monitoring
5. **OCI labels**: Include source and revision for traceability
6. **Layer caching**: Optimized for security updates (dependencies layer separate)

## Maintenance

### Updating Base Images

```bash
# Pull latest base images
docker pull python:3.11-slim
docker pull node:20-alpine

# Rebuild with updated bases
docker build --pull -f backend/Dockerfile backend/
docker build --pull -f frontend/Dockerfile frontend/
```

### Dependency Updates

```bash
# Backend: Update requirements.txt, then rebuild
cd backend
pip-compile requirements.in  # If using pip-tools
docker build -f Dockerfile .

# Frontend: Update package.json, then rebuild
cd frontend
pnpm update
docker build -f Dockerfile .
```

## Verification Commands

After building and starting containers:

```bash
# 1. Verify containers are running
docker compose -f infra/docker/compose/docker-compose.prod.yml ps

# 2. Check backend health
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 3. Check frontend
curl http://localhost:3000/
# Expected: HTML response

# 4. Verify via Traefik (if configured)
curl -H "Host: api.example.com" http://localhost/health
curl -H "Host: example.com" http://localhost/
```

## Image Registry

For production deployments, push images to a container registry:

```bash
# Example: Docker Hub
docker tag exam-platform-backend:sha-abc1234 your-org/exam-platform-backend:sha-abc1234
docker push your-org/exam-platform-backend:sha-abc1234

# Example: AWS ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag exam-platform-backend:sha-abc1234 <account>.dkr.ecr.<region>.amazonaws.com/exam-platform-backend:sha-abc1234
docker push <account>.dkr.ecr.<region>.amazonaws.com/exam-platform-backend:sha-abc1234
```

## Files Reference

- `backend/Dockerfile` - Backend production Dockerfile
- `backend/.dockerignore` - Backend build context exclusions
- `frontend/Dockerfile` - Frontend production Dockerfile
- `frontend/.dockerignore` - Frontend build context exclusions
- `infra/docker/compose/docker-compose.prod.yml` - Production compose file
