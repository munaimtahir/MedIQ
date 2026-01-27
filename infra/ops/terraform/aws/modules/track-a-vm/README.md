# Track A: EC2 + Docker Compose Module

Terraform module for deploying Exam Prep Platform on EC2 with Docker Compose.

## Usage

```hcl
module "track_a_vm" {
  source = "./modules/track-a-vm"

  aws_region  = var.aws_region
  environment = var.environment
  domain      = var.domain

  instance_type = "t3.medium"
  
  vpc_id              = module.networking.vpc_id
  subnet_id           = module.networking.public_subnet_id
  security_group_ids  = [module.networking.app_security_group_id]

  database_endpoint = module.database.endpoint
  cache_endpoint    = module.cache.endpoint

  image_backend  = var.image_backend
  image_frontend = var.image_frontend
}
```

## Variables

See `variables.tf` for complete list.

## Outputs

- `instance_public_ip`: EC2 instance public IP
- `instance_id`: EC2 instance ID

## TODO

- [ ] Implement EC2 instance creation
- [ ] Implement user data script for Docker Compose deployment
- [ ] Implement security group rules
- [ ] Add Cloudflare IP allowlist automation
- [ ] Add EBS volume for Docker volumes
- [ ] Add backup configuration
