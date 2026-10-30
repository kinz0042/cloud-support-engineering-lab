# Live S3 access investigation — 30 October 2026

This was an assistant-executed exercise in the owner's AWS account, using AWS Core API calls. It is not a customer outage, independent learner investigation or Terraform deployment.

## Scope and observed results

Region: `eu-north-1` (Stockholm), shown in AWS Settings as the project's configured region. A previous `CreateBucket` request to `us-east-1` failed with an explicit service control policy denial. Creation in Stockholm succeeded without changing organization policies or upgrading the account. This supports a regional restriction as the explanation; the policy itself could not be read, so its complete contents remain unverified.

One uniquely named disposable bucket and a 48-byte synthetic `fixture.txt` object were created through AWS APIs. No customer data, long-lived access keys or compute resources were created.

| Check | Actual result |
| --- | --- |
| CreateBucket in Stockholm | Succeeded |
| PutPublicAccessBlock | All four protections enabled |
| PutBucketEncryption | AES256 configured |
| Baseline HeadObject | Succeeded; ContentLength 48; AES256 |
| Inject object-scoped s3:GetObject deny | PutBucketPolicy succeeded |
| HeadObject after deny | 403 Forbidden |
| Inspect policy | GetBucketPolicy returned the injected statement |
| Remove deny | DeleteBucketPolicy succeeded |
| Recovery HeadObject | Succeeded; ContentLength 48 |
| Public access after recovery | All four protections still enabled |
| Cleanup | Deleted only fixture.txt, then its bucket |
| Verify cleanup | ListBuckets returned zero buckets |

The connector's API call records reported success for these operations except the expected 403. HTTP request IDs and full transport logs were not captured; none are fabricated here. HeadObject validates metadata access using s3:GetObject permission; this exercise did not download or validate the object's body.

## Injected cause and resolution

The temporary policy denied s3:GetObject to all principals for exactly the fixture object. It did not deny bucket-policy administration, deletes or other objects, and did not grant public access. The controlled before/after test, together with reading the injected policy, supports that deny as the cause of this fixture's failure. A generic 403 alone would not identify a cause in an unfamiliar environment.

Removing only the injected bucket policy restored the prior access. The administrator role's other permissions were not changed. No IAM user, role or access key was added. The original Terraform module remains undeployed and its prefix-restricted identity-policy example was not exercised by this test.

## Reproduction and investigation sequence

Use an authorized disposable bucket in the account's allowed region. Establish HeadObject success on a synthetic fixture; set all four public access blocks and AES256 encryption. Add a bucket policy with Effect Deny, Principal *, Action s3:GetObject and Resource equal to that fixture's exact object ARN. Repeat HeadObject and inspect GetBucketPolicy. Remove the injected policy in a finally/cleanup path and repeat HeadObject. Review contents before deleting only the known fixture and bucket. Never apply this fault to a shared bucket.

## Example customer communication

“We reproduced the access failure in an isolated test. An explicit deny on the test object blocked access despite the caller's existing permissions. Removing that deny restored access while public-access protections remained enabled. We verified recovery and removed the temporary resources.”

## Cost and remaining boundaries

The exercise used one tiny S3 object and a small number of requests, then removed storage. Billing can lag; no zero-cost or exact credit-consumption claim has been verified. The overall lab target remains $10 of credit. The existing budget alerts are configured, but email verification/delivery remains unresolved. No plan upgrade or advanced-feature activation was performed.

Live EC2/security-group exercises, cloud application deployment, learner investigations and laptop validation remain outside this result.
