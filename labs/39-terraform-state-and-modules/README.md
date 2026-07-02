# Lab 39 — Terraform: remote state, locking, modules & CI

**Maps to:** deepens lab 16 · **Milestone:** 4 — Operate & Automate · **Platform**

## Concept

Lab 16 left two things a reviewer would flag immediately: **local state** and **no reuse**.

**State** is Terraform's record of what actually exists — resource IDs, attributes, and
sometimes secrets (this project's generated SSH private key lives in state!). On your laptop
it means: no teammate or CI can plan against truth, two applies can race and corrupt it, and
a dead disk loses the mapping to real, still-billing infrastructure. The fix is a **remote
backend** (S3) with **locking** — classically an S3 bucket + DynamoDB lock table (the
interview answer), since Terraform 1.10 just the bucket with `use_lockfile = true`.

**Modules** are Terraform's reuse unit: the server pattern from lab 16 becomes
[modules/ec2-app](../../deploy/terraform/modules/ec2-app/), and each environment under
[envs/](../../deploy/terraform/envs/) is a tiny root module consuming it — own state key,
own sizing, five readable lines of difference.

## What you'll do

Bootstrap a state bucket, migrate lab 16's state into it, watch locking reject a concurrent
run, stand up directory-per-env on the shared module, and let CI enforce
`fmt`/`validate`/`tflint`/`checkov` on every PR.

Prereqs: lab 16 done (AWS credentials configured; ideally its EC2 still applied so you can
migrate real state — works with an empty state too). Terraform ≥ 1.10.

## Steps

### 1. Bootstrap the state bucket (once, with local state)

The bucket that stores state can't store its own state — that's the chicken-and-egg every
team solves with a tiny, apply-once bootstrap:

```powershell
cd deploy/terraform/state-backend
terraform init
terraform apply -var bucket_name=devops-dojo-tfstate-<yourname>   # must be globally unique
```

Read [state-backend/main.tf](../../deploy/terraform/state-backend/main.tf) while it runs:
versioning (state history — your undo button), encryption, public-access block,
`prevent_destroy`, and the commented DynamoDB table that shows the classic locking setup.

### 2. Migrate lab 16's state into the bucket

Uncomment the backend block in [deploy/terraform/backend.tf](../../deploy/terraform/backend.tf),
fill in your bucket name, then:

```powershell
cd deploy/terraform
terraform init -migrate-state     # answer "yes" to copy local -> S3
terraform plan                    # "No changes" — same infra, new home for the truth
aws s3 ls s3://devops-dojo-tfstate-<yourname>/dojo/ec2/
```

The local `terraform.tfstate` is now a leftover — after confirming the S3 copy, delete it.

### 3. See the lock do its job

Two terminals in `deploy/terraform`:

```powershell
# terminal 1 — start an apply and leave it WAITING at the approval prompt
terraform apply

# terminal 2 — try to plan meanwhile
terraform plan
# -> Error: Error acquiring the state lock
```

Answer `no` in terminal 1. That error is the feature: without it, two concurrent applies
interleave writes and corrupt state. Say exactly this in interviews when asked "why remote
state?" — *shared truth + locking*.

### 4. Modules + directory-per-env

```powershell
cd deploy/terraform/envs/dev
terraform init
terraform plan -var allowed_ssh_cidr=<your-ip>/32
```

Read [envs/dev/main.tf](../../deploy/terraform/envs/dev/main.tf) next to
[envs/prod/main.tf](../../deploy/terraform/envs/prod/main.tf): the entire env difference is
the module arguments (`t3.small` vs `t3.medium`, volume size, state key). Applying is
optional (it's a real EC2 bill — `terraform destroy` after, as always). The module itself
([modules/ec2-app](../../deploy/terraform/modules/ec2-app/)) declares *which* providers it
needs but no provider config — roots own regions/credentials, modules stay portable.

### 5. Terraform checks in CI

The `terraform` job added to [.github/workflows/ci.yml](../../.github/workflows/ci.yml) runs
on every PR: `fmt -check` (style), `init -backend=false` + `validate` per root module (broken
references), `tflint` (provider-aware mistakes), `checkov` (insecure patterns, report-only —
same philosophy as the Trivy fs scan). Make it fail once to trust it:

```powershell
# indent something wrong in deploy/terraform/main.tf, then:
terraform fmt -check -recursive -diff deploy/    # this is what CI runs
terraform fmt -recursive deploy/                 # and this fixes it
```

## How it works

- **What's in state:** every resource's real-world ID and attributes — including
  `tls_private_key`'s private key material. That's why the bucket is encrypted, private, and
  versioned, and why state never belongs in Git.
- **One key per root module** (`dojo/ec2/…`, `dojo/eks/…`, `dojo/envs/dev/…`): blast-radius
  isolation. A bad migration or forced unlock in one root can't touch the others.
- **Locking:** the backend takes a lock for the duration of any state-writing operation.
  Classic = DynamoDB conditional writes; modern = S3 conditional `PutObject` (the
  `use_lockfile` lockfile). Know both — most companies still run the DynamoDB setup.
- **Workspaces vs directories (the talk track):** workspaces = one configuration, N states —
  envs can't differ structurally, and it's easy to apply to the wrong one. Directories =
  explicit, diffable, independently plannable roots that share modules. Directories are the
  common production choice; that's what `envs/` implements.
- **Extracting a module from live infra** without destroying anything: `moved` blocks (or
  `terraform state mv`) tell Terraform "resource X is now known as module.Y.X" — the
  Exercise makes you do it for real.

## Exercise

1. Migrate the **EKS** root too: uncomment [deploy/eks/backend.tf](../../deploy/eks/backend.tf)
   (note the different key) and `terraform init -migrate-state`.
2. Refactor `deploy/terraform/main.tf` to consume `modules/ec2-app` **without recreating
   anything**: add the `module` block, delete the old resources, write `moved` blocks
   (`from = aws_instance.dojo`, `to = module.app_server.aws_instance.this`, one per
   resource), and prove it with a `terraform plan` that shows only moves, no
   destroy/create.
3. Give CI a real `terraform plan` on PRs with **GitHub OIDC**: create an IAM role trusting
   `token.actions.githubusercontent.com` for your repo, then use
   `aws-actions/configure-aws-credentials` with `role-to-assume` — no long-lived AWS keys in
   GitHub secrets. (IAM roles get real treatment in lab 40.)

## Checkpoint

- ✅ `terraform plan` in `deploy/terraform` reads state from S3 and shows no changes.
- ✅ A concurrent plan fails with "Error acquiring the state lock" — and you can explain why
  that's good.
- ✅ `envs/dev` and `envs/prod` plan independently against the same module.
- ✅ The CI `terraform` job goes red on an unformatted file and green after `terraform fmt`.
- ✅ You can answer "what is Terraform state, where do you keep it, and how do you stop two
  people applying at once?" in under a minute.

## Common failures

- `BucketAlreadyExists` → S3 names are global; make yours unique (suffix your name).
- `Error acquiring the state lock` with nobody else running → a crashed run left the lock;
  read the error's lock ID and `terraform force-unlock <id>` (only when you're SURE).
- `Backend configuration changed` on init → expected when toggling the backend; follow the
  prompt (`-migrate-state` to move, `-reconfigure` to abandon).
- CI validate fails with "provider requirements" → a new root module is missing its
  `required_providers`; every root and module declares its own.
- `prevent_destroy` blocks your teardown of the state bucket → intended; empty the bucket
  (all versions!) and remove the lifecycle block only when genuinely done with labs 39/40.

➡️ Next: [Lab 40 — AWS core services](../40-aws-core-services/)
