output "resource_group" {
  description = "Resource group holding the cluster (delete this = delete everything)."
  value       = azurerm_resource_group.dojo.name
}

output "cluster_name" {
  description = "AKS cluster name."
  value       = azurerm_kubernetes_cluster.dojo.name
}

output "get_credentials_command" {
  description = "Merge the cluster into your kubeconfig (the `aws eks update-kubeconfig` of Azure)."
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.dojo.name} --name ${azurerm_kubernetes_cluster.dojo.name}"
}
