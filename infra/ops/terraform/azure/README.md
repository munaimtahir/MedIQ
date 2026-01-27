# Azure Terraform Modules

Terraform modules for deploying the Exam Prep Platform to Azure.

## Structure

```
terraform/azure/
├── README.md                    # This file
├── main.tf                      # Main configuration (stub)
├── variables.tf                 # Variable definitions
├── outputs.tf                   # Output definitions
├── terraform.tfvars.example     # Example variable values
└── modules/
    ├── track-a-vm/              # Track A: VM + Docker Compose
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── track-b-container-apps/  # Track B: Container Apps
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── track-c-aks/             # Track C: AKS
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── database/                # Azure Database for PostgreSQL
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── cache/                   # Azure Cache for Redis
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── networking/              # Virtual Network, subnets, NSGs
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
- Azure CLI configured with credentials
- Azure subscription with appropriate permissions
- Domain DNS managed (Cloudflare recommended)

## Quick Start

### Track A: VM + Docker Compose

```bash
cd terraform/azure/modules/track-a-vm
terraform init
terraform plan -var-file=../../terraform.tfvars
terraform apply
```

### Track B: Container Apps

```bash
cd terraform/azure/modules/track-b-container-apps
terraform init
terraform plan -var-file=../../terraform.tfvars
terraform apply
```

### Track C: AKS

```bash
cd terraform/azure/modules/track-c-aks
terraform init
terraform plan -var-file=../../terraform.tfvars
terraform apply
```

## Variables

See `variables.tf` for complete variable definitions. Key variables:

- `azure_location`: Azure region (e.g., `eastus`)
- `environment`: Environment name (e.g., `staging`, `prod`)
- `domain`: Domain name (e.g., `example.com`)
- `image_backend`: Backend container image
- `image_frontend`: Frontend container image
- `database_sku_name`: PostgreSQL SKU (e.g., `B_Standard_B1ms`)
- `cache_sku_name`: Redis SKU (e.g., `Basic`)

## Outputs

Common outputs across all tracks:

- `load_balancer_ip`: Load balancer IP address (for Cloudflare DNS)
- `database_endpoint`: Azure Database endpoint
- `cache_endpoint`: Azure Cache endpoint
- `vnet_id`: Virtual Network ID

## State Management

**Recommended**: Use remote state (Azure Storage):

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name  = "terraformstate"
    container_name        = "terraform-state"
    key                   = "exam-platform/terraform.tfstate"
  }
}
```

## Security

- **Secrets**: Use Azure Key Vault
- **RBAC**: Least privilege principle
- **Encryption**: Enable encryption at rest for database, cache
- **Network**: Private subnets for application, database, cache

## Cost Estimation

Use `terraform plan` with cost estimation plugins or Azure Cost Calculator.

## TODO

- [ ] Implement Track A module (VM + Docker Compose)
- [ ] Implement Track B module (Container Apps)
- [ ] Implement Track C module (AKS)
- [ ] Implement database module (Azure Database for PostgreSQL)
- [ ] Implement cache module (Azure Cache for Redis)
- [ ] Implement networking module (Virtual Network)
- [ ] Implement observability module
- [ ] Add remote state configuration
- [ ] Add CI/CD integration
- [ ] Add cost estimation
- [ ] Add disaster recovery procedures
