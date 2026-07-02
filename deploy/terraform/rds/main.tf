# Lab 40: managed Postgres (RDS) + S3 backup bucket + IRSA, wired into the EKS
# cluster from lab 25. This root READS the EKS root's outputs through remote
# state — the standard way root modules share facts without merging into one
# giant configuration.

data "terraform_remote_state" "eks" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "dojo/eks/terraform.tfstate" # the EKS root's key (lab 39)
    region = var.region
  }
}

locals {
  vpc_id          = data.terraform_remote_state.eks.outputs.vpc_id
  private_subnets = data.terraform_remote_state.eks.outputs.private_subnets
  node_sg_id      = data.terraform_remote_state.eks.outputs.node_security_group_id
  oidc_arn        = data.terraform_remote_state.eks.outputs.oidc_provider_arn
  # arn:aws:iam::<acct>:oidc-provider/oidc.eks.<region>.amazonaws.com/id/XXX -> the issuer part
  oidc_issuer = element(split("oidc-provider/", local.oidc_arn), 1)

  tags = { Project = var.project_name }
}
