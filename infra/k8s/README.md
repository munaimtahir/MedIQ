# Kubernetes Manifests

Kubernetes deployment manifests for the Exam Prep Platform using Kustomize for environment-specific configurations.

## Structure

```
k8s/
├── base/                    # Base manifests (shared across environments)
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
│   └── kustomization.yaml
└── overlays/                # Environment-specific overlays
    └── staging/
        ├── kustomization.yaml
        ├── deployment-patch.yaml
        └── ingress-patch.yaml
```

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured to access your cluster
- Traefik Ingress Controller installed (or compatible Ingress Controller)
- PostgreSQL database (external/managed - not deployed in these manifests)
- GitHub Container Registry (GHCR) access for pulling images

## Quick Start

### 1. Create Secrets

**Important**: The `secret.yaml.template` file is a template. You must create actual secrets before deploying.

```bash
# Option 1: Create from template (edit values first)
kubectl create secret generic exam-platform-secrets \
  --from-file=secret.yaml.template \
  --dry-run=client -o yaml | \
  kubectl apply -f -

# Option 2: Create from literal values
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
```

### 2. Update Image References

Edit `k8s/overlays/staging/kustomization.yaml` and update image names:

```yaml
images:
  - name: ghcr.io/OWNER/REPO-backend
    newTag: staging  # or sha-abc1234 for specific version
  - name: ghcr.io/OWNER/REPO-frontend
    newTag: staging  # or sha-abc1234 for specific version
```

Replace `OWNER` and `REPO` with your GitHub username/organization and repository name.

### 3. Update Ingress Host

Edit `k8s/overlays/staging/ingress-patch.yaml` and update the host:

```yaml
spec:
  rules:
  - host: staging.example.com  # Change to your staging domain
```

### 4. Deploy to Staging

```bash
# Apply staging overlay
kubectl apply -k k8s/overlays/staging

# Verify deployment
kubectl get pods -n exam-platform
kubectl get services -n exam-platform
kubectl get ingress -n exam-platform
```

### 5. Check Deployment Status

```bash
# Watch pods
kubectl get pods -n exam-platform -w

# Check pod logs
kubectl logs -n exam-platform -l app=backend --tail=50
kubectl logs -n exam-platform -l app=frontend --tail=50

# Check pod status
kubectl describe pod -n exam-platform -l app=backend
```

## Required Secrets

The following secrets must be set in the `exam-platform-secrets` Secret:

| Key | Description | Required |
|-----|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `JWT_SECRET` | JWT signing secret | Yes |
| `JWT_ACCESS_TTL_MIN` | JWT access token TTL (minutes) | Yes |
| `JWT_REFRESH_TTL_DAYS` | JWT refresh token TTL (days) | Yes |
| `AUTH_TOKEN_PEPPER` | Auth token pepper | Yes |
| `MFA_ENCRYPTION_KEY` | MFA encryption key | Yes |
| `CORS_ALLOW_ORIGINS_APP` | CORS allowed origins (comma-separated) | Yes |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend API base URL | Yes |
| `NEXT_PUBLIC_APP_NAME` | Frontend app name | Yes |
| `DOMAIN` | Application domain | Yes |
| `FRONTEND_URL` | Frontend URL | Yes |
| `FRONTEND_BASE_URL` | Frontend base URL | Yes |
| `CORS_ALLOW_ORIGINS_PUBLIC` | Public CORS origins | No |
| `OAUTH_GOOGLE_CLIENT_ID` | Google OAuth client ID | No |
| `OAUTH_GOOGLE_CLIENT_SECRET` | Google OAuth client secret | No |
| `OAUTH_MICROSOFT_CLIENT_ID` | Microsoft OAuth client ID | No |
| `OAUTH_MICROSOFT_CLIENT_SECRET` | Microsoft OAuth client secret | No |
| `EMAIL_HOST` | SMTP host | No |
| `EMAIL_USER` | SMTP user | No |
| `EMAIL_PASSWORD` | SMTP password | No |
| `EMAIL_FROM` | Email from address | No |

## Setting Image Tags

### Using Kustomize (Recommended)

Edit `k8s/overlays/staging/kustomization.yaml`:

```yaml
images:
  - name: ghcr.io/OWNER/REPO-backend
    newTag: sha-abc1234  # Specific SHA
  - name: ghcr.io/OWNER/REPO-frontend
    newTag: sha-abc1234  # Specific SHA
```

Then apply:

```bash
kubectl apply -k k8s/overlays/staging
```

### Using kubectl set image

```bash
kubectl set image deployment/backend backend=ghcr.io/OWNER/REPO-backend:sha-abc1234 -n exam-platform
kubectl set image deployment/frontend frontend=ghcr.io/OWNER/REPO-frontend:sha-abc1234 -n exam-platform
```

## Health Checks

### Backend

- **Liveness**: `GET /v1/health` (checks if process is alive)
- **Readiness**: `GET /v1/ready` (checks database and Redis connectivity)

### Frontend

- **Liveness**: `GET /` (checks if server responds)
- **Readiness**: `GET /` (checks if server responds)

### Redis

- **Liveness**: `redis-cli ping`
- **Readiness**: `redis-cli ping`

## Ingress Configuration

The Ingress is configured for Traefik Ingress Controller with:

- **Routes**:
  - `/` → Frontend service (port 3000)
  - `/api` → Backend service (port 8000)
- **TLS**: Automatic certificate management via Let's Encrypt
- **Annotations**: Traefik-specific annotations for middleware and routing

### Customizing Ingress

For different Ingress Controllers (nginx, AWS ALB, etc.), modify `ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    # nginx example
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
```

## Database (PostgreSQL)

**Important**: PostgreSQL is **not** deployed in these manifests. It is assumed to be:

