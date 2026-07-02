# prod environment (lab 39): same module as dev, different sizing and state key.
# The env diff is readable in one glance — that's the payoff of module + envs.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # backend "s3" {
  #   bucket       = "YOUR-STATE-BUCKET"
  #   key          = "dojo/envs/prod/terraform.tfstate"
  #   region       = "eu-north-1"
  #   encrypt      = true
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.region
}

module "app_server" {
  source = "../../modules/ec2-app"

  project_name     = "devops-dojo-prod"
  instance_type    = "t3.medium" # prod gets headroom
  root_volume_size = 30
  allowed_ssh_cidr = var.allowed_ssh_cidr
  private_key_path = "dojo-prod-key.pem"
}

variable "region" {
  description = "AWS region."
  type        = string
  default     = "eu-north-1"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH, e.g. 203.0.113.4/32."
  type        = string
}

output "public_ip" {
  value = module.app_server.public_ip
}

output "ssh_command" {
  value = module.app_server.ssh_command
}
