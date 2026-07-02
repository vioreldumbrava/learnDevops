# Lab 47 — the whole AKS footprint: one resource group, one managed cluster.
# Compare with deploy/eks/main.tf: no VPC module, no subnet/NAT wiring, no IAM
# roles — AKS creates its network and drops node VMs/disks/LB into an
# auto-generated "MC_*" resource group next to this one. Azure also doesn't
# charge for the control plane (EKS does). The trade: less to assemble, less
# you control — the EKS root shows every moving part, this one hides them.

# Resource group = the Azure unit of grouping AND deletion. `az group delete`
# (or terraform destroy) removes everything in it — teardown is one motion.
resource "azurerm_resource_group" "dojo" {
  name     = "${var.cluster_name}-rg"
  location = var.location
  tags     = { project = var.cluster_name }
}

resource "azurerm_kubernetes_cluster" "dojo" {
  name                = var.cluster_name
  location            = azurerm_resource_group.dojo.location
  resource_group_name = azurerm_resource_group.dojo.name
  dns_prefix          = var.cluster_name

  default_node_pool {
    name       = "default"
    node_count = var.node_count
    vm_size    = var.node_size
  }

  # Managed identity: what IRSA/aws-auth achieve on EKS (lab 40), one block here.
  identity {
    type = "SystemAssigned"
  }

  tags = { project = var.cluster_name }
}
