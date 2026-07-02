variable "location" {
  description = "Azure region (the AWS 'region' — westeurope ≈ eu-west, close to eu-north-1)."
  type        = string
  default     = "westeurope"
}

variable "cluster_name" {
  description = "Name/prefix for the cluster and its resource group."
  type        = string
  default     = "dojo-aks"
}

variable "node_count" {
  description = "Nodes in the default pool. 2 is the demo minimum for rolling updates."
  type        = number
  default     = 2
}

variable "node_size" {
  description = "Node VM size. Standard_B2s (2 vCPU / 4 GiB, burstable) is the cheap lab choice."
  type        = string
  default     = "Standard_B2s"
}
