# Lab 40 — AWS core services and day-two operations

**Tier:** core · **Track:** AWS · **Milestone:** cloud

This lab has two independently scheduled parts. Complete **Part A immediately after lab 39**;
it uses the inexpensive EC2 host from lab 16 and does not require Kubernetes. Return for
**Part B after the EKS capstone (lab 25)**.

**Authentication:** use AWS IAM Identity Center/SSO locally and GitHub OIDC in CI. Do not
create IAM-user access keys for either part.

## Part A — IAM, VPC, S3, RDS concepts, operations, and cost

**Cost class:** low, but not zero. Keep the existing lab 16 EC2 instance only if you continue
directly into labs 17/18; otherwise destroy it. Confirm any budget-notification email.

### 1. Establish identity and region

```powershell
aws sso login --profile devops-dojo
$env:AWS_PROFILE = "devops-dojo"
$env:AWS_REGION = "eu-north-1"
aws sts get-caller-identity
aws configure list
```

Identify the principal, its permission boundary, and how it obtained a short-lived session.
IAM has two separate questions: a trust policy controls **who can assume** a role; permission
policies control **what that assumed role can do** to which resources.

### 2. Read the VPC path used by your EC2 host

```powershell
$instanceId = aws ec2 describe-instances `
  --filters "Name=tag:Project,Values=devops-dojo" `
            "Name=instance-state-name,Values=pending,running,stopping,stopped" `
  --query "Reservations[0].Instances[0].InstanceId" --output text

aws ec2 describe-instances --instance-ids $instanceId `
  --query "Reservations[0].Instances[0].{Vpc:VpcId,Subnet:SubnetId,Private:PrivateIpAddress,Public:PublicIpAddress,SGs:SecurityGroups[*].GroupId}" `
  --output json
aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=<subnet-id>" `
  --query "RouteTables[].Routes" --output table
```

Trace the request path: route table → internet/NAT gateway → security group → instance. Say
which controls routing and which controls stateful filtering. In a production design, public
load balancers belong in public subnets; application nodes and databases belong in private
subnets. The lab 16 default-VPC host is intentionally simpler and its production delta must
be explicit.

### 3. Apply the operational baseline

The small Terraform root discovers exactly one live lab 16 instance by its `Project` tag and
adds an encrypted/versioned private S3 bucket, lifecycle policy, EC2 status-check alarm, and
project-tagged monthly budget:

```powershell
Set-Location deploy/terraform/aws-baseline
Copy-Item terraform.tfvars.example terraform.tfvars
# Set budget_email in terraform.tfvars if you want forecast and actual alerts.
terraform init
terraform plan -out tfplan
terraform apply tfplan

$bucket = terraform output -raw operations_bucket
"curriculum integrity $(Get-Date -Format o)" | Set-Content "$env:TEMP\dojo-audit.txt"
aws s3 cp "$env:TEMP\dojo-audit.txt" "s3://$bucket/audit/dojo-audit.txt"
aws s3api get-object-attributes --bucket $bucket --key audit/dojo-audit.txt `
  --object-attributes StorageClass,Checksum,ObjectSize
```

Inspect the S3 public-access block, encryption, versioning, lifecycle, and tags. A bucket
being private today is not a retention strategy; versioning and lifecycle make recovery and
expiry explicit.

### 4. Observe and audit

```powershell
$alarm = terraform output -raw status_alarm_name
aws cloudwatch describe-alarms --alarm-names $alarm `
  --query "MetricAlarms[0].{State:StateValue,Metric:MetricName,Period:Period,Threshold:Threshold}"

aws cloudtrail lookup-events --max-results 20 `
  --query "Events[].{When:EventTime,Who:Username,Action:EventName}" --output table

aws budgets describe-budget --account-id (aws sts get-caller-identity --query Account --output text) `
  --budget-name (terraform output -raw budget_name)
