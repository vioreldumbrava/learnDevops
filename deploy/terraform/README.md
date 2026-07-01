# Terraform — provision the DevOps Dojo server (step by step)

This creates one Ubuntu EC2 server with a locked-down firewall and a stable IP. It only
creates the **infrastructure**; installing Docker and deploying the app happens next, with
Ansible.

### Where this fits (the whole journey)

```
[deploy/terraform]  ->  [deploy/ansible]        ->  [lab 18]
 create the server      install Docker + deploy      add a domain + HTTPS
 (this folder, lab 16)  (lab 17)                      (optional)
```

> Not the same as `deploy/eks/`. That's the separate **Kubernetes** path used by the capstone
> (lab 25). This folder is the simple single-server path (labs 16 → 18).

---

## Step 0 — Install the tools & connect AWS (one time)

1. **Install** [Terraform](https://developer.hashicorp.com/terraform/install) (≥ 1.6) and the
   [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
   Check: `terraform version` and `aws --version`.
2. **Get AWS access keys.** In the AWS Console → IAM → Users → your user → *Security
   credentials* → **Create access key** (type: CLI). For learning, the user needs permission to
   manage EC2/VPC (the broad `AdministratorAccess` policy is simplest; tighten later).
3. **Configure the CLI** and confirm it works:
   ```powershell
   aws configure                 # paste Access Key ID + Secret, region (e.g. eu-north-1), json
   aws sts get-caller-identity   # should print your account/user — creds work
   ```

## Step 1 — Configure this deployment

```powershell
cd deploy/terraform
copy terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

- `region` — e.g. `eu-north-1` (match what you'll use).
- `allowed_ssh_cidr` — **your** IP so only you can SSH. Get it from
  <https://checkip.amazonaws.com> and add `/32`, e.g. `203.0.113.4/32`.

## Step 2 — The SSH key (pick one)

**Option A — let Terraform make it (default, nothing to do).**
`terraform apply` generates the key pair and writes the private key to `dojo-key.pem` in the
repo root. Skip to Step 3.

**Option B — create the key yourself.** From the repo root:

```powershell
ssh-keygen -t ed25519 -f dojo-key.pem          # creates dojo-key.pem (+ dojo-key.pem.pub)
```

Then in `terraform.tfvars` set:

```hcl
generate_ssh_key = false
public_key_path  = "../../dojo-key.pem.pub"
```

*(Alternative: create a key pair in the AWS Console → EC2 → Key Pairs and download the `.pem`;
save it as `dojo-key.pem` at the repo root and point `public_key_path` at its public half.)*

Either way the private key is **`dojo-key.pem`**, so every later step (Ansible, SSH) is the same.

## Step 3 — Create the server

```powershell
terraform init      # downloads the providers (first time only)
terraform plan      # preview — nothing is created yet
terraform apply     # type "yes"; ~1 minute
terraform output    # public_ip, ssh_command, ansible_inventory_line, ...
```

## Step 4 — Connect

Run the `ssh_command` from the output, **from the repo root** (where `dojo-key.pem` is):

```powershell
ssh -i dojo-key.pem ubuntu@<public_ip>
```

On Windows, if SSH complains the key is too open, lock its permissions once:

```powershell
icacls dojo-key.pem /inheritance:r
icacls dojo-key.pem /grant:r "$($env:USERNAME):R"
```

## Step 5 — Hand off to Ansible (install + deploy)

Terraform made the box; Ansible configures it. Copy the `ansible_inventory_line` output into
the inventory, then run the playbook — see [../ansible/README.md](../ansible/README.md):

```powershell
terraform output -raw ansible_inventory_line   # -> dojo ansible_host=<ip> ansible_user=ubuntu
```

## Tear down (stop paying)

```powershell
terraform destroy
```

## Cost & safety

- Roughly a few dollars/day for a `t3.small` + EIP while running — **destroy when done**.
- Only ports 22 (you), 80, and 443 are open; database/app ports stay private.
- `terraform.tfstate` and `dojo-key.pem` are gitignored (`*.tfstate`, `*.pem`). When Terraform
  generates the key, the private key is also stored in state — fine for local learning; real
  setups keep keys and state in a managed backend/secret store.

## Troubleshooting

- **`Unable to locate credentials` / `AccessDenied`** → run `aws sts get-caller-identity`; if it
  fails, redo `aws configure`; if it succeeds but apply is denied, the IAM user lacks EC2/VPC
  permissions.
- **SSH times out** → `allowed_ssh_cidr` isn't your current IP (it changes); update it and
  `terraform apply` again.
- **`Permission denied (publickey)`** → you used the wrong key; SSH with `-i dojo-key.pem` and
  user `ubuntu`.
- **`VPCIdNotSpecified` / no default VPC** → this config uses your account's default VPC; if the
  region has none, create one (AWS Console → VPC → *Create default VPC*) or add a `subnet_id`.
