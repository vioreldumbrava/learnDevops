# AWS operational baseline (Part A)

This root adds inexpensive AWS fundamentals around the EC2 host from lab 16 without
requiring EKS or RDS. It discovers exactly one non-terminated EC2 instance tagged
`Project=devops-dojo`, then creates:

- an encrypted, versioned, private S3 bucket for `audit/` exports and `backup/` objects;
- a CloudWatch alarm for consecutive EC2 status-check failures;
- a monthly AWS Budget filtered by the same project tag, with optional email alerts.

Use AWS IAM Identity Center locally; do not create long-lived IAM-user access keys.

```powershell
Set-Location deploy/terraform/aws-baseline
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out tfplan
terraform apply tfplan

# CloudTrail keeps 90 days of management-event history without creating a paid trail.
aws cloudtrail lookup-events --region eu-north-1 --max-results 20

$teardownCheck = terraform output -raw teardown_tag_check_command
terraform destroy
Invoke-Expression $teardownCheck
```

The default `force_destroy_bucket = true` makes the learning teardown remove object
versions as well as the bucket. Set it to `false` anywhere the audit/backup data must
survive infrastructure deletion. Budget notifications require email confirmation from
AWS; an empty `budget_email` still creates the budget without subscribers.

Activate the `Project` cost-allocation tag in AWS Billing before relying on the filtered
budget; tag activation and cost data can take roughly a day to appear.
