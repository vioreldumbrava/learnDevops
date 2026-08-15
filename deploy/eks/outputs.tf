output "cluster_name" {
  value = module.eks.cluster_name
}

output "region" {
  value = var.region
}

output "configure_kubectl" {
  description = "Run this to point kubectl at the new cluster."
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "Kubernetes control-plane version."
  value       = module.eks.cluster_version
}

output "load_balancer_controller_role_arn" {
  description = "IRSA role used by the aws-load-balancer-controller service account."
  value       = aws_iam_role.load_balancer_controller.arn
}

# Consumed by other root modules via terraform_remote_state (lab 40: RDS + IRSA).
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "private_subnets" {
  value = module.vpc.private_subnets
}

output "node_security_group_id" {
  description = "Security group on the worker nodes — RDS allows Postgres from exactly this."
  value       = module.eks.node_security_group_id
}

output "oidc_provider_arn" {
  description = "IAM OIDC provider for the cluster — the trust anchor for IRSA roles."
  value       = module.eks.oidc_provider_arn
}
