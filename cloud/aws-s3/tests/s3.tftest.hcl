mock_provider "aws" {
  override_during = plan
}

override_resource {
  target          = aws_s3_bucket.lab
  override_during = plan
  values = {
    id  = "relay-synthetic-test-bucket"
    arn = "arn:aws:s3:::relay-synthetic-test-bucket"
  }
}

variables {
  aws_region  = "us-east-1"
  bucket_name = "relay-synthetic-test-bucket"
}

run "private_bucket_configuration" {
  command = plan
  assert {
    condition     = aws_s3_bucket.lab.force_destroy == false
    error_message = "The bucket must not automatically destroy its contents."
  }
  assert {
    condition     = aws_s3_bucket_public_access_block.lab.block_public_acls && aws_s3_bucket_public_access_block.lab.block_public_policy && aws_s3_bucket_public_access_block.lab.ignore_public_acls && aws_s3_bucket_public_access_block.lab.restrict_public_buckets
    error_message = "All four public access blocking settings must be enabled."
  }
  assert {
    condition     = one(one(aws_s3_bucket_server_side_encryption_configuration.lab.rule).apply_server_side_encryption_by_default).sse_algorithm == "AES256"
    error_message = "The synthetic bucket must use SSE-S3 encryption."
  }
}

run "reject_adjacent_periods" {
  command = plan
  variables {
    bucket_name = "invalid..bucket"
  }
  expect_failures = [var.bucket_name]
}

run "reject_ip_address_bucket_name" {
  command = plan
  variables {
    bucket_name = "192.168.1.1"
  }
  expect_failures = [var.bucket_name]
}
