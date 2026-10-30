# Project acceptance: local lab v1

The local, synthetic RelayDesk lab is a complete, reviewable **v1 project**. Its purpose is to provide a reproducible application and support investigations, not to claim production deployment, independent learner experience, or job readiness. This record separates the delivered project from work that depends on an AWS account or the learner's participation.

## Delivered scope

| Capability | Evidence and entry point | Boundary |
| --- | --- | --- |
| Orders and data | [API reference](api.md), tenant-scoped PostgreSQL orders and transactional delivery record | Synthetic data and public lab credentials; no production authorization claim |
| Integrations | [Webhook recovery](../incidents/INC-015/verification.md), retries, signatures, recipient deduplication and replay audit | Mock partner; delivery is at least once, not exactly once |
| API authentication | [OAuth profile](oauth.md), local Keycloak and JWT gateway; API keys in the base profile | Local HTTP, simplified access model, no revocation checks |
| Operations | [Observability](observability.md), logs, metrics, alert rules, SQL and [incident catalogue](../incidents/README.md) | No external alert delivery; investigations are synthetic |
| Linux and network | [Linux services](linux-service-lab.md), [disk](linux-space-lab.md), [networking](networking.md) | Different exercises have different prerequisites and test scopes |
| Cloud design | [S3/IAM scaffold](../cloud/aws-s3/README.md), [network scaffold](../cloud/aws-network/README.md) | Offline/static tests only; AWS resources have not been deployed |
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

## Explicitly outside v1 acceptance

- **Live AWS:** no AWS account, deployment, bill, IAM troubleshooting or teardown has been verified. A real cloud extension requires a user-owned account and an agreed cost boundary.
- **Personal setup:** Docker, WSL, Windows compatibility, desktop Postman, power and connectivity on the learner's own computer remain unverified. Hosted Windows tests do not establish laptop compatibility.
- **Professional evidence:** incidents are simulated; none is represented as a real customer's outage or the learner's independently completed investigation. The learner's explanations, assessments and interview performance have not been measured.
- **Production operation:** no production TLS, secret management, comprehensive egress controls, total request deadlines, high availability, backups or external alerting. Do not expose the lab publicly.
- **Career outcome:** this project is one part of the wider career plan. Job eligibility, current vacancies, application materials, interviews and employment outcomes are not established by passing CI.

These are honest boundaries, not hidden implementation tasks required to run the local v1. Future changes should address an observed defect or a specific need, rather than add incidents to inflate the catalogue.
