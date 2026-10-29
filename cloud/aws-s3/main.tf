terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0, < 7.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_partition" "current" {}

resource "aws_s3_bucket" "lab" {
  bucket        = var.bucket_name
  force_destroy = false
  tags = {
    Purpose = "synthetic-support-lab"
  }
}

resource "aws_s3_bucket_public_access_block" "lab" {
  bucket                  = aws_s3_bucket.lab.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lab" {
  bucket = aws_s3_bucket.lab.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# This identity policy is output as JSON for review or simulation only.
# It is deliberately not attached to a user, group, or role.
data "aws_iam_policy_document" "read_allowed_prefix" {
  statement {
    sid       = "ListAllowedPrefix"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.lab.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["allowed/*"]
    }
  }
  statement {
    sid       = "ReadAllowedObjects"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.lab.arn}/allowed/*"]
  }
}

output "bucket_name" {
  value = aws_s3_bucket.lab.id
}

output "example_restricted_identity_policy" {
  value       = data.aws_iam_policy_document.read_allowed_prefix.json
  description = "Review or simulate; this policy is not attached to any principal."
}
