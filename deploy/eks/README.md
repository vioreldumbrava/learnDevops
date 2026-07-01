# EKS — provision a real Kubernetes cluster (capstone)

Provisions a production-shaped **Amazon EKS** cluster (VPC across 3 AZs, private node
subnets, a managed node group) using the well-known community modules. This is the
real-cloud counterpart to the local `kind` cluster from lab 22, and the foundation for the
GitOps capstone (lab 25).

> 💸 **This costs real money.** EKS control plane ≈ $0.10/hr, plus worker nodes and one NAT
> gateway (~$0.045/hr). Budget roughly **$5–10/day** and **always `terraform destroy`** when
> you stop. Don't leave it running overnight by accident.

## Prerequisites

- AWS account with credentials configured — see
  [../terraform/README.md](../terraform/README.md) **Step 0** for installing the AWS CLI,
  creating access keys, `aws configure`, and verifying with `aws sts get-caller-identity`
  (EKS needs broad EKS/EC2/VPC/IAM permissions).
- Terraform ≥ 1.6, `kubectl`, and the `aws` CLI.

## Provision

```powershell
cd deploy/eks
copy terraform.tfvars.example terraform.tfvars

terraform init      # downloads the vpc + eks modules and the AWS provider
terraform apply     # ~15 minutes to build the cluster

# Point kubectl at the new cluster (command is printed as an output):
terraform output -raw configure_kubectl | Invoke-Expression
kubectl get nodes
```

## Next

Deploy the app onto it with GitOps — see [../gitops/README.md](../gitops/README.md) and
[lab 25](../../labs/25-capstone-eks-gitops/).

## Tear down (important!)

```powershell
# Delete anything that created cloud load balancers first (ArgoCD app / services),
# otherwise the VPC destroy can hang on leftover ELBs:
kubectl delete -n devops-dojo ingress --all --ignore-not-found

terraform destroy
```

## Notes

- `single_nat_gateway = true` keeps cost down; production uses one NAT per AZ for HA.
- `enable_cluster_creator_admin_permissions = true` grants your identity cluster-admin so
  `kubectl` works immediately after apply.
- Ingress on EKS needs a controller (ingress-nginx or the AWS Load Balancer Controller); the
  capstone lab installs ingress-nginx, which provisions an AWS NLB.
