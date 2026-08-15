data "aws_caller_identity" "current" {}

# Part A deliberately discovers the EC2 instance created by lab 16 instead of
# duplicating it or coupling this root to another Terraform state file.
data "aws_instances" "dojo" {
  instance_state_names = ["pending", "running", "stopping", "stopped"]

  filter {
    name   = "tag:Project"
    values = [var.project_name]
  }
}

locals {
  instance_id = length(data.aws_instances.dojo.ids) == 1 ? data.aws_instances.dojo.ids[0] : "invalid-selection"
  bucket_name = "${substr(var.project_name, 0, 24)}-${data.aws_caller_identity.current.account_id}-${var.region}-ops"
}

resource "aws_s3_bucket" "operations" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy_bucket

  tags = {
    Purpose = "audit-and-backup"
  }

}

resource "aws_s3_bucket_ownership_controls" "operations" {
  bucket = aws_s3_bucket.operations.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "operations" {
  bucket = aws_s3_bucket.operations.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "operations" {
  bucket = aws_s3_bucket.operations.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "operations" {
  bucket = aws_s3_bucket.operations.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "operations" {
  bucket = aws_s3_bucket.operations.id
  depends_on = [
    aws_s3_bucket_versioning.operations
  ]

  rule {
    id     = "age-out-learning-artifacts"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 180
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "ec2_status_check" {
  alarm_name          = "${var.project_name}-ec2-status-check"
  alarm_description   = "Lab EC2 instance failed an AWS system or instance status check."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = local.instance_id
  }

  lifecycle {
    precondition {
      condition     = length(data.aws_instances.dojo.ids) == 1
      error_message = "Expected exactly one active lab 16 EC2 instance tagged Project=${var.project_name}."
    }
  }
}

resource "aws_budgets_budget" "project" {
  name         = "${var.project_name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [format("user:Project$%s", var.project_name)]
  }

  dynamic "notification" {
    for_each = var.budget_email == "" ? [] : [var.budget_email]

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = 80
      threshold_type             = "PERCENTAGE"
      notification_type          = "FORECASTED"
      subscriber_email_addresses = [notification.value]
    }
  }

  dynamic "notification" {
    for_each = var.budget_email == "" ? [] : [var.budget_email]

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = 100
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [notification.value]
    }
  }
}
