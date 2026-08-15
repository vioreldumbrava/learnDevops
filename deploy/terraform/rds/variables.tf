variable "region" {
  description = "AWS region — must match the EKS cluster's."
  type        = string
  default     = "eu-north-1"
}

variable "project_name" {
  description = "Name/prefix tag for created resources."
  type        = string
  default     = "devops-dojo"
}

variable "state_bucket" {
  description = "The Terraform state bucket (lab 39) — used to read the EKS root's outputs."
  type        = string
}

variable "db_password" {
  description = "Master password for the RDS instance. Pass via TF_VAR_db_password or a tfvars file kept out of Git."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 16 && can(regex("^[A-Za-z0-9!$&'()*+,;=_~-]+$", var.db_password))
    error_message = "Use at least 16 URI-safe characters: letters, digits, and !$&'()*+,;=_~-. Do not use : / ? # @ or %."
  }
}

variable "backup_bucket_name" {
  description = "Globally-unique S3 bucket name for database backups, e.g. devops-dojo-backups-<yourname>."
  type        = string
}

variable "force_destroy_backup_bucket" {
  description = "Delete versioned backup objects during terraform destroy. Keep true for the time-boxed learning environment."
  type        = bool
  default     = true
}
