# AWS S3 sandbox

This Terraform module defines a private synthetic S3 bucket with public access blocked, AES256 default encryption, and an example identity policy limited to reading objects in `allowed/`. The policy is an output; it is not attached to anyone. It does not create objects or grant a principal access. The exercise is scaffolding, not evidence of AWS operation or learner experience.

For an account-free starting point, run the [offline object-access exercise](offline-exercise.md). Its HTTP service and permissions are synthetic teaching fixtures, not S3 or an IAM simulator; changing the local fixture does not change the Terraform policy or an AWS account.

Terraform initialization and static validation passed in [GitHub Actions](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40959897772). **The Terraform module has not been deployed. A separate live S3 API exercise has now been executed and cleaned up; see the [live verification record](live-verification.md).** Before any deployment, use a dedicated authorized sandbox, agree on region and spending limit, create budget alerts, review the plan and understand permissions and cleanup. AWS charges may occur, and budget alerts are not hard spending caps. No real data or production account. Bucket names are globally unique; supply your own value. Terraform state may contain infrastructure identifiers; keep it private and never commit it.

Read [the S3/IAM investigation design](../../docs/aws-s3-design.md). Under IAM, a policy decision can also depend on bucket policies, organization controls, permissions boundaries and encryption-key policies. The example policy alone does not prove access in a real account.

Only after an explicit deployment decision: initialize, validate and plan with explicit `aws_region` and `bucket_name`; review all changes before applying. `force_destroy = false` means destroy will fail while objects remain. Carefully remove only synthetic lab objects and versions, then destroy and verify cleanup. Do not perform bulk deletion in an account containing valuable data. IAM simulator output can differ from live authorization and should be checked against the actual environment.

See the [S3 access-denied investigation plan](incident-runbook.md) for evidence, validation and cleanup steps.
