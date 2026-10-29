# S3 access-denied exercise: deployment and investigation plan

**Status: not deployed or tested against AWS.** This plan is not evidence of an AWS incident or hands-on experience.

## Before deployment

Use an explicitly authorized isolated sandbox with synthetic data only. Agree a region and budget, set spending alerts, review identity permissions, and inspect the Terraform plan. Alerts do not cap spending. The existing Terraform scaffold creates a bucket and an example unattached policy; it does not create an identity, attach the policy, upload objects, or guarantee any principal access. Never use this exercise against an account or bucket containing valuable data.

## Customer scenario

A customer reports that their integration receives AccessDenied when retrieving an S3 object. Establish the object key, operation, time, region and caller identity through an approved channel. Do not publish account identifiers, signed URLs, session credentials or object contents.

## Investigation sequence

1. Confirm the actual caller with `aws sts get-caller-identity`. Verify the configured region and the precise bucket and synthetic key.
2. Capture the exact failing operation and sanitized error. Distinguish a nonexistent object from an authorization problem; access controls can prevent distinguishing them from the error alone.
3. Examine relevant identity and bucket policies, explicit denies, organization controls and permission boundaries. For encrypted objects consider KMS key authorization where applicable. The provided scaffold defaults to SSE-S3, not a customer-managed KMS key.
4. Compare the action and resource ARN with the example policy's allowed prefix. Check both bucket-level actions and object-level actions separately; a policy for object reads does not automatically grant listing.
5. Make the smallest approved change in the sandbox, validate the intended read and an out-of-scope denied read, and record the exact policy evidence. An IAM simulation is a useful clue, not proof of live authorization.
6. Record a customer-facing update and internal explanation. Delete only known synthetic objects and versions; review the destroy plan, remove the dedicated lab infrastructure, and independently verify cleanup.

## Evidence required

Collect sanitized caller identity, command outcomes, timestamps, relevant policy statements, before/after results and cleanup confirmation. Mark uncertainties and any assisted steps. No real account deployment or remediation is implied by this design.