```

CloudWatch answers “what is the system doing?”; CloudTrail management-event history answers
“who changed what?”; the budget answers “what cost boundary did we set?” Cost allocation tags
must be activated in Billing before they appear in cost reports, so verify that separately.

### 5. RDS decision before provisioning it

Draw the production delta for this application: Postgres in private subnets, a DB subnet
group spanning Availability Zones, TLS, security-group access only from the application,
automated backups/PITR, and Secrets Manager rotation. Be able to distinguish:

- Multi-AZ standby: synchronous availability/failover, not read capacity.
- Read replica: asynchronous read scaling, not the primary HA mechanism.
- RPO: acceptable data loss; RTO: acceptable recovery time. Both must be tested.

Do not provision RDS yet. Part B integrates it with the capstone VPC and workload identity.

### Part A checkpoint and teardown

- The caller is an SSO session, not a static access key.
- You can narrate the VPC route and security-group boundary for your real EC2 instance.
- The S3 object is encrypted/versioned, the alarm exists, CloudTrail shows your operation,
  and the budget is filtered by `Project=devops-dojo`.
- You can explain the RDS topology, Multi-AZ/read-replica distinction, and RPO/RTO.

Mark the dashboard's guided completion after this checkpoint so lab 25 sees AWS Part A as
done. Add a note `Part A | date | duration | teardown result`; Part B is the later transfer
task and remains mandatory for the Delivery/cloud learner gate.

```powershell
$teardownCheck = terraform output -raw teardown_tag_check_command
terraform destroy
Invoke-Expression $teardownCheck
Set-Location ../../..
```

The EC2 instance is owned by lab 16, not this root. Continue immediately to labs 17/18 or
destroy it from `deploy/terraform`. After teardown, use Resource Groups Tagging API and the
Billing console to verify no **unexpected** tagged billable resources remain.

---

## Part B — RDS, IRSA, backup/restore, and EKS operations

**Prerequisites:** lab 25 EKS cluster running; lab 39 remote state configured. **Cost class:**
high while EKS/RDS/NAT are alive. Use one focused session and destroy everything afterward.

### 1. Provision the EKS-integrated data layer

```powershell
Set-Location deploy/terraform/rds
terraform init
$env:TF_VAR_db_password = "pick-a-strong-one!42" # 16+ URI-safe characters; see variables.tf
terraform apply `
  -var state_bucket=<your-tfstate-bucket> `
  -var backup_bucket_name=devops-dojo-backups-<yourname>
```

Read `rds.tf`, `s3.tf`, and `iam.tf`. The RDS root consumes EKS outputs through remote state,
places RDS in private subnets, allows port 5432 from the node security group rather than a
broad CIDR, and creates a narrowly scoped IRSA role for one backup bucket.
The learning root defaults `force_destroy_backup_bucket=true`, so versioned test backups do
not block the required teardown. Set it false only when retention is deliberate and you have
a separate empty/delete procedure.

### 2. Move the workload to RDS through desired state

Argo CD owns the chart with self-heal and pruning enabled, so do **not** overwrite its
`dojo-secrets` or scale the StatefulSet by hand: reconciliation would undo the drift, and
the later sync could prune that tracked Secret. Use a distinct, independently owned Secret
for a safe ownership handoff. Create `dojo-rds-secrets`, then change the chart values in
`deploy/gitops/argocd/application.yaml` to `secrets.create: false`,
`secrets.name: dojo-rds-secrets`, and `postgres.enabled: false`; commit and push once.

```powershell
$dbUrl = terraform output -raw database_url
kubectl -n devops-dojo create secret generic dojo-rds-secrets `
  --from-literal=POSTGRES_PASSWORD=$env:TF_VAR_db_password `
  --from-literal=DATABASE_URL=$dbUrl `
  --dry-run=client -o yaml | kubectl apply -f -

# While both databases coexist, make a logical cutover backup and restore it to RDS.
# Keep the original PVC until the later S3 backup + timed restore has also passed.
$cutoverDump = "backups/pre-rds-cutover.sql"
kubectl -n devops-dojo exec db-0 -- pg_dump -U dojo -d dojo `
  --clean --if-exists --no-owner --no-privileges > $cutoverDump
Get-Content -Raw $cutoverDump | kubectl -n devops-dojo exec -i db-0 -- psql $dbUrl

# Compare exact curriculum IDs, not a stale fixed row count.
$expectedIds = (Get-Content -Raw curriculum/manifest.json | ConvertFrom-Json).steps.id |
  Sort-Object
