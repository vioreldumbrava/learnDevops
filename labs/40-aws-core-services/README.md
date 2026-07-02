# Lab 40 — AWS core services: RDS, S3, IAM/IRSA, VPC

**Maps to:** deepens labs 16/25 · **Milestone:** 4 — Operate & Automate · **Cloud**

> 💸 **Cost:** this lab assumes the lab 25 EKS cluster is up (~$5–10/day) and adds RDS
> `db.t4g.micro` (~$0.40/day) + pennies of S3. Do it in one or two sittings and
> **`terraform destroy` everything after** — the checkpoint includes proving you did.

## Concept

Every JD lists the same four AWS services, and this lab touches each with a real job to do:

- **RDS** — the database leaves the cluster. A managed Postgres brings automated backups,
  point-in-time recovery, patching, and optional multi-AZ failover — the trade-off
  conversation ("what do you gain/lose vs self-hosted in K8s?") is a guaranteed question.
- **S3 + lifecycle** — backups go off-site, and retention becomes *policy on the bucket*
  instead of a cron job someone forgets.
- **IAM + IRSA** — the backup job gets AWS permissions **without any stored keys**: a
  ServiceAccount token exchanged for a role via the cluster's OIDC provider, scoped to one
  bucket. IAM's model (principal → policy → resource + trust policies) is the deepest of the
  four; IRSA is the flavor K8s people are asked about.
- **VPC** — you already *built* one in lab 25 (the EKS module); now you'll *read* it —
  subnets, route tables, the NAT gateway — until the "private subnet" answer is yours.

## What you'll do

Provision RDS/S3/IAM with the [deploy/terraform/rds/](../../deploy/terraform/rds/) root
(which reads the EKS root's outputs via **remote state** — lab 39 pays off immediately),
point the app at RDS, run a nightly S3 backup through IRSA, and tour the VPC.

Prereqs: lab 25 cluster running, lab 39 done **including migrating the EKS root's state to
S3** (this lab reads it from there; also `cd deploy/eks && terraform apply` once to publish
its new outputs).

## Steps

### 1. Provision

```powershell
cd deploy/terraform/rds
terraform init
$env:TF_VAR_db_password = "pick-a-strong-one"
terraform apply -var state_bucket=<your-tfstate-bucket> -var backup_bucket_name=devops-dojo-backups-<yourname>
```

While it builds (~10 min for RDS), read the four files — each is an interview topic:
[main.tf](../../deploy/terraform/rds/main.tf) (remote state consumption),
[rds.tf](../../deploy/terraform/rds/rds.tf) (subnet group, SG-to-SG rule, the
learning-vs-prod flags), [s3.tf](../../deploy/terraform/rds/s3.tf) (lifecycle policy),
[iam.tf](../../deploy/terraform/rds/iam.tf) (permission policy vs **trust** policy).

### 2. Point the app at RDS

The app doesn't know or care where Postgres lives — that's what 12-factor config buys you.
Swap the secret, re-run migrations, restart:

```powershell
$dbUrl = terraform output -raw database_url

kubectl -n devops-dojo delete secret dojo-secrets
kubectl -n devops-dojo create secret generic dojo-secrets `
  --from-literal=POSTGRES_PASSWORD=$env:TF_VAR_db_password `
  --from-literal=DATABASE_URL=$dbUrl

kubectl -n devops-dojo delete job migrate
kubectl apply -f deploy/k8s/base/migrate-job.yaml       # fresh schema + seed on RDS
kubectl -n devops-dojo rollout restart deploy/api deploy/worker
kubectl -n devops-dojo scale statefulset/db --replicas=0  # in-cluster Postgres retires
```

Verify the dashboard still works — it's now reading from RDS. To carry your progress data
over instead of reseeding, this is exactly the
[db-restore runbook](../../docs/runbooks/db-restore.md): dump from `db-0` *before* scaling it
down, restore into RDS through a pod.

### 3. Backups to S3 via IRSA

Edit [deploy/k8s/backup/s3-backup-cronjob.yaml](../../deploy/k8s/backup/s3-backup-cronjob.yaml):
paste `terraform output backup_role_arn` into the ServiceAccount annotation and
`terraform output backup_bucket` into `BACKUP_BUCKET`. Then:

```powershell
kubectl apply -f deploy/k8s/backup/s3-backup-cronjob.yaml
kubectl -n devops-dojo create job --from=cronjob/db-backup-s3 backup-now   # don't wait for 03:00
kubectl -n devops-dojo logs job/backup-now -c upload -f
aws s3 ls s3://devops-dojo-backups-<yourname>/db/
```

No access key was configured anywhere — trace how that worked:
`kubectl -n devops-dojo get sa dojo-backup -o yaml` (the role-arn annotation) and the pod's
injected `AWS_WEB_IDENTITY_TOKEN_FILE` env.

### 4. Read the VPC you already own

For each command, say out loud what you're looking at:

```powershell
aws ec2 describe-subnets --filters "Name=tag:Project,Values=dojo-eks" `
  --query "Subnets[].{cidr:CidrBlock,az:AvailabilityZone,public:MapPublicIpOnLaunch}" --output table

aws ec2 describe-route-tables --filters "Name=tag:Project,Values=dojo-eks" `
  --query "RouteTables[].Routes[].{dest:DestinationCidrBlock,igw:GatewayId,nat:NatGatewayId}" --output table

aws ec2 describe-nat-gateways --filter "Name=tag:Project,Values=dojo-eks" --output table
```

The story to be able to tell: *public subnets route `0.0.0.0/0` to an Internet Gateway (things
in them can be reached); private subnets route it to a NAT Gateway (things in them can reach
out but not be reached). Nodes, RDS, and pods live private; only load balancers live public.*

(If your `Project` tag differs, check `deploy/eks/variables.tf` for the cluster name.)

### 5. Tear down (really)

```powershell
cd deploy/terraform/rds; terraform destroy   # RDS + bucket + role
# and when done with the cluster: cd ../../eks; terraform destroy
```

The backups bucket must be emptied first (`aws s3 rm s3://... --recursive` — versions too if
you added any). Then confirm nothing is left billing: `python scripts/aws_untagged_report.py`
plus a look at the console's billing page.

## How it works

- **Remote state as an interface:** the RDS root never hardcodes VPC/subnet IDs — it reads
  the EKS root's *outputs* from S3. Roots stay small and independently applyable; facts flow
  through outputs, not copy-paste.
- **SG-to-SG rules:** the RDS security group allows 5432 *from the node security group*, not
  from CIDRs. Nodes can be replaced, autoscaled, re-IP'd — the rule still holds. This is the
  cloud-native answer to "how do you firewall a moving target?"
- **IAM's two policies:** the *permission* policy says what the role may do (ListBucket +
  Put/GetObject on one bucket). The *trust* policy says who may **become** the role — here,
  OIDC tokens whose `sub` is exactly `system:serviceaccount:devops-dojo:dojo-backup`. Most
  IAM confusion in interviews is not knowing these are two different documents.
