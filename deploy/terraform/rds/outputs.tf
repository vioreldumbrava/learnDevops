output "rds_endpoint" {
  description = "host:port of the RDS instance (private — reachable from inside the VPC only)."
  value       = aws_db_instance.dojo.endpoint
}

output "database_url" {
  description = "Drop-in DATABASE_URL. db_password validation limits credentials to URI-safe characters."
  value       = "postgres://dojo:${var.db_password}@${aws_db_instance.dojo.endpoint}/dojo?sslmode=require"
  sensitive   = true
}

output "backup_bucket" {
  value = aws_s3_bucket.backups.id
}

output "backup_role_arn" {
  description = "Annotate the dojo-backup ServiceAccount with this (deploy/k8s/backup/s3-backup-cronjob.yaml)."
  value       = aws_iam_role.backup.arn
}
