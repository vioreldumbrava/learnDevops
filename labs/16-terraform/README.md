# Lab 16 — Infrastructure as Code: Terraform

**Maps to:** extra (fills a gap in the original path) · **Milestone:** 2

## Concept

**Infrastructure as Code** describes servers, networks, and firewalls in version-controlled
files instead of clicking in a console. **Terraform** reads your desired state, computes a
**plan** (what it will create/change/destroy), and applies it. The result is reproducible,
reviewable, and easy to tear down.

## What you'll do

Provision an Ubuntu EC2 instance, a locked-down security group, and a stable Elastic IP for
DevOps Dojo — infrastructure only (Ansible installs the software in lab 17).

## Steps

Prereqs: an AWS account, `aws configure` done, Terraform ≥ 1.6, and an EC2 key pair imported
from your `devDockerKey` (see [deploy/terraform/README.md](../../deploy/terraform/README.md)).

```powershell
cd deploy/terraform
copy terraform.tfvars.example terraform.tfvars   # edit region, key_name, allowed_ssh_cidr

terraform init       # downloads the AWS provider
terraform plan        # review what will be created (nothing is changed yet)
terraform apply       # type "yes" to create it

terraform output      # public_ip, ssh_command, ansible_inventory_line
```

Connect to confirm it exists (from the repo root):

```powershell
ssh -i .\devDockerKey.pem ubuntu@<public_ip>
```

## How it works

- [main.tf](../../deploy/terraform/main.tf) declares a `data "aws_ami"` lookup (latest Ubuntu
  24.04), an `aws_security_group` (SSH from your IP; 80/443 public; app/db ports closed), an
  `aws_instance`, and an `aws_eip`.
- [variables.tf](../../deploy/terraform/variables.tf) parameterizes region, instance type,
  key name, and your SSH CIDR.
- Terraform records reality in `terraform.tfstate` (gitignored — treat as sensitive).

This is the **IaC vs config-management** split: Terraform decides *what infrastructure
exists*; Ansible (lab 17) decides *how it's configured*.

## Exercise

Run `terraform plan` again after `apply` — it should report "No changes" (your config matches
reality). Then change `instance_type` to `t3.medium` and `plan` again to see Terraform detect
the drift and propose the update. (You don't have to apply it.)

## Checkpoint

- ✅ `terraform apply` completes and `terraform output` shows a public IP.
- ✅ You can SSH into the instance as `ubuntu`.
- ✅ A second `terraform plan` reports no changes.

## Common failures

- `InvalidKeyPair.NotFound` → the `key_name` isn't imported in that region (see the Terraform
  README's import step).
- SSH times out → `allowed_ssh_cidr` isn't your current IP; get it from
  <https://checkip.amazonaws.com> and use `/32`.

**Don't forget** `terraform destroy` when you're done, to stop paying.

➡️ Next: [Lab 17 — Configuration management (Ansible)](../17-ansible/)
