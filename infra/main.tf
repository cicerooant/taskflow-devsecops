terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

variable "region" {
  description = "AWS region for TaskFlow resources."
  type        = string
  default     = "us-east-1"
}

variable "bucket_prefix" {
  description = "Globally unique lowercase prefix for the S3 buckets."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$", var.bucket_prefix))
    error_message = "bucket_prefix must be 3-30 lowercase letters, digits, or hyphens, and start and end with a letter or digit."
  }
}

variable "allowed_cidr" {
  description = "One authorized IPv4 address in CIDR /32 form. Never use 0.0.0.0/0."
  type        = string

  validation {
    condition = (
      can(cidrhost(var.allowed_cidr, 0)) &&
      can(cidrnetmask(var.allowed_cidr)) &&
      endswith(var.allowed_cidr, "/32") &&
      var.allowed_cidr != "0.0.0.0/32" &&
      var.allowed_cidr != "0.0.0.0/0"
    )
    error_message = "allowed_cidr must be one valid IPv4 address with /32, not a world-open range."
  }
}

variable "egress_cidrs" {
  description = "Restricted IPv4 destinations allowed for HTTPS egress."
  type        = list(string)
  default     = ["10.0.0.0/24"]

  validation {
    condition = alltrue([
      for cidr in var.egress_cidrs :
      can(cidrhost(cidr, 0)) && can(cidrnetmask(cidr)) && cidr != "0.0.0.0/0"
    ])
    error_message = "egress_cidrs must contain valid restricted CIDRs and cannot include 0.0.0.0/0."
  }
}

data "aws_iam_policy_document" "kms" {
  #checkov:skip=CKV_AWS_109:KMS key policies must name the key resource as *, and the root principal is the AWS account administration principal.
  #checkov:skip=CKV_AWS_111:This statement grants the account root principal key administration so the key remains recoverable; IAM access is still governed by account policies.
  #checkov:skip=CKV_AWS_356:Within a KMS key policy, resources * refers to the key carrying this policy and cannot grant access to other keys.
  statement {
    sid       = "EnableAccountIAMPermissions"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }
}

resource "aws_kms_key" "data" {
  description             = "Encryption key for TaskFlow S3 buckets."
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy                  = data.aws_iam_policy_document.kms.json
}

resource "aws_s3_bucket" "logs" {
  #checkov:skip=CKV_AWS_18:This is the access-log destination bucket; logging it to itself would create recursive log delivery.
  #checkov:skip=CKV_AWS_144:Cross-region replication is outside this single-region lab and would require a second account or region.
  #checkov:skip=CKV2_AWS_62:No event consumer exists in this lab; access logging is enabled for the application data bucket.
  #checkov:skip=CKV_AWS_145:S3 server access log destinations support SSE-S3 only; AWS does not support SSE-KMS for S3 log delivery.
  bucket = "${var.bucket_prefix}-logs"
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-access-logs"
    status = "Enabled"
    filter {}

    expiration {
      days = 365
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket" "data" {
  #checkov:skip=CKV_AWS_144:Cross-region replication is outside this single-region lab and would require a second account or region.
  #checkov:skip=CKV2_AWS_62:No event consumer exists in this lab; S3 access logging is configured separately.
  bucket = "${var.bucket_prefix}-data"
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data.arn
    }
  }
}

resource "aws_s3_bucket_logging" "data" {
  bucket        = aws_s3_bucket.data.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access/"
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

data "aws_iam_policy_document" "logs" {
  statement {
    sid     = "AllowS3ServerAccessLogs"
    effect  = "Allow"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.logs.arn}/s3-access/*"
    ]

    principals {
      type        = "Service"
      identifiers = ["logging.s3.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.data.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs.json
}

resource "aws_security_group" "app" {
  #checkov:skip=CKV2_AWS_5:This module defines the restricted security group only; attaching it requires the application VPC and compute resource, which are outside this lab.
  name        = "${var.bucket_prefix}-app"
  description = "Restrict TaskFlow HTTPS ingress and egress."

  ingress {
    description = "HTTPS from the single authorized IPv4 address."
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    description = "HTTPS only to explicitly permitted destinations."
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.egress_cidrs
  }
}

output "data_bucket" {
  description = "Private, encrypted, versioned bucket used for application data."
  value       = aws_s3_bucket.data.id
}
