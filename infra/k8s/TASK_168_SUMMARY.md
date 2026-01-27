# Task 168: Starter Kubernetes Manifests - COMPLETE ✅

## Summary

Created minimal, production-ready Kubernetes manifests using Kustomize for environment-specific configurations. The manifests deploy backend, frontend, and Redis services with proper health checks, security, and Ingress routing.

## Files Created

### Base Manifests (`k8s/base/`)
- `namespace.yaml` - Exam Platform namespace ✅ **NEW**
- `configmap.yaml` - Non-secret environment variables ✅ **NEW**
- `secret.yaml.template` - Secret template (not committed) ✅ **NEW**
- `backend-deployment.yaml` - Backend deployment with probes ✅ **NEW**
- `backend-service.yaml` - Backend ClusterIP service ✅ **NEW**
- `frontend-deployment.yaml` - Frontend deployment with probes ✅ **NEW**
- `frontend-service.yaml` - Frontend ClusterIP service ✅ **NEW**
- `redis-deployment.yaml` - Redis deployment ✅ **NEW**
- `redis-service.yaml` - Redis ClusterIP service (internal only) ✅ **NEW**
- `ingress.yaml` - Traefik-compatible Ingress ✅ **NEW**
- `kustomization.yaml` - Base Kustomize configuration ✅ **NEW**
- `.gitignore` - Ignore actual secret files ✅ **NEW**

### Staging Overlay (`k8s/overlays/staging/`)
- `kustomization.yaml` - Staging-specific Kustomize config ✅ **NEW**
- `deployment-patch.yaml` - Staging environment patches ✅ **NEW**
- `ingress-patch.yaml` - Staging Ingress configuration ✅ **NEW**

### Documentation
- `k8s/README.md` - Comprehensive deployment guide ✅ **UPDATED**

## Key Features

### Backend Deployment
- ✅ Replicas: 2 (configurable)
- ✅ Liveness probe: `/v1/health`
- ✅ Readiness probe: `/v1/ready`
- ✅ Resource limits: 1Gi memory, 1500m CPU
- ✅ Security: Non-root user (UID 1000), dropped capabilities
- ✅ Environment: ConfigMap + Secrets

### Frontend Deployment
- ✅ Replicas: 2 (configurable)
- ✅ Liveness probe: `/`
- ✅ Readiness probe: `/`
- ✅ Resource limits: 512Mi memory, 1000m CPU
- ✅ Security: Non-root user (UID 1001), dropped capabilities
- ✅ Environment: ConfigMap + Secrets

### Redis Deployment
- ✅ Replicas: 1
- ✅ Liveness probe: `redis-cli ping`
- ✅ Readiness probe: `redis-cli ping`
- ✅ Storage: `emptyDir` (ephemeral)
- ✅ Persistence: AOF enabled
- ✅ Memory: 256MB limit with LRU eviction
- ✅ **Not exposed publicly** (ClusterIP only)

### Ingress Configuration
- ✅ Traefik Ingress Controller compatible
- ✅ Routes:
  - `/` → Frontend service (port 3000)
  - `/api` → Backend service (port 8000)
- ✅ TLS: Automatic Let's Encrypt certificates
- ✅ Annotations: Traefik-specific middleware

### Kustomize Structure
- ✅ Base manifests in `k8s/base/`
- ✅ Staging overlay in `k8s/overlays/staging/`
- ✅ Image tag overrides via Kustomize
- ✅ Environment-specific patches

## Health Checks

### Backend
- **Liveness**: `GET /v1/health` (initial delay: 30s, period: 10s)
- **Readiness**: `GET /v1/ready` (initial delay: 10s, period: 5s)

### Frontend
- **Liveness**: `GET /` (initial delay: 30s, period: 10s)
- **Readiness**: `GET /` (initial delay: 10s, period: 5s)

### Redis
- **Liveness**: `redis-cli ping` (initial delay: 10s, period: 10s)
- **Readiness**: `redis-cli ping` (initial delay: 5s, period: 5s)

## Deployment Commands

### Deploy to Staging

```bash
# 1. Create secrets (required before deployment)
kubectl create secret generic exam-platform-secrets \
  --namespace=exam-platform \
  --from-literal=DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/db" \
  --from-literal=JWT_SECRET="your-secret" \
  --from-literal=AUTH_TOKEN_PEPPER="your-pepper" \
  --from-literal=MFA_ENCRYPTION_KEY="your-key" \
  --from-literal=REDIS_URL="redis://redis-service:6379/0" \
  --from-literal=CORS_ALLOW_ORIGINS_APP="https://staging.example.com" \
  --from-literal=NEXT_PUBLIC_API_BASE_URL="https://api-staging.example.com/v1" \
  --from-literal=NEXT_PUBLIC_APP_NAME="Exam Prep Platform (Staging)" \
  --from-literal=DOMAIN="example.com" \
  --from-literal=FRONTEND_URL="https://staging.example.com" \
  --from-literal=FRONTEND_BASE_URL="https://staging.example.com"

# 2. Update image references in k8s/overlays/staging/kustomization.yaml
# Replace OWNER and REPO with your GitHub username/organization and repo name

# 3. Update Ingress host in k8s/overlays/staging/ingress-patch.yaml
# Change staging.example.com to your staging domain

# 4. Deploy
kubectl apply -k k8s/overlays/staging

# 5. Verify
kubectl get pods -n exam-platform
kubectl get services -n exam-platform
kubectl get ingress -n exam-platform
```

## Required Secrets

The following secrets must be configured:

