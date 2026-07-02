# Bootstrap for remote Terraform state (lab 39).
#
# Chicken-and-egg: the S3 bucket that stores state can't itself be created with
# remote state — so this tiny root module uses LOCAL state, is applied exactly
# once, and is rarely touched again. Everything else (deploy/terraform, deploy/eks,
# deploy/terraform/envs/*) then points its backend at the bucket created here.
#
#   cd deploy/terraform/state-backend
#   terraform init && terraform apply -var bucket_name=<globally-unique-name>

resource "aws_s3_bucket" "state" {
  bucket = var.bucket_name

  # State is the crown jewels (it can contain secrets and is your record of what
  # exists). Never let a stray `destroy` take it out.
  lifecycle {
    prevent_destroy = true
  }

  tags = { Project = "devops-dojo" }
}

# Versioning = state history. A corrupted/mangled state can be rolled back to a
# previous version — this has saved more teams than any other single setting.
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Locking: with Terraform >= 1.10 the backend locks via S3 itself
# (`use_lockfile = true` in the backend block) — no extra infrastructure.
# The CLASSIC setup interviewers ask about used a DynamoDB table instead;
# uncomment to build that variant and set `dynamodb_table` in the backend:
#
# resource "aws_dynamodb_table" "locks" {
#   name         = "terraform-locks"
#   billing_mode = "PAY_PER_REQUEST"
#   hash_key     = "LockID"
#   attribute {
#     name = "LockID"
#     type = "S"
#   }
#   tags = { Project = "devops-dojo" }
# }
