# EKS — provision the Kubernetes capstone

This Terraform root creates an Amazon EKS 1.35 cluster, a three-AZ VPC with private
worker nodes, and the IAM role used by AWS Load Balancer Controller through IRSA. It is
the cloud counterpart to the local kind cluster and the foundation for the GitOps
capstone.

> **This costs real money.** EKS, EC2 workers, NAT Gateway, and any ALB created by a
> Gateway are billable. Budget roughly **$5–10/day** for the learning stack and destroy
> it when the session is over.

## Prerequisites

- Terraform 1.10 or newer, `kubectl`, Helm, AWS CLI v2, and PowerShell 7.
- Local AWS authentication through IAM Identity Center (`aws configure sso` followed by
  `aws sso login`). Do not create long-lived access keys for this lab.
- Permission to create EKS, VPC, EC2, ELB, and IAM resources.

GitHub automation uses the OIDC-only workflow in
[../../.github/workflows/aws-terraform-plan.yml](../../.github/workflows/aws-terraform-plan.yml).
It does not accept `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` repository secrets.

## Provision

```powershell
Set-Location deploy/eks
Copy-Item terraform.tfvars.example terraform.tfvars

terraform init
terraform plan -out tfplan
terraform apply tfplan

# Configure kubectl, install pinned Gateway/LBC CRDs, AWS Load Balancer
# Controller v2.14.1 (chart 1.14.0), and the aws-alb GatewayClass.
./bootstrap-gateway.ps1

kubectl get nodes
kubectl get gatewayclass aws-alb
kubectl get deployment aws-load-balancer-controller -n kube-system
```

The bootstrap is repeatable: it uses `helm upgrade --install`, server-side CRD apply,
and the Terraform-created IRSA role. It installs standard Gateway API v1.2.0 and the
LBC-specific Gateway CRDs from the immutable `v2.14.1` tag. `ALBGatewayAPI` is enabled
for the standard `HTTPRoute`/`GRPCRoute` definitions. `NLBGatewayAPI` is explicitly
disabled because its TCP/UDP/TLS routes require the optional experimental Gateway API
CRDs, which this HTTP capstone does not install.

Application `Gateway` resources on EKS must use `gatewayClassName: aws-alb`;
`gateway.k8s.aws/alb` is the controller name. That class references the namespaced
`aws-alb-internet-facing` `LoadBalancerConfiguration`, because LBC otherwise creates an
internal ALB. The configuration also applies `Project=devops-dojo` to the AWS load
balancer resources for cost and teardown queries.

Deploy the app with GitOps using [../gitops/README.md](../gitops/README.md) and the
[capstone lab](../../labs/25-capstone-eks-gitops/).

## Tear down

Delete Kubernetes resources that own AWS load balancers before destroying the VPC:

```powershell
kubectl delete application devops-dojo -n argocd --ignore-not-found
kubectl delete gateway --all --all-namespaces --ignore-not-found
# StatefulSet claims survive workload deletion. After confirming the database
# backup/restore evidence, remove them and wait for their EBS-backed PVs to go.
kubectl -n devops-dojo delete pvc --all --ignore-not-found
kubectl get pv

# Repeat until ResourceTagMappingList is empty, then remove the controller.
aws resourcegroupstaggingapi get-resources --region eu-north-1 `
  --resource-type-filters elasticloadbalancing:loadbalancer `
  --tag-filters Key=Project,Values=devops-dojo
helm uninstall aws-load-balancer-controller -n kube-system

terraform destroy
```

After destroy, verify that no resource tagged `Project=devops-dojo` remains and check
AWS Cost Explorer on the following day. `single_nat_gateway = true` keeps this learning
environment cheaper; a production VPC normally uses one NAT Gateway per availability
zone for high availability.
