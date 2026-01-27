# Azure Terraform Outputs

output "load_balancer_ip" {
  description = "Load balancer IP address (for Cloudflare DNS)"
  value       = null # Placeholder - implement in track-specific modules
}

output "database_endpoint" {
  description = "Azure Database for PostgreSQL endpoint"
  value       = null # Placeholder - implement in database module
}

output "cache_endpoint" {
  description = "Azure Cache for Redis endpoint"
  value       = null # Placeholder - implement in cache module
}

output "vnet_id" {
  description = "Virtual Network ID"
  value       = null # Placeholder - implement in networking module
}
