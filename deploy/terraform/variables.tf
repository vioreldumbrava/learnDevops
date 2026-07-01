variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "eu-north-1"
}

variable "project_name" {
  description = "Name/prefix tag for created resources."
  type        = string
  default     = "devops-dojo"
}

variable "instance_type" {
  description = "EC2 instance type. t3.small is the practical minimum for building images on the box."
  type        = string
  default     = "t3.small"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach SSH (22). Restrict to your own IP, e.g. 203.0.113.4/32."
  type        = string
}

variable "root_volume_size" {
  description = "Root EBS volume size in GiB."
  type        = number
  default     = 20
}

# --- SSH key ---
# Default (true): Terraform generates the key pair and writes the private key to
# private_key_path. Set to false to bring your own public key (see public_key_path).
variable "generate_ssh_key" {
  description = "Let Terraform generate the SSH key pair (true) or use your own public key (false)."
  type        = bool
  default     = true
}

variable "public_key_path" {
  description = "Path to YOUR public key, used only when generate_ssh_key = false (e.g. ../../dojo-key.pem.pub)."
  type        = string
  default     = ""
}

variable "private_key_path" {
  description = "Where to write the generated private key (used only when generate_ssh_key = true)."
  type        = string
  default     = "../../dojo-key.pem"
}
