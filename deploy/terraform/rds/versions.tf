terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Own state, own key — same pattern as every root (lab 39).
  # backend "s3" {
  #   bucket       = "YOUR-STATE-BUCKET"
  #   key          = "dojo/rds/terraform.tfstate"
  #   region       = "eu-north-1"
  #   encrypt      = true
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.region
}
