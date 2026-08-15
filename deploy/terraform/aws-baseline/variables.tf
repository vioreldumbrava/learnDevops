variable "region" {
  description = "AWS region containing the lab 16 EC2 instance."
  type        = string
  default     = "eu-north-1"
}

variable "project_name" {
  description = "Value of the Project tag shared with the lab 16 EC2 root."
  type        = string
  default     = "devops-dojo"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.project_name))
    error_message = "project_name must be 3-32 lowercase letters, digits, or hyphens."
  }
}

variable "monthly_budget_usd" {
  description = "Monthly project-tagged AWS cost budget in USD."
  type        = number
  default     = 20

  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "monthly_budget_usd must be greater than zero."
  }
}

variable "budget_email" {
  description = "Email for forecast/actual budget alerts. Empty disables notifications."
  type        = string
  default     = ""

  validation {
    condition     = var.budget_email == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_email))
    error_message = "budget_email must be empty or a plausible email address."
  }
}

variable "force_destroy_bucket" {
  description = "Allow terraform destroy to delete all learning-bucket object versions. Keep false for retained data."
  type        = bool
  default     = true
}
