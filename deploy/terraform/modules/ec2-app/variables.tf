variable "project_name" {
  description = "Name/prefix for resources — MUST differ per environment (e.g. devops-dojo-dev)."
  type        = string
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

variable "generate_ssh_key" {
  description = "Let Terraform generate the SSH key pair (true) or bring your own public key (false)."
  type        = bool
  default     = true
}

variable "public_key_path" {
  description = "Path to YOUR public key, used only when generate_ssh_key = false."
  type        = string
  default     = ""
}

variable "private_key_path" {
  description = "Where to write the generated private key, relative to the calling root module."
  type        = string
  default     = "dojo-key.pem"
}
