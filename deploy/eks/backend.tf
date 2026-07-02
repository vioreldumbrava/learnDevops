# Remote state backend for the EKS root (lab 39) — same bucket as the EC2 root,
# DIFFERENT key: every root module gets its own state object so a mistake in one
# can't corrupt the other.
#
# Uncomment after creating the bucket (deploy/terraform/state-backend/), then:
#   terraform init -migrate-state
#
# terraform {
#   backend "s3" {
#     bucket       = "YOUR-STATE-BUCKET"
#     key          = "dojo/eks/terraform.tfstate"
#     region       = "eu-north-1"
#     encrypt      = true
#     use_lockfile = true # native S3 locking (TF >= 1.10)
#   }
# }
