# Azure Terraform Main Configuration
# This is a stub - implement track-specific configurations

terraform {
  required_version = ">= 1.5"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  # Uncomment and configure for remote state
  # backend "azurerm" {
  #   resource_group_name  = "terraform-state-rg"
  #   storage_account_name = "terraformstate"
  #   container_name       = "terraform-state"
  #   key                  = "exam-platform/terraform.tfstate"
  # }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Placeholder - implement track-specific modules
# Example for Track A:
# module "track_a_vm" {
#   source = "./modules/track-a-vm"
#   ...
# }
