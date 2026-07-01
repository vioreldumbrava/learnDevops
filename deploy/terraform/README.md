# Terraform — provision the DevOps Dojo server

Creates an Ubuntu 24.04 EC2 instance, a locked-down security group (SSH from your IP;
HTTP/HTTPS public), and a stable Elastic IP. It provisions **infrastructure only** — Ansible
(lab 17) installs Docker and deploys the app. That separation is the point: Terraform =
*what exists*, Ansible = *how it's configured*.

## Prerequisites

1. An AWS account + the AWS CLI configured (`aws configure`) or env credentials.
2. Terraform ≥ 1.6.
3. An EC2 **key pair** registered in AWS. Import it from your existing `devDockerKey.pem`
   (run from the repo root):

   ```powershell
   ssh-keygen -y -f .\devDockerKey.pem > devDockerKey.pub
   aws ec2 import-key-pair --key-name devDockerKey --public-key-material fileb://devDockerKey.pub --region eu-north-1
   ```

## Use

```powershell
cd deploy/terraform
copy terraform.tfvars.example terraform.tfvars   # then edit allowed_ssh_cidr etc.

terraform init
terraform plan
terraform apply

terraform output          # public_ip, ssh_command, ansible_inventory_line
```

Then hand the IP to Ansible (see [../ansible/README.md](../ansible/README.md)) — copy the
`ansible_inventory_line` output straight into the inventory.

## Tear down (stop paying)

```powershell
terraform destroy
```

## Notes

- `allowed_ssh_cidr` should be your IP `/32`, never `0.0.0.0/0`.
- State (`terraform.tfstate`) and `*.tfvars` are gitignored — they can contain sensitive data.
  For teams, use a remote backend (S3 + DynamoDB lock); local state is fine for learning.
- The instance opens only 22/80/443. App and database ports stay private (lab 19).