- **Why `sslmode=require`:** traffic now leaves the cluster for RDS; TLS on the DB connection
  stops being optional.
- **Multi-AZ vs read replicas** (follow-up they'll ask): multi-AZ = synchronous standby for
  *failover* (no extra read capacity); read replicas = async copies for *read scaling*.
  Different problems, different features.

## Exercise

1. Wire `backup_rotate.sh`'s S3 idea for real: extend the CronJob (or lab 37's script) to
   also `aws s3 ls` and prune, then compare with what the bucket lifecycle already does —
   when is policy-on-bucket better than logic-in-job?
2. Restore drill, cloud edition: take a backup from S3 and restore it into a *fresh* RDS
   instance (`terraform apply` a second identifier). This is the real DR test — and the
   moment you appreciate `backup_retention_period` and point-in-time recovery.
3. IAM least-privilege proof: from the backup pod's ServiceAccount, try
   `aws s3 ls s3://<some-other-bucket>` and watch `AccessDenied` — then explain exactly which
   policy line made both the allow and the deny happen.

## Checkpoint

- ✅ The dashboard works with `statefulset/db` at 0 replicas — Postgres is fully on RDS.
- ✅ A manually-triggered backup job lands a dump under `s3://…/db/` with **no AWS keys**
  stored in any Secret.
- ✅ You can narrate the public/private subnet + IGW/NAT story from your own route tables.
- ✅ `terraform destroy` completed and the untagged-resource report comes back clean.

## Common failures

- `terraform init` fails reading remote state → the EKS root's state isn't in S3 yet
  (lab 39 exercise 1), or you didn't re-`apply` deploy/eks to publish the new outputs
  (`vpc_id`, `oidc_provider_arn`, …).
- API pods `0/1 Ready` after the swap → readiness can't reach RDS: wrong password in the
  new secret, or you edited the secret but didn't `rollout restart` (env is read at start).
- Backup job `AccessDenied` → role-arn annotation typo'd, or the trust policy's `sub`
  doesn't match `devops-dojo/dojo-backup` exactly (namespace and name both matter).
- `migrate` job connects but fails → RDS enforces SSL; the `database_url` output already has
  `sslmode=require` — make sure you used it verbatim.
- Destroy hangs on the bucket → S3 buckets must be empty (including *versions*) before
  deletion.

➡️ Next: [Lab 41 — Supply-chain security](../41-supply-chain-security/)
