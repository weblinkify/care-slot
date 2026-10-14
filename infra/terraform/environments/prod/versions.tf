terraform {
  required_version = ">= 1.9"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  # Remote state in a locked-down storage account (configured per environment at init:
  # `terraform init -backend-config=backend.hcl`). State can contain secrets - treat it as such.
  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false # never hard-delete keys that decrypt patient data
    }
  }
}
