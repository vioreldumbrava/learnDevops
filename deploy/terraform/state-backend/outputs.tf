output "bucket_name" {
  description = "Use this in every backend \"s3\" block (see deploy/terraform/backend.tf)."
  value       = aws_s3_bucket.state.id
}
