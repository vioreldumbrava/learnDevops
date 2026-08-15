variable "region" {
  description = "AWS region."
  type        = string
  default     = "eu-north-1"
}

variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
  default     = "devops-dojo"
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS control plane."
  type        = string
  default     = "1.35"

  validation {
    condition     = var.cluster_version == "1.35"
    error_message = "This capstone is tested against EKS/Kubernetes 1.35."
  }
}

variable "node_instance_type" {
  description = "EC2 instance type for the managed node group."
  type        = string
  default     = "t3.medium"
}

variable "node_desired_size" {
  description = "Desired number of worker nodes."
  type        = number
  default     = 2
}
