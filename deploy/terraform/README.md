# Terraform — provision the DevOps Dojo server

This root creates one Ubuntu EC2 server with a restricted firewall and stable public IP.
Ansible installs Docker and deploys the app in the next lab.

```text
deploy/terraform  ->  deploy/ansible  ->  lab 18 HTTPS
lab 16 server         lab 17 config       public service
```

The EKS capstone is a separate root under [../eks/](../eks/). The inexpensive AWS
operational baseline that follows this server is under [aws-baseline/](aws-baseline/).

## Authenticate without long-lived keys

Install Terraform 1.10+, AWS CLI v2, and configure AWS IAM Identity Center for local
work. Do not create IAM-user access keys just to complete the labs.

```powershell
aws configure sso
aws sso login --profile devops-dojo
$env:AWS_PROFILE = "devops-dojo"
aws sts get-caller-identity
```

GitHub cloud plans use [aws-terraform-plan.yml](../../.github/workflows/aws-terraform-plan.yml)
and short-lived credentials from GitHub OIDC. Configure it once:

1. In AWS IAM, create or reuse the GitHub OIDC provider
   `https://token.actions.githubusercontent.com` with audience `sts.amazonaws.com`.
2. Create a read-only Terraform plan role whose trust policy restricts `sub` to
   `repo:OWNER/REPO:environment:aws-plan` and `aud` to `sts.amazonaws.com`.
3. Create the protected GitHub environment `aws-plan` and set its variable
   `AWS_TERRAFORM_PLAN_ROLE_ARN` to that role ARN.
4. Never add `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` as GitHub secrets.

Use this trust-policy shape, replacing the account, owner, and repository. The
environment-bound `sub` prevents workflows outside `aws-plan` from assuming the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:<OWNER>/<REPO>:environment:aws-plan"
      }
    }
  }]
}
```

The role also needs read access to the configured remote-state S3 object if you enable
the backend. Environment approval plus this tightly scoped, read-only role is the trust
boundary for same-repository pull-request plans; fork pull requests are skipped. Keep
apply permissions in a different, approval-protected role. Remote state with S3 locking
also needs `PutObject`/`DeleteObject` on the state key's `.tflock` object; that is the
only write permission the plan role should receive.

## Configure and create the server

```powershell
Set-Location deploy/terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```

Set `allowed_ssh_cidr` to your public IP plus `/32` (for example,
`203.0.113.4/32`). Retrieve it from <https://checkip.amazonaws.com>. The default region
is `eu-north-1`.

By default Terraform creates an Ed25519 key and stores `dojo-key.pem` in the repository
root. To bring your own key, generate one and update `terraform.tfvars`:

```powershell
ssh-keygen -t ed25519 -f ../../dojo-key.pem
```

```hcl
generate_ssh_key = false
public_key_path  = "../../dojo-key.pem.pub"
```

Provision and inspect the outputs:

```powershell
terraform init
terraform plan -out tfplan
terraform apply tfplan
terraform output
```

Run the printed SSH command from the repository root. On Windows, restrict the private
key if OpenSSH reports that its permissions are too broad:

```powershell
icacls dojo-key.pem /inheritance:r
icacls dojo-key.pem /grant:r "$($env:USERNAME):R"
ssh -i dojo-key.pem ubuntu@<public_ip>
```

Pass `terraform output -raw ansible_inventory_line` to the inventory described in
[../ansible/README.md](../ansible/README.md).

## Tear down and troubleshoot

```powershell
terraform destroy
```

- A `t3.small` and unattached Elastic IP cost money; destroy them after practice.
- Ports 22 (your CIDR), 80, and 443 are exposed. Database and application ports are not.
- State and the generated key are gitignored, but the private key also exists inside
  state. Use the encrypted remote-state root for shared work.
- If AWS authentication fails, run `aws sso login --profile devops-dojo`, restore
  `AWS_PROFILE`, and retry `aws sts get-caller-identity`.
- If SSH times out, refresh `allowed_ssh_cidr`; residential public IPs often change.
- `VPCIdNotSpecified` means the chosen region lacks a default VPC. Create a default VPC
  or extend this learning root with an explicit VPC/subnet.
