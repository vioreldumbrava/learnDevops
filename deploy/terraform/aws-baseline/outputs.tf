output "observed_instance_id" {
  description = "Lab 16 EC2 instance discovered through its Project tag."
  value       = local.instance_id
}

output "operations_bucket" {
  description = "Encrypted, versioned bucket for audit exports and backups."
  value       = aws_s3_bucket.operations.id
}

output "status_alarm_name" {
  description = "CloudWatch EC2 status-check alarm."
  value       = aws_cloudwatch_metric_alarm.ec2_status_check.alarm_name
}

output "budget_name" {
  description = "Project-tagged monthly AWS budget."
  value       = aws_budgets_budget.project.name
}

output "cloudtrail_lookup_command" {
  description = "Read recent management events from the built-in CloudTrail event history."
  value       = "aws cloudtrail lookup-events --region ${var.region} --max-results 20"
}

output "teardown_tag_check_command" {
  description = "Resource Groups query used after destroy to find leftover tagged resources."
  value       = "aws resourcegroupstaggingapi get-resources --region ${var.region} --tag-filters Key=Project,Values=${var.project_name}"
}
