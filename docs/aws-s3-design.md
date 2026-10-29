# AWS S3 and IAM scenario — design boundary

Status: planned; no AWS account has been connected and no AWS resources have been created or verified. The aim is a disposable, private S3 bucket and two synthetic object prefixes, with an intentionally narrow IAM policy. A customer reports AccessDenied when requesting an object outside the allowed prefix.

Before any deployment, choose a dedicated AWS sandbox, an explicit spending limit and region, set budget alerts, review the plan, and obtain the account owner's authorization. Budget alerts notify but do not enforce a hard spending cap. Do not deploy into a production account or use real customer data. Cost and cleanup depend on region, storage, requests, logs, and any added resources.

Investigation: record the caller identity using STS, exact API action, bucket and object ARN, error time and request ID. Compare identity policies, bucket policy, permissions boundary, organization policies and relevant encryption-key policies. Simulating a policy provides useful evidence but is not a complete reproduction of live AWS authorization. Investigate explicit denies before broadening access. Confirm a minimal allowed action and resource, validate an allowed object and a denied negative control, then remove the sandbox resources.

References:
- https://docs.aws.amazon.com/cli/latest/reference/iam/simulate-custom-policy.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html

No AWS incident is claimed as completed until the deployment, failure, investigation and teardown are actually observed and recorded.
