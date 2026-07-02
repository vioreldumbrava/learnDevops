variable "region" {
  description = "AWS region for the state bucket (same as your infra region)."
  type        = string
  default     = "eu-north-1"
}

variable "bucket_name" {
  description = "Globally-unique S3 bucket name for Terraform state, e.g. devops-dojo-tfstate-<yourname>."
  type        = string
}
