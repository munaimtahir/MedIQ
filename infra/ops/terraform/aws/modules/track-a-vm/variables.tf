# Track A: EC2 + Docker Compose Variables

variable "aws_region" {
  description = "AWS region"
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

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for EC2 instance"
  type        = string
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "database_endpoint" {
  description = "RDS PostgreSQL endpoint"
  type        = string
  sensitive   = true
}

variable "cache_endpoint" {
  description = "ElastiCache Redis endpoint"
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

variable "key_pair_name" {
  description = "EC2 Key Pair name for SSH access"
  type        = string
  default     = null
}
