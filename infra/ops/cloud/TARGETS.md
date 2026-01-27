# Cloud Deployment Targets

This document describes deployment options for the Exam Prep Platform on AWS and Azure, focusing on container-first approaches with a path to Kubernetes.

## Overview

Three deployment tracks are available for each cloud provider:

- **Track A**: VPS/VM + Docker Compose (fastest to deploy, simplest ops)
- **Track B**: Managed Containers (serverless containers, minimal ops)
- **Track C**: Kubernetes (EKS/AKS, maximum control, future-ready)

All tracks assume:
- **Edge**: Cloudflare (CDN, WAF, DDoS protection)
- **Reverse Proxy**: Traefik (routing, TLS termination)
- **Application**: Backend (FastAPI) + Frontend (Next.js) containers
- **Data**: Managed PostgreSQL + Managed Redis
- **Observability**: Prometheus/Grafana/Tempo stack (or cloud-native equivalents)

## Day-1 Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Cloudflare                           │
│              (CDN, WAF, DDoS Protection)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Traefik (Reverse Proxy)                    │
│              (TLS Termination, Routing)                       │
└──────┬──────────────────────────────────────┬─────────────────┘
       │                                      │
       │                                      │
┌──────▼──────────┐                  ┌───────▼──────────┐
│   Frontend      │                  │    Backend        │
│   (Next.js)     │                  │   (FastAPI)       │
│   Container     │                  │   Container       │
└─────────────────┘                  └────────┬──────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
         ┌──────────▼──────────┐   ┌─────────▼──────────┐   ┌─────────▼──────────┐
         │  Managed PostgreSQL │   │   Managed Redis    │   │  Observability     │
         │  (RDS / Azure DB)   │   │ (ElastiCache /     │   │  (Prometheus/      │
         │                     │   │  Azure Cache)      │   │   Grafana/Tempo)   │
         └─────────────────────┘   └────────────────────┘   └────────────────────┘
