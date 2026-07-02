# Remote state backend (lab 39). Local state (the default) is fine solo, but breaks
# down the moment a second machine — a teammate or CI — needs to plan: no shared
# truth, no locking, secrets sitting in a local file.
#
# To activate: create the bucket once via ./state-backend/, fill in the name below,
# uncomment, then migrate the existing local state INTO the bucket:
#
#   terraform init -migrate-state
#
# terraform {
#   backend "s3" {
#     bucket       = "YOUR-STATE-BUCKET"          # from state-backend output
#     key          = "dojo/ec2/terraform.tfstate" # one key per root module
#     region       = "eu-north-1"
#     encrypt      = true
#     use_lockfile = true # native S3 locking (TF >= 1.10)
#     # Classic pre-1.10 locking used DynamoDB instead of use_lockfile:
#     # dynamodb_table = "terraform-locks"
#   }
# }
