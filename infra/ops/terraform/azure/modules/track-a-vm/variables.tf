# Track A: VM + Docker Compose Variables

variable "azure_location" {
  description = "Azure region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "domain" {
  description = "Domain name"
  type        = string
}

variable "vm_size" {
  description = "VM size"
  type        = string
  default     = "Standard_B2s"
}

variable "vnet_id" {
  description = "Virtual Network ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for VM"
  type        = string
}

variable "network_security_group_id" {
  description = "Network Security Group ID"
  type        = string
}

variable "database_endpoint" {
  description = "Azure Database for PostgreSQL endpoint"
  type        = string
  sensitive   = true
}

variable "cache_endpoint" {
  description = "Azure Cache for Redis endpoint"
  type        = string
  sensitive   = true
}

variable "image_backend" {
  description = "Backend container image"
  type        = string
}

variable "image_frontend" {
  description = "Frontend container image"
  type        = string
}

variable "admin_username" {
  description = "VM admin username"
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
  default     = null
}
