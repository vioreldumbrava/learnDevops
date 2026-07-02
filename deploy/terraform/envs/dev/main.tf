# dev environment (lab 39): directory-per-env. Each env is its own ROOT module —
# own state, own backend key, own variables — consuming the shared ec2-app module.
# Compare with workspaces (one config, N states): directories keep envs explicit,
# diffable, and independently plannable, which is why most teams prefer them.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state per env — same bucket, unique key (see ../../backend.tf for setup):
  # backend "s3" {
  #   bucket       = "YOUR-STATE-BUCKET"
  #   key          = "dojo/envs/dev/terraform.tfstate"
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

  project_name     = "devops-dojo-dev"
  instance_type    = "t3.small" # dev stays cheap
  allowed_ssh_cidr = var.allowed_ssh_cidr
  private_key_path = "dojo-dev-key.pem"
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
