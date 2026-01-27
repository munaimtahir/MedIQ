# Track A: VM + Docker Compose Module

Terraform module for deploying Exam Prep Platform on Azure VM with Docker Compose.

## Usage

```hcl
module "track_a_vm" {
  source = "./modules/track-a-vm"

  azure_location = var.azure_location
  environment    = var.environment
  domain         = var.domain

  vm_size = "Standard_B2s"
  
  vnet_id              = module.networking.vnet_id
  subnet_id            = module.networking.public_subnet_id
  network_security_group_id = module.networking.app_nsg_id

  database_endpoint = module.database.endpoint
  cache_endpoint    = module.cache.endpoint

  image_backend  = var.image_backend
  image_frontend = var.image_frontend
}
```

## Variables

See `variables.tf` for complete list.

## Outputs

- `vm_public_ip`: VM public IP address
- `vm_id`: VM resource ID

## TODO

- [ ] Implement Azure VM creation
- [ ] Implement custom data script for Docker Compose deployment
- [ ] Implement Network Security Group rules
- [ ] Add Cloudflare IP allowlist automation
- [ ] Add Managed Disk for Docker volumes
- [ ] Add backup configuration
