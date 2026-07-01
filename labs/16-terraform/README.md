# Lab 16 — Infrastructure as Code: Terraform

**Maps to:** extra (fills a gap in the original path) · **Milestone:** 2

## Concept

**Infrastructure as Code** describes servers, networks, and firewalls in version-controlled
files instead of clicking in a console. **Terraform** reads your desired state, computes a
**plan** (what it will create/change/destroy), and applies it — reproducible, reviewable, and
easy to tear down.

## The big picture

You're doing the first of three steps: **Terraform creates the server (this lab)** → Ansible
installs Docker + deploys the app (lab 17) → add a domain + HTTPS (lab 18). Terraform decides
*what infrastructure exists*; Ansible decides *how it's configured*.

## What you'll do

Provision an Ubuntu EC2 instance, a locked-down security group, and a stable Elastic IP — plus
an SSH key pair, which Terraform generates for you by default.

## Steps

Full setup (installing tools, AWS credentials) is in
[deploy/terraform/README.md](../../deploy/terraform/README.md) — do **Step 0** there first. Then:

```powershell
cd deploy/terraform
copy terraform.tfvars.example terraform.tfvars
# edit: region + allowed_ssh_cidr (your IP /32 from https://checkip.amazonaws.com)

terraform init      # download providers
terraform plan       # preview (nothing created yet)
terraform apply      # type "yes" to create it
terraform output     # public_ip, ssh_command, ansible_inventory_line
```

**SSH key:** by default Terraform generates it and writes `dojo-key.pem` to the repo root — no
action needed. Prefer to make your own? Run `ssh-keygen -t ed25519 -f dojo-key.pem`, then set
`generate_ssh_key = false` and `public_key_path = "../../dojo-key.pem.pub"` in tfvars (details
in the README).

Connect (from the repo root, where `dojo-key.pem` lives):

```powershell
ssh -i dojo-key.pem ubuntu@<public_ip>
# Windows: if SSH says the key is too open ->
#   icacls dojo-key.pem /inheritance:r
#   icacls dojo-key.pem /grant:r "$($env:USERNAME):R"
```

## How it works

- [main.tf](../../deploy/terraform/main.tf): a `data "aws_ami"` lookup (latest Ubuntu 24.04), an
  `aws_security_group` (SSH from your IP; 80/443 public; app/db ports closed), an
  `aws_instance`, an `aws_eip`, and the key pair (`tls_private_key` + `local_sensitive_file` +
  `aws_key_pair`, gated by `generate_ssh_key`).
- [variables.tf](../../deploy/terraform/variables.tf): region, instance type, your SSH CIDR, and
  the key-pair options.
- Terraform records reality in `terraform.tfstate` (gitignored; treat as sensitive).

## Exercise

Run `terraform plan` again after `apply` — it should report "No changes" (config matches
reality). Then change `instance_type` to `t3.medium` and `plan` again to watch Terraform detect
the drift and propose the update. (You don't have to apply it.)

## Checkpoint

- ✅ `terraform apply` completes and `terraform output` shows a public IP.
- ✅ You can `ssh -i dojo-key.pem ubuntu@<public_ip>` into the box.
- ✅ A second `terraform plan` reports no changes.

## Common failures

- **Credentials/`AccessDenied`** → `aws sts get-caller-identity` should print your identity;
  if not, redo `aws configure` (README Step 0).
- **SSH times out** → `allowed_ssh_cidr` isn't your current IP; update it and re-apply.
- **Windows: key too open** → run the `icacls` commands above.

**Don't forget** `terraform destroy` when you're done, to stop paying.

➡️ Next: [Lab 17 — Configuration management (Ansible)](../17-ansible/)
