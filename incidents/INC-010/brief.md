# INC-010 — S3 object access denied

**Synthetic customer:** “Our integration can list some files, but downloading a report returns AccessDenied.”

**Status:** a local toy object-access scenario is implemented; no AWS deployment, AWS API call, customer impact or learner investigation has been verified. The separate Terraform scaffold does not create or attach an IAM principal or create objects, so a real scenario requires additional setup in an authorized sandbox.

## Local reproduction

The [offline exercise](../../cloud/aws-s3/offline-exercise.md) starts a synthetic loopback service with a missing toy allow for one report. It compares a successful list and reference read against a denied report, then switches to a recovered local fixture and repeats positive and negative controls. Record the generated request IDs and log evidence. These are not AWS APIs, policies, credentials, or CloudTrail events.

For the supplied toy fixture, the report is denied because it is outside its allowed prefixes and exact-key list. The recovered fixture adds the report key while unrelated and private objects remain denied. This is a controlled explanation for the toy fixture, not a conclusion about a real S3 error.

The local toy checks passed in the [PostgreSQL-backed CI suite](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41024286687); live AWS and learner validation remain pending.

## Real AWS investigation design

The planned environment is a disposable S3 bucket with public access blocked and an example IAM policy that allows reads only under `allowed/`. Investigate a request for an object outside that prefix. Confirm the caller identity, exact bucket/key, API action, time, error and request ID before comparing identity and resource policies. Check for explicit denies, permission boundaries, organization policies and any encryption-key permissions relevant to the real environment.

The AWS policy simulator can test the proposed policy, but it does not execute the S3 operation and can differ from live authorization. Avoid granting broad access as a troubleshooting shortcut. A minimal fix must be approved, scoped to the specific requirement and validated with both an authorized object and a denied negative control.

Record actual observations, hypotheses, root cause, resolution, validation and cleanup using [the incident template](../TEMPLATE.md). The [AWS sandbox design](../../docs/aws-s3-design.md) covers costs and prerequisites. No resources should be deployed or deleted without an authorized disposable AWS account and an agreed spending limit.
