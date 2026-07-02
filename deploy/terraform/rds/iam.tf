# IRSA (IAM Roles for Service Accounts): a Kubernetes ServiceAccount exchanges its
# projected token for AWS credentials via the cluster's OIDC provider. No access
# keys in Secrets, credentials auto-rotate, and the policy is least-privilege.
# This role lets ONE ServiceAccount (devops-dojo/dojo-backup) write to ONE bucket.

data "aws_iam_policy_document" "backup_writer" {
  statement {
    sid       = "ListBackupBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.backups.arn]
  }
  statement {
    sid       = "ReadWriteBackupObjects"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.backups.arn}/*"]
  }
}

resource "aws_iam_policy" "backup_writer" {
  name   = "${var.project_name}-backup-writer"
  policy = data.aws_iam_policy_document.backup_writer.json
  tags   = local.tags
}

# Trust policy: only tokens issued by THIS cluster, for THIS ServiceAccount,
# may assume the role. This is the line to be able to explain in interviews.
data "aws_iam_policy_document" "backup_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:sub"
      values   = ["system:serviceaccount:devops-dojo:dojo-backup"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "${var.project_name}-backup"
  assume_role_policy = data.aws_iam_policy_document.backup_trust.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = aws_iam_policy.backup_writer.arn
}
