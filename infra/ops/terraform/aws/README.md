# AWS Terraform Modules

Terraform modules for deploying the Exam Prep Platform to AWS.

## Structure

```
terraform/aws/
├── README.md                    # This file
├── main.tf                      # Main configuration (stub)
├── variables.tf                 # Variable definitions
├── outputs.tf                   # Output definitions
├── terraform.tfvars.example     # Example variable values
└── modules/
    ├── track-a-vm/              # Track A: EC2 + Docker Compose
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── track-b-ecs/             # Track B: ECS Fargate
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── track-c-eks/             # Track C: EKS
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── database/                # RDS PostgreSQL
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── cache/                   # ElastiCache Redis
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── networking/              # VPC, subnets, security groups
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    └── observability/          # Prometheus, Grafana, Tempo
        ├── main.tf
        ├── variables.tf
        ├── outputs.tf
        └── README.md
```

## Prerequisites

- Terraform 1.5+
- AWS CLI configured with credentials
- AWS account with appropriate permissions
- Domain DNS managed (Cloudflare recommended)

## Quick Start

### Track A: EC2 + Docker Compose

```bash
cd terraform/aws/modules/track-a-vm
terraform init
terraform plan -var-file=../../terraform.tfvars
terraform apply
```

### Track B: ECS Fargate

```bash
cd terraform/aws/modules/track-b-ecs
terraform init
terraform plan -var-file=../../terraform.tfvars
terraform apply
```

### Track C: EKS

```bash
cd terraform/aws/modules/track-c-eks
terraform init
terraform plan -var-file=../../terraform.tfvars
terraform apply
```

## Variables

See `variables.tf` for complete variable definitions. Key variables:

- `aws_region`: AWS region (e.g., `us-east-1`)
- `environment`: Environment name (e.g., `staging`, `prod`)
- `domain`: Domain name (e.g., `example.com`)
- `image_backend`: Backend container image (e.g., `ghcr.io/owner/repo-backend:staging`)
- `image_frontend`: Frontend container image (e.g., `ghcr.io/owner/repo-frontend:staging`)
- `database_instance_class`: RDS instance class (e.g., `db.t3.micro`)
- `cache_node_type`: ElastiCache node type (e.g., `cache.t3.micro`)

## Outputs

Common outputs across all tracks:

- `load_balancer_dns`: Load balancer DNS name (for Cloudflare DNS)
- `database_endpoint`: RDS endpoint
- `cache_endpoint`: ElastiCache endpoint
- `vpc_id`: VPC ID

## State Management

**Recommended**: Use remote state (S3 + DynamoDB):

```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "exam-platform/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

## Security

- **Secrets**: Use AWS Secrets Manager or Parameter Store
- **IAM**: Least privilege principle
- **Encryption**: Enable encryption at rest for RDS, ElastiCache
- **Network**: Private subnets for application, database, cache

## Cost Estimation

Use `terraform plan` with cost estimation plugins or AWS Cost Calculator.

## TODO

- [ ] Implement Track A module (EC2 + Docker Compose)
- [ ] Implement Track B module (ECS Fargate)
- [ ] Implement Track C module (EKS)
- [ ] Implement database module (RDS)
- [ ] Implement cache module (ElastiCache)
- [ ] Implement networking module (VPC)
- [ ] Implement observability module
- [ ] Add remote state configuration
- [ ] Add CI/CD integration
- [ ] Add cost estimation
- [ ] Add disaster recovery procedures
