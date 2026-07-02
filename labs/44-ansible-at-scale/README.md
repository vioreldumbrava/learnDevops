# Lab 44 — Ansible at scale: dynamic inventory, roles, Terraform handoff

**Maps to:** deepens labs 16/17/39 · **Milestone:** 5 — Ecosystem breadth · *TWN Bootcamp Module 15* · 💸 runs a `t3.small`

## Concept

Lab 17's Ansible works, but it has three "demo smells" that real teams engineer away:

1. **Static inventory** — you copy-paste an IP from Terraform output into `inventory.ini`.
   With 3 servers that's annoying; with 300 (or autoscaling) it's impossible. A **dynamic
   inventory plugin** asks the cloud API "which instances are mine?" at runtime, grouping by
   **tags** — the same tags Terraform wrote.
2. **Monolithic playbook** — one file that installs Docker *and* deploys the app. **Roles**
   split it into reusable units (`docker` works for any project; `dojo_app` is ours).
3. **Manual handoff** — you run `terraform apply`, wait, then run `ansible-playbook`. Wiring
   them (Terraform triggers Ansible) makes provision-and-configure one motion — and teaches
   *why provisioners are a last resort*, a favorite interview probe.

## What you'll do

Replace the pasted IP with a tag-driven AWS inventory, run the role-based playbook, then let
`terraform apply` do provision **and** configure in one command. Same WSL control node and AWS
account as labs 16/17.

## Steps

### 0. Prereqs (control node, WSL)

```bash
ansible-galaxy collection install amazon.aws
pip install boto3 botocore          # the AWS inventory plugin's SDK
```

Same AWS credentials as Terraform (env vars or `~/.aws`).

### 1. Dynamic inventory — no more pasting IPs

With the lab-16 server up (`terraform apply` in `deploy/terraform` if not):

```bash
cd deploy/ansible
ansible-inventory -i inventory/aws_ec2.yaml --graph
```

Expected shape:

```
@all:
  |--@aws_ec2:
  |  |--51.21.251.231
  |--@dojo:
  |  |--51.21.251.231
  |--@project_devops_dojo:
  |  |--51.21.251.231
```

The instance appears **by tag**, not because you told Ansible about it. Ping it through the
new inventory, then run the play — `hosts: dojo` didn't change, only where "dojo" comes from:

```bash
ansible -i inventory/aws_ec2.yaml dojo -m ping
ansible-playbook -i inventory/aws_ec2.yaml site.yml \
  -e repo_url=https://github.com/<you>/<repo>.git \
  -e postgres_password=$(openssl rand -hex 16)
```

### 2. Read the roles layout

[site.yml](../../deploy/ansible/site.yml) is lab 17's playbook split into
[roles/docker](../../deploy/ansible/roles/docker/tasks/main.yml) (host prep — reusable
anywhere) and [roles/dojo_app](../../deploy/ansible/roles/dojo_app/tasks/main.yml) (our
deployment). Diff `site.yml` + roles against [playbook.yml](../../deploy/ansible/playbook.yml):
same tasks, but defaults moved to
[roles/dojo_app/defaults/main.yml](../../deploy/ansible/roles/dojo_app/defaults/main.yml)
(lowest variable precedence — overridable by everything).

### 3. Terraform → Ansible in one command

```bash
cd ../terraform
terraform destroy    # start clean so you see the full flow (keeps it cheap too)
terraform apply \
  -var run_ansible=true \
  -var repo_url=https://github.com/<you>/<repo>.git \
  -var 'ansible_extra_args=-e postgres_password=<strong-password>'
```

`apply` now ends with the Ansible `PLAY RECAP` and `http://<public_ip>` serves the dashboard
— zero manual steps between "no server" and "app running". Note what happened *between* the
tools: Terraform tagged the instance, waited for SSH, and just ran `ansible-playbook` — which
found the new server **via the tags** (dynamic inventory), not via a passed IP.

When done: `terraform destroy` (💸).

## How it works

- [inventory/aws_ec2.yaml](../../deploy/ansible/inventory/aws_ec2.yaml) is the
  `amazon.aws.aws_ec2` **inventory plugin**: it filters instances by
  `tag:Project = devops-dojo` + `running`, names hosts by public IP, and puts every match in
  group `dojo` (so lab 17's play still targets it). `keyed_groups` shows the general pattern —
  one group per tag value (`project_devops_dojo`), which is how a single account with many
  projects stays navigable.
- [provision.tf](../../deploy/terraform/provision.tf) adds an opt-in `null_resource` with a
  `local-exec` provisioner: poll SSH until the instance answers, then run the playbook. Its
  `triggers` re-run configuration when the instance is replaced. **Why last resort:**
  provisioner results live outside Terraform's state and plan — no drift detection, no
  preview, failure poisons the resource. The production-grade alternatives: two pipeline
  steps (lab 15/24 style), cloud-init/user_data for boot-time config, or baked AMIs (Packer).
- The tag is the contract: Terraform writes `Project = devops-dojo`
  ([main.tf](../../deploy/terraform/main.tf)), Ansible selects on it. Tags quietly became your
  service registry — which is why lab 40's tagging discipline matters.

## Exercise

1. Bring up a **second** instance (copy the `aws_instance` block with a new name, same tags —
   or `terraform apply -var instance_type=t3.micro` a scratch copy in the console with the
   same `Project` tag). Re-run `ansible-inventory --graph`: it appears with no inventory edit.
   Run `site.yml` and watch Ansible configure **both**. Delete the extra instance after (💸).
2. In one sentence each, note where you'd draw the line: what belongs in Terraform
   (`user_data`?), what in Ansible, what in the image (Packer)? There's no single right
   answer — having *an* answer with reasons is the interview signal.

## Checkpoint

- ✅ `ansible-inventory -i inventory/aws_ec2.yaml --graph` lists the instance under `@dojo`
  without any IP in a file.
- ✅ `site.yml` (roles layout) deploys the same stack as lab 17's `playbook.yml`,
  `failed=0`.
- ✅ A clean `terraform apply -var run_ansible=true ...` ends with the app answering on
  `http://<public_ip>`.
- ✅ You can give the two-sentence "why provisioners are a last resort" answer.

## Common failures

- `ansible-inventory` shows nothing → wrong region in `aws_ec2.yaml` (must match
  `deploy/terraform` `var.region`), instance not `running`, or AWS credentials not visible to
  Ansible (`aws sts get-caller-identity` to check).
- `boto3 required for this module` → `pip install boto3 botocore` into the same Python
  Ansible uses (`ansible --version` shows which).
- Handoff hangs at "Waiting for SSH" → security group allows only your IP on 22
  (`allowed_ssh_cidr`) — did your IP change? — or the key path differs from
  `private_key_path`.
- `Failed to import the required Python library` on `keyed_groups`/filters → old `amazon.aws`
  collection; `ansible-galaxy collection install amazon.aws --force` to update.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md)
