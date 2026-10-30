# Project acceptance: flagship lab v1

The local, synthetic RelayDesk lab is a complete, reviewable **v1 project**. Its purpose is to provide a reproducible application and support investigations, not to claim production deployment, independent learner experience, or job readiness. This record separates the delivered project from optional future engineering and the learner's independent competence assessment.

## Delivered scope

| Capability | Evidence and entry point | Boundary |
| --- | --- | --- |
| Orders and data | [API reference](api.md), tenant-scoped PostgreSQL orders and transactional delivery record | Synthetic data and public lab credentials; no production authorization claim |
| Integrations | [Webhook recovery](../incidents/INC-015/verification.md), retries, signatures, recipient deduplication and replay audit | Mock partner; delivery is at least once, not exactly once |
| API authentication | [OAuth profile](oauth.md), local Keycloak and JWT gateway; API keys in the base profile | Local HTTP, simplified access model, no revocation checks |
| Operations | [Observability](observability.md), logs, metrics, alert rules, SQL and [incident catalogue](../incidents/README.md) | No external alert delivery; investigations are synthetic |
| Linux and network | [Linux services](linux-service-lab.md), [disk](linux-space-lab.md), [networking](networking.md) | Different exercises have different prerequisites and test scopes |
| Cloud design | [S3/IAM scaffold](../cloud/aws-s3/README.md), [network scaffold](../cloud/aws-network/README.md) | Terraform remains undeployed; separate [S3](../cloud/aws-s3/live-verification.md) and [EC2 network](../cloud/aws-network/live-verification.md) API exercises verified and cleaned up |
| User and reviewer entry | [README](../README.md), [Windows guide](windows-first-incident.md), [readiness criteria](readiness.md) | Laptop and independent learner competence not verified |

The architecture diagram in the README and [architecture notes](architecture.md) describe the implemented topology. A frontend is not needed to reproduce or investigate these API-first workflows. Postman collections provide an additional client; desktop import is not verified.

## Verification snapshot

The following GitHub Actions runs executed commit `87cf2725fee7988360053485b906915aa978b2f4` on disposable hosted runners:

| Check | Result | What it establishes |
| --- | --- | --- |
| [API contract](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41033077983) | Passed | Unit and local HTTP tests; optional dependencies may be skipped in this job |
| [PostgreSQL integration](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41033077948) | Passed | Test suite against a PostgreSQL service, including persistence and tenant tests |
| [Windows foundation](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41033077947) | Passed | Selected foundation, pagination, request body, webhook and gateway checks on a hosted Windows runner |
| [Compose end-to-end](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41033078021) | Passed | Stack startup, delivery, fault recovery, SQL, monitoring, replay, lock latency and cleanup checks |
| [OAuth](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41033077986) | Passed | Local Keycloak and gateway end-to-end checks |
| [Postman](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41033077990) | Passed | Automated collection checks using Newman, not the desktop application |

The documentation audit at this snapshot checked relative Markdown paths and heading fragments against the repository tree; it did not validate external URLs or every command on every platform. Automated checks establish only their specific assertions and environment. Open each run to inspect its exact steps; later commits have their own results.

## Verification boundaries

- **Live AWS extension:** separate S3 object-policy and EC2 private-network recovery exercises now have linked evidence above. Both were cleaned up. The core RelayDesk API/database/worker/mock-partner stack has now also run on temporary EC2 with verified teardown; optional OAuth/Prometheus profiles were not deployed there. The Terraform modules remain unapplied, and actual billed credit usage remains unverified.
- **Personal setup:** Docker, WSL, Windows compatibility, desktop Postman, power and connectivity on the learner's own computer remain unverified. Hosted Windows tests do not establish laptop compatibility.
- **Professional evidence:** incidents are simulated; none is represented as a real customer's outage or the learner's independently completed investigation. The learner's explanations, assessments and interview performance have not been measured.
- **Production operation:** no production TLS, secret management, comprehensive egress controls, total request deadlines, high availability, backups or external alerting. Do not expose the lab publicly.
- **Career outcome:** this project is one part of the wider career plan. Job eligibility, current vacancies, application materials, interviews and employment outcomes are not established by passing CI.

These are honest boundaries, not hidden implementation tasks required to run the local v1. Future changes should address an observed defect or a specific need, rather than add incidents to inflate the catalogue.


## AWS extension closeout — 30 October 2026

After the live S3 and EC2 exercises, a further read-only check at approximately 20:10 UTC confirmed:

- ListBuckets returned no S3 buckets.
- Both lab EC2 instances were terminated.
- Stockholm had no EBS volumes, Elastic IP allocations or NAT gateways.
- The prior teardown check confirmed both temporary security groups were deleted, leaving the existing default group.

This scope is the global S3 bucket list and the Stockholm EC2 resource types listed above, not an inventory of every AWS service or region. Existing VPCs and subnets were retained. No paid plan upgrade was performed.

The $10 monthly budget remains configured with credits excluded. Its reported actual spend was $0, but its LastUpdatedTime was still 10:45 UTC, before the experiments. Therefore actual experiment costs and remaining credits are **not yet verified**. Email alert verification/delivery also remains unresolved; resource cleanup did not depend on receiving an alert.

The following workflows all passed for commit `24b9322f86e76fd438bbfb2245a5bc62577487aa`:

- [API contract tests](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41119468603)
- [Terraform static validation](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41119468634)
- [PostgreSQL integration](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41119468623)
- [OAuth end-to-end](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41119468619)
- [Compose end-to-end](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41119468666)

The project now includes local application checks and two separate live AWS exercises with verified teardown. Subsequently, the core RelayDesk stack also passed a [temporary EC2 deployment and CloudWatch batch export](../cloud/aws-relaydesk/verification.md). Applied Terraform, continuous cloud logging/alarms, independent learner investigations and job-readiness assessment remain distinct unfinished capabilities.

## Temporary application deployment extension

The [EC2 run](../cloud/aws-relaydesk/verification.md) executed the existing Compose smoke script from revision `837c5a86a92b5fa23c055eb5a1554737ef138189`, then verified an 11-event sanitized CloudWatch batch export and removed the temporary instance, disks, security group and log group. This is single-host, loopback-only application validation with mock integrations, not a publicly hosted production application or continuous cloud observability.

## Final build review

The flagship v1 build is closed for feature expansion. Existing implementation defects can still be fixed; additional technologies or projects require a concrete evidence gap. See [build completion](build-completion.md) for the handoff and the difference between a completed lab and independently demonstrated competence.