```

## AWS Deployment Tracks

### Track A: EC2 + Docker Compose

**Best For**: Quick deployment, cost optimization, full control

**Architecture:**
- **Compute**: EC2 instance (t3.medium or larger)
- **Orchestration**: Docker Compose
- **Load Balancer**: Application Load Balancer (ALB) or Cloudflare (if using Cloudflare)
- **Database**: Amazon RDS for PostgreSQL
- **Cache**: Amazon ElastiCache for Redis
- **Storage**: EBS volumes for Docker volumes
- **Networking**: VPC with public/private subnets

**Pros:**
- ✅ Fastest to deploy (familiar Docker Compose)
- ✅ Lowest cost for small-medium scale
- ✅ Full control over infrastructure
- ✅ Easy to migrate from existing deployments

**Cons:**
- ❌ Manual scaling (requires instance resizing or multiple instances)
- ❌ Higher ops burden (OS updates, security patches)
- ❌ Single point of failure (unless multi-AZ setup)

**Estimated Monthly Cost** (small scale):
- EC2 t3.medium: ~$30-50
- RDS db.t3.micro: ~$15-25
- ElastiCache cache.t3.micro: ~$15-20
- **Total**: ~$60-95/month (excluding data transfer)

**Deployment Steps:**
1. Launch EC2 instance (Ubuntu 22.04 LTS)
2. Install Docker and Docker Compose
3. Configure security groups (ports 80, 443 from Cloudflare IPs only)
4. Deploy docker-compose.prod.yml
5. Configure RDS and ElastiCache
6. Update DNS to point to EC2 instance (via Cloudflare)

### Track B: ECS Fargate

**Best For**: Serverless containers, minimal ops, auto-scaling

**Architecture:**
- **Compute**: ECS Fargate tasks (backend + frontend)
- **Orchestration**: ECS service definitions
- **Load Balancer**: Application Load Balancer (ALB)
- **Database**: Amazon RDS for PostgreSQL
- **Cache**: Amazon ElastiCache for Redis
- **Networking**: VPC with Fargate tasks in private subnets
- **Service Discovery**: ECS service discovery or ALB target groups

**Pros:**
- ✅ No server management (serverless containers)
- ✅ Auto-scaling built-in
- ✅ Pay per use (only for running tasks)
- ✅ High availability (multi-AZ by default)

**Cons:**
- ❌ Higher cost at scale (vs EC2)
- ❌ Cold starts possible (minimal with always-on tasks)
- ❌ Less control over underlying infrastructure

**Estimated Monthly Cost** (small scale):
- ECS Fargate (2 tasks, 0.5 vCPU, 1GB each): ~$30-40
- ALB: ~$20-25
- RDS db.t3.micro: ~$15-25
- ElastiCache cache.t3.micro: ~$15-20
- **Total**: ~$80-110/month (excluding data transfer)

**Deployment Steps:**
1. Create ECS cluster (Fargate)
2. Create task definitions for backend and frontend
3. Create ECS services with auto-scaling
4. Configure ALB with target groups
5. Set up RDS and ElastiCache
6. Configure Cloudflare to point to ALB

### Track C: EKS (Elastic Kubernetes Service)

**Best For**: Kubernetes-native, maximum scalability, multi-cloud ready

**Architecture:**
- **Compute**: EKS cluster with managed node groups or Fargate
- **Orchestration**: Kubernetes (using manifests from `infra/k8s/`)
- **Load Balancer**: AWS Load Balancer Controller (ALB/NLB)
- **Database**: Amazon RDS for PostgreSQL
- **Cache**: Amazon ElastiCache for Redis
- **Ingress**: Traefik Ingress Controller or AWS ALB Ingress
- **Networking**: VPC CNI, private subnets for pods

**Pros:**
- ✅ Maximum scalability and flexibility
- ✅ Kubernetes ecosystem (Helm, operators, etc.)
- ✅ Multi-cloud portability
- ✅ Advanced features (HPA, VPA, network policies)

**Cons:**
- ❌ Highest complexity
- ❌ Higher cost (control plane + nodes)
- ❌ Steeper learning curve
- ❌ More moving parts to manage

**Estimated Monthly Cost** (small scale):
- EKS control plane: ~$73/month
- Managed node group (2x t3.medium): ~$60-100
- ALB: ~$20-25
- RDS db.t3.micro: ~$15-25
- ElastiCache cache.t3.micro: ~$15-20
- **Total**: ~$183-243/month (excluding data transfer)

**Deployment Steps:**
1. Create EKS cluster
2. Configure node groups or Fargate profiles
3. Install Traefik Ingress Controller
4. Apply Kubernetes manifests from `infra/k8s/`
5. Configure RDS and ElastiCache
6. Set up Cloudflare to point to ALB/NLB

## Azure Deployment Tracks

### Track A: Azure VM + Docker Compose

**Best For**: Quick deployment, cost optimization, full control

**Architecture:**
- **Compute**: Azure Virtual Machine (Standard_B2s or larger)
- **Orchestration**: Docker Compose
- **Load Balancer**: Azure Load Balancer or Application Gateway (or Cloudflare)
- **Database**: Azure Database for PostgreSQL (Flexible Server)
- **Cache**: Azure Cache for Redis
- **Storage**: Azure Managed Disks
- **Networking**: Virtual Network (VNet) with public/private subnets

**Pros:**
- ✅ Fastest to deploy (familiar Docker Compose)
- ✅ Lowest cost for small-medium scale
- ✅ Full control over infrastructure
- ✅ Easy to migrate from existing deployments

**Cons:**
- ❌ Manual scaling (requires VM resizing or multiple VMs)
- ❌ Higher ops burden (OS updates, security patches)
- ❌ Single point of failure (unless multi-region setup)

**Estimated Monthly Cost** (small scale):
- VM Standard_B2s: ~$30-50
- PostgreSQL Flexible Server (Burstable B1ms): ~$15-25
- Azure Cache for Redis (Basic C0): ~$15-20
- **Total**: ~$60-95/month (excluding data transfer)

**Deployment Steps:**
1. Create Azure VM (Ubuntu 22.04 LTS)
2. Install Docker and Docker Compose
3. Configure Network Security Groups (ports 80, 443 from Cloudflare IPs)
4. Deploy docker-compose.prod.yml
5. Configure Azure Database for PostgreSQL and Azure Cache for Redis
6. Update DNS to point to VM (via Cloudflare)

### Track B: Azure Container Apps

**Best For**: Serverless containers, minimal ops, auto-scaling

**Architecture:**
- **Compute**: Azure Container Apps (backend + frontend)
- **Orchestration**: Container Apps service
- **Load Balancer**: Built-in (Container Apps environment)
- **Database**: Azure Database for PostgreSQL (Flexible Server)
- **Cache**: Azure Cache for Redis
- **Networking**: VNet integration (optional)
- **Ingress**: Container Apps built-in ingress

**Pros:**
- ✅ No server management (serverless containers)
- ✅ Auto-scaling built-in (scale to zero)
- ✅ Pay per use (only for running containers)
- ✅ Integrated with Azure ecosystem

**Cons:**
- ❌ Azure-specific (less portable)
- ❌ Cold starts possible (minimal with always-on)
- ❌ Less control over networking

**Estimated Monthly Cost** (small scale):
- Container Apps (2 apps, 0.5 vCPU, 1GB each): ~$30-40
- Container Apps Environment: ~$0 (consumption plan)
- PostgreSQL Flexible Server (Burstable B1ms): ~$15-25
- Azure Cache for Redis (Basic C0): ~$15-20
- **Total**: ~$60-85/month (excluding data transfer)

**Deployment Steps:**
1. Create Container Apps Environment
2. Create Container Apps for backend and frontend
3. Configure ingress and scaling rules
4. Set up Azure Database for PostgreSQL and Azure Cache for Redis
5. Configure Cloudflare to point to Container Apps ingress

### Track C: AKS (Azure Kubernetes Service)

**Best For**: Kubernetes-native, maximum scalability, multi-cloud ready

**Architecture:**
- **Compute**: AKS cluster with node pools
- **Orchestration**: Kubernetes (using manifests from `infra/k8s/`)
- **Load Balancer**: Azure Load Balancer or Application Gateway
- **Database**: Azure Database for PostgreSQL (Flexible Server)
- **Cache**: Azure Cache for Redis
- **Ingress**: Traefik Ingress Controller or Application Gateway Ingress Controller
- **Networking**: Azure CNI or kubenet

**Pros:**
- ✅ Maximum scalability and flexibility
- ✅ Kubernetes ecosystem (Helm, operators, etc.)
- ✅ Multi-cloud portability
- ✅ Advanced features (HPA, VPA, network policies)

**Cons:**
- ❌ Highest complexity
- ❌ Higher cost (control plane + nodes)
- ❌ Steeper learning curve
- ❌ More moving parts to manage

**Estimated Monthly Cost** (small scale):
- AKS cluster (free tier): $0 (control plane)
- Node pool (2x Standard_B2s): ~$60-100
- Application Gateway (Basic): ~$25-35
- PostgreSQL Flexible Server (Burstable B1ms): ~$15-25
- Azure Cache for Redis (Basic C0): ~$15-20
- **Total**: ~$115-180/month (excluding data transfer)

**Deployment Steps:**
1. Create AKS cluster
2. Configure node pools
3. Install Traefik Ingress Controller
4. Apply Kubernetes manifests from `infra/k8s/`
5. Configure Azure Database for PostgreSQL and Azure Cache for Redis
6. Set up Cloudflare to point to Application Gateway

## Decision Matrix

| Factor | Track A (VM + Compose) | Track B (Managed Containers) | Track C (Kubernetes) |
|--------|------------------------|------------------------------|----------------------|
| **Cost (Small Scale)** | ⭐⭐⭐⭐⭐ Lowest | ⭐⭐⭐⭐ Low-Medium | ⭐⭐⭐ Medium-High |
| **Complexity** | ⭐⭐⭐⭐⭐ Simplest | ⭐⭐⭐⭐ Simple | ⭐⭐ Complex |
| **Ops Burden** | ⭐⭐ High (OS management) | ⭐⭐⭐⭐ Low (serverless) | ⭐⭐⭐ Medium (K8s management) |
| **Scalability** | ⭐⭐ Manual | ⭐⭐⭐⭐ Auto-scaling | ⭐⭐⭐⭐⭐ Maximum |
| **Portability** | ⭐⭐⭐⭐ High (Docker Compose) | ⭐⭐⭐ Medium (cloud-specific) | ⭐⭐⭐⭐⭐ Highest (K8s standard) |
| **Time to Deploy** | ⭐⭐⭐⭐⭐ Fastest | ⭐⭐⭐⭐ Fast | ⭐⭐⭐ Moderate |
| **Control** | ⭐⭐⭐⭐⭐ Full | ⭐⭐⭐ Limited | ⭐⭐⭐⭐⭐ Full |
| **High Availability** | ⭐⭐ Manual setup | ⭐⭐⭐⭐ Built-in | ⭐⭐⭐⭐⭐ Built-in |
| **Best For** | Small teams, MVP, cost-sensitive | Production, auto-scaling needs | Enterprise, multi-cloud |

**Legend**: ⭐ = Lower/Better, ⭐⭐⭐⭐⭐ = Higher/Better (for scalability, portability, control, HA)

## Recommended Progression

### Phase 1: MVP / Staging (Track A)
- Start with VM + Docker Compose
- Fastest to deploy and iterate
- Lowest cost for validation

### Phase 2: Production (Track B)
- Migrate to managed containers (ECS Fargate or Container Apps)
- Enable auto-scaling
- Reduce ops burden

### Phase 3: Scale / Enterprise (Track C)
- Migrate to Kubernetes (EKS or AKS)
- Maximum scalability and flexibility
- Multi-cloud portability

## Managed Services

### Database: PostgreSQL

**AWS:**
- **Amazon RDS for PostgreSQL**
  - Multi-AZ for high availability
  - Automated backups
  - Point-in-time recovery
  - Read replicas for scaling reads

**Azure:**
- **Azure Database for PostgreSQL (Flexible Server)**
  - Zone-redundant high availability
  - Automated backups
  - Point-in-time restore
  - Read replicas

**Configuration:**
- Instance size: Start with db.t3.micro (AWS) or Burstable B1ms (Azure)
- Storage: 20GB minimum, auto-grow enabled
- Backups: 7-day retention (minimum)
- Multi-AZ: Enable for production

### Cache: Redis

**AWS:**
- **Amazon ElastiCache for Redis**
  - Cluster mode for scaling
  - Automatic failover
  - Backup and restore

**Azure:**
- **Azure Cache for Redis**
  - Standard tier for high availability
  - Clustering for scaling
  - Persistence options

**Configuration:**
- Instance size: Start with cache.t3.micro (AWS) or Basic C0 (Azure)
- High availability: Enable for production
- Persistence: AOF enabled (if supported)

## Observability Stack

### Option 1: Self-Hosted (Prometheus/Grafana/Tempo)

**Deploy alongside application:**
- Prometheus: Metrics collection
- Grafana: Dashboards and visualization
- Tempo: Distributed tracing
- OpenTelemetry Collector: Instrumentation

**Pros:**
- Full control
- No vendor lock-in
- Cost-effective at scale

**Cons:**
- Higher ops burden
- Requires infrastructure management

### Option 2: Cloud-Native (AWS/Azure Managed)

**AWS:**
- **Amazon Managed Service for Prometheus**: Prometheus-compatible
- **Amazon Managed Grafana**: Grafana dashboards
- **AWS X-Ray**: Distributed tracing (alternative to Tempo)

**Azure:**
- **Azure Monitor**: Metrics and logs
- **Azure Monitor Managed Service for Prometheus**: Prometheus-compatible
- **Application Insights**: APM and tracing

**Pros:**
- Managed service (low ops burden)
- Integrated with cloud ecosystem
- Automatic scaling

**Cons:**
- Vendor lock-in
- Higher cost at scale
- Less control

**Recommendation**: Start with self-hosted for cost control, migrate to managed as scale increases.

## Networking Considerations

### Cloudflare Integration

All tracks should use Cloudflare in front:
- **DNS**: Point Cloudflare DNS to load balancer or VM
- **SSL/TLS**: Full (strict) mode (Cloudflare ↔ Origin: HTTPS)
- **WAF**: Cloudflare WAF rules (see `infra/ops/cloudflare/BASELINE.md`)
- **CDN**: Static asset caching

### Security Groups / Network Security Groups

**Common Rules:**
- **Inbound**: Port 80, 443 from Cloudflare IP ranges only
- **Outbound**: All traffic (for Cloudflare, database, cache access)
- **Internal**: Allow all traffic within VPC/VNet

**Cloudflare IP Ranges:**
- Update security groups regularly with Cloudflare IP ranges
- Use Cloudflare's IP list or API to automate updates

### Private Networking

**Best Practice:**
- Application containers in private subnets
- Database and cache in private subnets (no public access)
- Load balancer in public subnet (or use Cloudflare)
- NAT Gateway for outbound internet access

## Migration Path

### From Track A → Track B

1. Create ECS/Container Apps task definitions from docker-compose.yml
2. Migrate environment variables to Parameter Store / Key Vault
3. Update DNS to point to ALB/Container Apps ingress
4. Test and validate
5. Decommission EC2/VM

### From Track B → Track C

1. Use existing Kubernetes manifests from `infra/k8s/`
2. Create EKS/AKS cluster
3. Migrate container images to same registry
4. Apply Kubernetes manifests
5. Update DNS to point to Kubernetes ingress
6. Test and validate
7. Decommission ECS/Container Apps

## Cost Optimization Tips

1. **Right-Sizing**: Start small, scale up based on metrics
2. **Reserved Instances**: Use for predictable workloads (Track A)
3. **Spot Instances**: Use for non-critical workloads (Track C)
4. **Auto-Scaling**: Scale down during off-hours (Track B, C)
5. **Storage**: Use appropriate storage tiers
6. **Data Transfer**: Minimize data transfer costs (use Cloudflare CDN)

## Files Reference

- `infra/ops/cloud/TARGETS.md` - This file
- `infra/ops/cloudflare/BASELINE.md` - Cloudflare configuration
- `infra/k8s/` - Kubernetes manifests (Track C)
- `infra/docker/compose/docker-compose.prod.yml` - Docker Compose (Track A)
- `infra/ops/deploy/staging/docker-compose.staging.yml` - Staging compose file

## Runbook Integration

Operational procedures for cloud deployments are documented in:

- **[00-QuickStart.md](../runbooks/00-QuickStart.md)** - Health checks and restarts (adapt for cloud)
- **[01-Incident-Checklist.md](../runbooks/01-Incident-Checklist.md)** - Incident triage
- **[02-Rollback.md](../runbooks/02-Rollback.md)** - Rollback procedures
- **[03-Database.md](../runbooks/03-Database.md)** - Database operations (RDS/Azure DB)
- **[04-Redis.md](../runbooks/04-Redis.md)** - Cache operations (ElastiCache/Azure Cache)
- **[08-Cloudflare.md](../runbooks/08-Cloudflare.md)** - Cloudflare configuration

**Note**: Cloud provider-specific runbooks (AWS/Azure) are planned for future implementation.

## TODO Checklist

- [ ] Create Terraform modules for Track A (EC2/VM + Docker Compose)
- [ ] Create Terraform modules for Track B (ECS Fargate / Container Apps)
- [ ] Create Terraform modules for Track C (EKS / AKS)
- [ ] Add managed database Terraform modules (RDS / Azure DB)
- [ ] Add managed cache Terraform modules (ElastiCache / Azure Cache)
- [ ] Add load balancer Terraform modules (ALB / Application Gateway)
- [ ] Add observability stack Terraform modules
- [ ] Add cost estimation calculator
- [ ] Add migration guides (A→B, B→C)
- [ ] Add disaster recovery procedures
- [ ] Add multi-region deployment guides
- [ ] Add CI/CD integration for each track
- [ ] Add monitoring and alerting setup for each track
- [ ] Add cloud provider-specific runbooks (AWS/Azure)