$actualIds = kubectl -n devops-dojo exec db-0 -- psql $dbUrl -Atc `
  "SELECT id FROM steps ORDER BY id;"
$idDiff = Compare-Object $expectedIds ($actualIds | Sort-Object)
if ($idDiff) { $idDiff; throw "RDS restore does not match the curriculum manifest" }

# In deploy/gitops/argocd/application.yaml, keep/create these values:
#   secrets.create: false
#   secrets.name: dojo-rds-secrets
#   postgres.enabled: false
# Retire the old cluster-Postgres ciphertext in the same desired-state change.
git rm --ignore-unmatch deploy/secrets/capstone/sealed-dojo-secrets.yaml
# Argo's Helm post-upgrade hook runs migrations against the new DATABASE_URL.
git add deploy/gitops/argocd/application.yaml
git commit -m "feat: move capstone database to RDS"
git push
kubectl -n argocd get application devops-dojo -w
kubectl -n devops-dojo rollout status deployment/api --timeout=180s
kubectl -n devops-dojo rollout status deployment/worker --timeout=180s
kubectl -n devops-dojo get statefulset db # NotFound is expected after prune
curl.exe --fail http://<gateway-address>/api/steps
```

The cutover preserves learner progress rather than silently reseeding RDS. Keep both the
cutover dump and retained PVC until the S3 backup and timed restore in step 3 pass.

Because `dojo-rds-secrets` never belonged to the Argo Application, pruning its old
`dojo-secrets` cannot delete the new credentials. For the learning run it can be bootstrapped
imperatively. For a durable portfolio deployment, commit an ExternalSecret/SealedSecret
from lab 26 that produces `dojo-rds-secrets`—never a plaintext database URL or password.

### 3. Prove pod identity and timed restore

Set the role ARN and bucket in `deploy/k8s/backup/s3-backup-cronjob.yaml`. Its dump container
already reads the post-cutover `dojo-rds-secrets`; keep that name aligned if you chose a
different external Secret. Then:

```powershell
kubectl apply -f deploy/k8s/backup/s3-backup-cronjob.yaml
kubectl -n devops-dojo create job --from=cronjob/db-backup-s3 backup-now
kubectl -n devops-dojo logs job/backup-now -c upload -f
aws s3 ls "s3://$(terraform output -raw backup_bucket)/db/"
```

No access key is stored in a Secret: a projected ServiceAccount token is exchanged for the
role. Prove least privilege by attempting access to an unrelated bucket and expecting
`AccessDenied`.

Declare an RPO and RTO in your notes, start a timer, restore the newest dump into a fresh
database, and run both row-count/manifest-ID integrity and an API smoke test. Record achieved
RPO/RTO, assistance, and the slowest recovery step.

Only after that proof may you delete the old in-cluster claim. StatefulSet deletion retains
PVCs by design, so wait for its dynamically provisioned PV/EBS volume to disappear:

```powershell
kubectl -n devops-dojo delete pvc data-db-0
kubectl get pv -w # stop when the former data-db-0 PV is gone
```

### 4. Operate EKS, then tear it down

Use the lifecycle procedure in [`deploy/eks/README.md`](../../deploy/eks/README.md): inspect
upgrade insights and deprecated APIs/add-ons, review control-plane/node sequencing, and
observe both pod HPA and node-capacity scaling. Do not perform an unplanned control-plane
upgrade in the same session as the restore drill.

Delete Gateway/LB resources before destroying the VPC:

```powershell
kubectl delete -f deploy/gitops/argocd/application.yaml --ignore-not-found
kubectl -n devops-dojo delete pvc --all --ignore-not-found
kubectl get pv # no capstone-owned Released/Bound PV may remain
Set-Location deploy/terraform/rds
terraform destroy
Set-Location ../../eks
terraform destroy
```

### Part B checkpoint

- The application runs on private RDS with TLS and in-cluster Postgres removed through Git.
- A backup reaches S3 through IRSA, unrelated-bucket access is denied, and no AWS keys exist
  in Kubernetes Secrets.
- A timed restore meets—or honestly records a miss against—the declared RPO/RTO.
- You can explain EKS version/add-on lifecycle and pod-versus-node scaling.
- Tag inventory and the Billing console show no leftover load balancer, NAT gateway, EBS
  volume/snapshot, RDS instance/snapshot, or other tagged billable resource.

➡️ Next: choose the Platform/CKA or SRE branch in
[`docs/CURRICULUM.md`](../../docs/CURRICULUM.md).
