# Cloud Support Engineering Lab

**Investigate realistic API, database, integration and Linux failures in a synthetic B2B order service.**

[Architecture](docs/architecture.md) · [Incident catalogue](incidents/README.md) · [Run locally](#run-locally) · [CI workflows](#verification) · [Career roadmap](docs/roadmap.md)

RelayDesk accepts synthetic customer orders, stores them in PostgreSQL and delivers signed webhooks to a mock partner. Its failure scenarios are built for evidence-driven support work: reproduce the complaint, compare hypotheses, inspect logs and metrics, identify a cause, validate recovery and write an appropriate customer update.

> This is an independent simulation built with substantial AI assistance, not employment or production experience. The owner's independent investigations and job readiness remain unassessed.

```mermaid
flowchart TD
  Client["Synthetic customer"] --> API["Order API"]
  API --> DB[("PostgreSQL")]
  Worker["Webhook worker"] --> DB
  Worker --> Partner["Mock partner"]
  Prom["Prometheus, optional"] --> API
```

The API creates the order and delivery record in one transaction. The worker leases and retries deliveries; the partner validates signatures and retains event IDs in a local volume. The optional [OAuth profile](docs/oauth.md) puts a Keycloak-backed JWT gateway in front of the API. A separate [Linux service lab](docs/linux-service-lab.md) exercises systemd without requiring the Docker stack.

## What a reviewer can inspect

| Support problem | Implemented evidence |
| --- | --- |
| Accepted order, missing notification | [Exhausted retries, recipient review and audited replay](incidents/INC-015/verification.md) |
| API healthy while deliveries stop | [Queue telemetry and stopped-worker recovery](incidents/INC-016/verification.md) |
| Slow reads despite healthy readiness | [PostgreSQL lock waits, request timing and alert recovery](incidents/INC-017/verification.md) |
| Invalid or expired credentials | [Keycloak-issued token and JWT failure checks](incidents/oauth-verification.md) |
| Linux service will not start or bind | [Configuration failure](incidents/INC-018/brief.md) and [port conflict](incidents/INC-019/brief.md) |

These are synthetic exercises. CI evidence proves that specified tests ran; it does not prove that the learner independently diagnosed the incidents. Each investigation has a [recording template](incidents/TEMPLATE.md) for actual evidence, competing hypotheses, root cause, validation and communication.

## Run locally

The lightweight foundation needs Python 3.11+ and no third-party packages. From the repository root:

```sh
python -m unittest discover -s tests -v
python app/server.py
```

The full test command skips PostgreSQL- and JWT-dependent tests when their services or packages are unavailable. The local server listens on `127.0.0.1:8080`. In a second terminal:

```sh
curl -i http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/v1/orders
curl -i http://127.0.0.1:8080/v1/orders -H 'Authorization: Bearer lab-demo-token-not-a-secret'
```

The second request deliberately demonstrates a 401; the third uses the public synthetic credential. On Windows, use `py` if needed and `curl.exe` in PowerShell. Stop the server with Ctrl+C. See [Windows setup](docs/windows-setup.md) for the user's platform.

| Profile | Purpose | Requirements |
| --- | --- | --- |
| [Docker application](docs/operations.md) | API, PostgreSQL, worker and signed webhooks | Docker Engine with Compose |
| [Observability](docs/observability.md) | Queue and latency metrics, alerts and recovery | Docker Compose; optional Prometheus profile |
| [OAuth](docs/oauth.md) | Client credentials and JWT failure scenarios | Docker Compose; optional Keycloak profile |
| [Linux services](docs/linux-service-lab.md) | systemd, journal, environment and listening-port investigations | Authorized Linux system with systemd and `sudo` |
| [AWS sandbox design](cloud/aws-s3/README.md) | S3/IAM investigation scaffold | Terraform; real deployment has not been performed |

## Verification

GitHub Actions runs [API tests](https://github.com/kinz0042/cloud-support-engineering-lab/actions/workflows/tests.yml), [PostgreSQL integration](https://github.com/kinz0042/cloud-support-engineering-lab/actions/workflows/integration.yml), [Docker Compose end-to-end](https://github.com/kinz0042/cloud-support-engineering-lab/actions/workflows/compose.yml), [OAuth](https://github.com/kinz0042/cloud-support-engineering-lab/actions/workflows/oauth.yml), [Windows foundation checks](https://github.com/kinz0042/cloud-support-engineering-lab/actions/workflows/windows.yml), [Linux service checks](https://github.com/kinz0042/cloud-support-engineering-lab/actions/workflows/linux-service.yml) and [Terraform static validation](https://github.com/kinz0042/cloud-support-engineering-lab/actions/workflows/terraform.yml). Open individual runs for their exact revision and scope; tests can be skipped when optional dependencies are absent.

The Compose suite uses a disposable database, injects failures and checks recovery. The Linux CI exercise uses uniquely named transient units on a disposable runner. Terraform validation does not deploy or test AWS resources. See the [incident catalogue](incidents/README.md) for completed automated checks and unfinished investigations.

## Project map

- `app/`, `db/`, `compose.yaml`: synthetic API, database, worker and local topology.
- `linux/`: optional loopback status service for systemd investigations.
- `tests/`, `scripts/`, `.github/workflows/`: contract, integration and end-to-end checks.
- `incidents/`: customer reports, briefs, verification evidence and investigation template.
- `docs/`, `monitoring/`, `cloud/`: runbooks, metrics/alerts and undeployed AWS scaffold.

## Boundaries and next steps

Use synthetic data only. Credentials in the repository are public lab values. The services lack production TLS, secret management, production-grade rate limiting and external alert delivery. The Postman collection has not been manually verified; WSL and the full setup have not been verified on the learner's laptop. See [security](docs/security.md).

Learning and hiring readiness require independently performed investigations, written customer communication and interview practice. The [readiness criteria](docs/readiness.md), [practice assessment](docs/support-readiness-assessment.md), and [market evidence](docs/market.md) make those gates explicit. Only personally verified work belongs in a CV or interview story.
