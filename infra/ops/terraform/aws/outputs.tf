# AWS Terraform Outputs

output "load_balancer_dns" {
  description = "Load balancer DNS name (for Cloudflare DNS)"
  value       = null # Placeholder - implement in track-specific modules
}

output "database_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = null # Placeholder - implement in database module
}

output "cache_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = null # Placeholder - implement in cache module
}

output "vpc_id" {
  description = "VPC ID"
  value       = null # Placeholder - implement in networking module
}
