terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# Auth comes from the Azure CLI session (`az login`) — the azurerm equivalent
# of the AWS credentials chain the other roots use.
provider "azurerm" {
  features {}
}
