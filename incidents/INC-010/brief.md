# INC-010 — S3 object access denied

**Synthetic customer:** “Our integration can list some files, but downloading a report returns AccessDenied.”

**Status:** designed scenario. The Terraform scaffold has passed static validation, but no AWS deployment, AWS API call, customer impact or learner investigation has been verified. The scaffold does not create or attach an IAM principal or create objects, so the scenario requires additional setup in an authorized sandbox.

The planned environment is a disposable S3 bucket with public access blocked and an example IAM policy that allows reads only under `allowed/`. Investigate a request for an object outside that prefix. Confirm the caller identity, exact bucket/key, API action, time, error and request ID before comparing identity and resource policies. Check for explicit denies, permission boundaries, organization policies and any encryption-key permissions relevant to the real environment.

The AWS policy simulator can test the proposed policy, but it does not execute the S3 operation and can differ from live authorization. Avoid granting broad access as a troubleshooting shortcut. A minimal fix must be approved, scoped to the specific requirement and validated with both an authorized object and a denied negative control.

Record actual observations, hypotheses, root cause, resolution, validation and cleanup using [the incident template](../TEMPLATE.md). The [AWS sandbox design](../../docs/aws-s3-design.md) covers costs and prerequisites. No resources should be deployed or deleted without an authorized disposable AWS account and an agreed spending limit.
