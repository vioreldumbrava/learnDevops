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

variable "key_name" {
  description = "Name of an EXISTING EC2 key pair to attach (import it from devDockerKey first — see README)."
  type        = string
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
