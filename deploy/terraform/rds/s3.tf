# Off-site home for the pg_dump backups (labs 07/37) with a LIFECYCLE policy:
# recent backups stay hot, older ones get cheaper, ancient ones disappear —
# retention as code instead of a cron job someone forgets.

resource "aws_s3_bucket" "backups" {
  bucket        = var.backup_bucket_name
  force_destroy = var.force_destroy_backup_bucket
  tags          = local.tags
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "age-out-backups"
    status = "Enabled"

    filter {
      prefix = "db/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA" # cheaper storage once restore urgency fades
    }

    expiration {
      days = 180
    }

    # versioning + lifecycle: clean up overwritten/deleted versions too
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
