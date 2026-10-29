# AWS S3 sandbox (not deployed)

This Terraform module defines a private synthetic S3 bucket with public access blocked, AES256 default encryption, and an example identity policy limited to reading objects in `allowed/`. The policy is an output; it is not attached to anyone. It does not create objects or grant a principal access. The exercise is scaffolding, not evidence of AWS operation or learner experience.

**No AWS resources have been deployed or tested.** Before any deployment, use a dedicated authorized sandbox, agree on region and spending limit, create budget alerts, review the plan and understand permissions and cleanup. AWS charges may occur, and budget alerts are not hard spending caps. No real data or production account. Bucket names are globally unique; supply your own value. Terraform state may contain infrastructure identifiers; keep it private and never commit it.

Read [the S3/IAM investigation design](../../docs/aws-s3-design.md). Under IAM, a policy decision can also depend on bucket policies, organization controls, permissions boundaries and encryption-key policies. The example policy alone does not prove access in a real account.

Only after an explicit deployment decision: initialize, validate and plan with explicit `aws_region` and `bucket_name`; review all changes before applying. `force_destroy = false` means destroy will fail while objects remain. Carefully remove only synthetic lab objects and versions, then destroy and verify cleanup. Do not perform bulk deletion in an account containing valuable data. IAM simulator output can differ from live authorization and should be checked against the actual environment.