| Key | Description | Required |
|-----|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `JWT_SECRET` | JWT signing secret | Yes |
| `JWT_ACCESS_TTL_MIN` | JWT access token TTL | Yes |
| `JWT_REFRESH_TTL_DAYS` | JWT refresh token TTL | Yes |
| `AUTH_TOKEN_PEPPER` | Auth token pepper | Yes |
| `MFA_ENCRYPTION_KEY` | MFA encryption key | Yes |
| `CORS_ALLOW_ORIGINS_APP` | CORS allowed origins | Yes |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend API base URL | Yes |
| `NEXT_PUBLIC_APP_NAME` | Frontend app name | Yes |
| `DOMAIN` | Application domain | Yes |
| `FRONTEND_URL` | Frontend URL | Yes |
| `FRONTEND_BASE_URL` | Frontend base URL | Yes |

## Setting Image Tags

### Using Kustomize (Recommended)

Edit `k8s/overlays/staging/kustomization.yaml`:

```yaml
images:
  - name: ghcr.io/OWNER/REPO-backend
    newTag: sha-abc1234  # or staging, latest, etc.
  - name: ghcr.io/OWNER/REPO-frontend
    newTag: sha-abc1234
```

Then apply:

```bash
kubectl apply -k k8s/overlays/staging
```

## Caveats

### PostgreSQL
- ✅ **Not deployed** - Assumed external/managed
- ✅ Connection string provided via `DATABASE_URL` secret
- ✅ Examples: AWS RDS, Google Cloud SQL, Azure Database, DigitalOcean Managed Databases

### Redis
- ✅ Deployed as Deployment (ephemeral storage)
- ✅ For production, consider StatefulSet with persistent volumes
- ✅ Or use managed Redis service

### Image Pull Secrets
- ✅ If using private GHCR, create image pull secret:
  ```bash
  kubectl create secret docker-registry ghcr-secret \
    --docker-server=ghcr.io \
    --docker-username=USERNAME \
    --docker-password=TOKEN \
    --namespace=exam-platform
  ```
- ✅ Add `imagePullSecrets` to deployment specs

## Security Features

- ✅ Non-root users (backend: UID 1000, frontend: UID 1001)
- ✅ Dropped all capabilities
- ✅ Resource limits on all containers
- ✅ Secrets stored in Kubernetes Secrets (not ConfigMaps)
- ✅ Redis not exposed publicly (ClusterIP only)
- ✅ TLS enabled on Ingress

## File Tree

```
k8s/
├── base/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml.template
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── redis-deployment.yaml
│   ├── redis-service.yaml
│   ├── ingress.yaml
│   ├── kustomization.yaml
│   └── .gitignore
├── overlays/
│   └── staging/
│       ├── kustomization.yaml
│       ├── deployment-patch.yaml
│       └── ingress-patch.yaml
├── README.md
└── TASK_168_SUMMARY.md
```

## Verification Checklist

After deployment:

- [ ] Namespace created: `kubectl get namespace exam-platform`
- [ ] ConfigMap created: `kubectl get configmap -n exam-platform`
- [ ] Secrets created: `kubectl get secrets -n exam-platform`
- [ ] Backend pods running: `kubectl get pods -n exam-platform -l app=backend`
- [ ] Frontend pods running: `kubectl get pods -n exam-platform -l app=frontend`
- [ ] Redis pod running: `kubectl get pods -n exam-platform -l app=redis`
- [ ] Services created: `kubectl get services -n exam-platform`
- [ ] Ingress created: `kubectl get ingress -n exam-platform`
- [ ] Backend health check passes: `kubectl exec -n exam-platform deployment/backend -- curl http://localhost:8000/v1/health`
- [ ] Frontend responds: `kubectl exec -n exam-platform deployment/frontend -- wget -qO- http://localhost:3000/`
- [ ] Redis responds: `kubectl exec -n exam-platform deployment/redis -- redis-cli ping`

## Runbook Integration

Kubernetes deployment procedures can be adapted from Docker Compose runbooks:

- **[00-QuickStart.md](../ops/runbooks/00-QuickStart.md)** - Health checks (adapt `kubectl` commands)
- **[01-Incident-Checklist.md](../ops/runbooks/01-Incident-Checklist.md)** - Incident triage
- **[02-Rollback.md](../ops/runbooks/02-Rollback.md)** - Rollback procedures (adapt for K8s)
- **[03-Database.md](../ops/runbooks/03-Database.md)** - Database operations
- **[04-Redis.md](../ops/runbooks/04-Redis.md)** - Redis troubleshooting
- **[06-Observability.md](../ops/runbooks/06-Observability.md)** - Observability tools

**Note**: A dedicated Kubernetes runbook is planned for future implementation.

## TODO Checklist

- [ ] Add production overlay (`k8s/overlays/prod/`)
- [ ] Add PodDisruptionBudgets for high availability
- [ ] Add NetworkPolicies for pod-to-pod security
- [ ] Add HorizontalPodAutoscaler configurations
- [ ] Add VerticalPodAutoscaler configurations
- [ ] Add Prometheus ServiceMonitor for metrics scraping
- [ ] Add Grafana dashboards
- [ ] Add database migration Job/CronJob
- [ ] Add persistent Redis StatefulSet option
- [ ] Add backup CronJob for Redis (if using persistent storage)
- [ ] Add init containers for pre-deployment checks
- [ ] Add resource quotas and limit ranges
- [ ] Add monitoring and alerting (Prometheus, Alertmanager)
- [ ] Add centralized logging (Loki, ELK)
- [ ] Add distributed tracing (Jaeger, Tempo)
- [ ] Add GitOps integration (ArgoCD, Flux)
- [ ] Add multi-region deployment support
- [ ] Add blue-green deployment strategy
- [ ] Add canary deployment support
- [ ] Add chaos engineering tests (Chaos Mesh, Litmus)
