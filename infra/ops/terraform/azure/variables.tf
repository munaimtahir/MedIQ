# Azure Terraform Variables

variable "azure_location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment name (staging, prod)"
  type        = string
  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "Environment must be 'staging' or 'prod'."
  }
}

variable "domain" {
  description = "Domain name for the application"
  type        = string
}

variable "image_backend" {
  description = "Backend container image (e.g., ghcr.io/owner/repo-backend:staging)"
  type        = string
}

variable "image_frontend" {
  description = "Frontend container image (e.g., ghcr.io/owner/repo-frontend:staging)"
  type        = string
}

variable "database_sku_name" {
  description = "Azure Database for PostgreSQL SKU"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "cache_sku_name" {
  description = "Azure Cache for Redis SKU"
  type        = string
  default     = "Basic"
}

variable "vnet_address_space" {
  description = "Address space for Virtual Network"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_zone_redundancy" {
  description = "Enable zone redundancy for high availability"
  type        = bool
  default     = true
}

variable "cloudflare_ip_ranges" {
  description = "Cloudflare IP ranges for Network Security Group rules"
  type        = list(string)
  default = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22"
  ]
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "exam-platform"
    ManagedBy   = "terraform"
  }
}