- External managed database (AWS RDS, Google Cloud SQL, Azure Database, etc.)
- Managed database service (DigitalOcean Managed Databases, etc.)
- Separate PostgreSQL deployment

The `DATABASE_URL` secret must point to your external PostgreSQL instance.

### Running Migrations

Before deploying, run database migrations:

```bash
# Option 1: Run migrations in a Job
kubectl run migration-job \
  --image=ghcr.io/OWNER/REPO-backend:staging \
  --restart=Never \
  --rm -it \
  --env="DATABASE_URL=$(kubectl get secret exam-platform-secrets -n exam-platform -o jsonpath='{.data.DATABASE_URL}' | base64 -d)" \
  -- alembic upgrade head

# Option 2: Use init container (add to deployment)
# See: https://kubernetes.io/docs/concepts/workloads/pods/init-containers/
```

## Redis

Redis is deployed as a Deployment with:

- **Storage**: `emptyDir` (ephemeral - data lost on pod restart)
- **Persistence**: `appendonly yes` (AOF enabled)
- **Memory**: 256MB limit with LRU eviction

### Persistent Redis (Optional)

For production, consider using a StatefulSet with persistent volumes:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
spec:
  serviceName: redis-service
  replicas: 1
  template:
    spec:
      containers:
      - name: redis
        volumeMounts:
        - name: redis-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

## Scaling

### Horizontal Pod Autoscaling (HPA)

```bash
# Install metrics-server first
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Create HPA for backend
kubectl autoscale deployment backend \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n exam-platform

# Create HPA for frontend
kubectl autoscale deployment frontend \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n exam-platform
```

### Manual Scaling

```bash
kubectl scale deployment backend --replicas=5 -n exam-platform
kubectl scale deployment frontend --replicas=3 -n exam-platform
```

## Monitoring

### View Pod Logs

```bash
# Backend logs
kubectl logs -n exam-platform -l app=backend --tail=100 -f

# Frontend logs
kubectl logs -n exam-platform -l app=frontend --tail=100 -f

# Redis logs
kubectl logs -n exam-platform -l app=redis --tail=100 -f
```

### Check Resource Usage

```bash
kubectl top pods -n exam-platform
kubectl top nodes
```

### Describe Resources

```bash
kubectl describe deployment backend -n exam-platform
kubectl describe pod <pod-name> -n exam-platform
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n exam-platform

# Describe pod for events
kubectl describe pod <pod-name> -n exam-platform

# Check logs
kubectl logs <pod-name> -n exam-platform
```

### Image Pull Errors

```bash
# Check if image exists
docker pull ghcr.io/OWNER/REPO-backend:staging

# Verify image pull secrets (if using private registry)
kubectl get secrets -n exam-platform

# Create image pull secret for GHCR
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=USERNAME \
  --docker-password=TOKEN \
  --namespace=exam-platform

# Add to deployment
# Add imagePullSecrets to deployment spec
```

### Health Check Failures

```bash
# Test health endpoint manually
kubectl port-forward -n exam-platform svc/backend-service 8000:8000
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/ready

# Check probe configuration
kubectl get deployment backend -n exam-platform -o yaml | grep -A 10 livenessProbe
```

### Database Connection Issues

```bash
# Verify DATABASE_URL secret
kubectl get secret exam-platform-secrets -n exam-platform -o jsonpath='{.data.DATABASE_URL}' | base64 -d

# Test connection from pod
kubectl exec -n exam-platform -it deployment/backend -- python -c "from app.db.engine import engine; engine.connect()"
```

### Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n exam-platform
kubectl describe ingress exam-platform-ingress -n exam-platform

# Check Traefik logs
kubectl logs -n traefik-system -l app.kubernetes.io/name=traefik --tail=50

# Test ingress from inside cluster
kubectl run test-pod --image=curlimages/curl --rm -it --restart=Never -- curl http://frontend-service.exam-platform.svc.cluster.local:3000/
```

## Updating Deployments

### Rolling Update

```bash
# Update image tag
kubectl set image deployment/backend backend=ghcr.io/OWNER/REPO-backend:sha-new123 -n exam-platform

# Watch rollout
kubectl rollout status deployment/backend -n exam-platform

# Rollback if needed
kubectl rollout undo deployment/backend -n exam-platform
```

### Using Kustomize

```bash
# Edit kustomization.yaml with new image tags
# Then apply
kubectl apply -k k8s/overlays/staging
```

## Cleanup

```bash
# Delete all resources in namespace
kubectl delete namespace exam-platform

# Or delete specific resources
kubectl delete -k k8s/overlays/staging
```

## Security Considerations

1. **Secrets**: Never commit real secrets. Use external-secrets-operator or sealed-secrets
2. **Image Pull Secrets**: Configure for private registries
3. **Network Policies**: Consider adding NetworkPolicies to restrict pod-to-pod communication
4. **Pod Security Standards**: Deployments use non-root users and drop all capabilities
5. **Resource Limits**: All containers have resource requests and limits
6. **TLS**: Ingress uses TLS with Let's Encrypt certificates

## Production Considerations

1. **PostgreSQL**: Use managed database service with backups, high availability
2. **Redis**: Use managed Redis service or StatefulSet with persistent volumes
3. **Monitoring**: Add Prometheus, Grafana for metrics and alerting
4. **Logging**: Add centralized logging (ELK, Loki, etc.)
5. **Backups**: Set up database backups and disaster recovery
6. **HPA**: Configure horizontal pod autoscaling
7. **PDB**: Add PodDisruptionBudgets for high availability
8. **Resource Quotas**: Set namespace resource quotas

## Files Reference

- `k8s/base/` - Base manifests (shared)
- `k8s/overlays/staging/` - Staging-specific overlays
- `k8s/README.md` - This file

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
