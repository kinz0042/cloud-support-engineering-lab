# Cloud Support Engineering Lab

**Evidence-driven troubleshooting for a simulated B2B order-integration service.**

Status: Python foundation and Docker/PostgreSQL integration profile. Real PostgreSQL integration and Docker Compose startup, delivery, callback deduplication and database recovery pass GitHub Actions.
This is an independent lab, not employment or production experience. No learner incidents are certified complete.

[Start here](docs/start-here.md) · [Windows setup](docs/windows-setup.md) · [Architecture](docs/architecture.md) · [Incident catalogue](incidents/README.md) · [Support playbook](docs/support-playbook.md) · [API and Postman](docs/api.md) · [OAuth lab](docs/oauth.md) · [AWS sandbox](cloud/aws-s3/README.md) · [Operations](docs/operations.md) · [Observability](docs/observability.md) · [Networking](docs/networking.md) · [Roadmap](docs/roadmap.md) · [Market evidence](docs/market.md) · [Readiness](docs/readiness.md) · [Practice assessment](docs/support-readiness-assessment.md)

## What a reviewer can verify today

- A local HTTP service with a health endpoint, protected order endpoint, safe structured request logs and correlation IDs.
- A reproducible customer authentication failure and contract tests for success and error paths.
- A consistent investigation template separating observations, hypotheses and conclusions.
- Explicit distinction between implemented capabilities and future work.
- A Docker profile with synthetic tenants, PostgreSQL, a worker and signed webhooks. An optional Prometheus profile adds readiness monitoring and alert rules. PostgreSQL and full Compose smoke checks have passed on GitHub Actions.

## Run the foundation

Python 3.11+; no external packages. Run from the repository root:

```sh
python -m unittest discover -s tests -v
python app/server.py
```

Windows may require `py` in place of `python`. In a second terminal:

```sh
curl -i http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/v1/orders
```

PowerShell users should use `curl.exe`. Follow [INC-001](incidents/INC-001/brief.md) and [INC-002](incidents/INC-002/brief.md); record your own evidence before inspecting implementation. The [Docker profile](docs/operations.md) runs separately on port 8081.
Stop the server with Ctrl+C. The server binds only to localhost.

## Project structure

- `app/`: implemented foundation service
- `tests/`: real HTTP contract and log-redaction tests
- `incidents/`: briefs, catalogue and investigation template
- `docs/`: architecture, learning gates, market evidence and security
- `db/`, `compose.yaml`: PostgreSQL schema and local service topology
- `docs/operations.md`: Docker setup and failure drills
- `.github/workflows/`: API, PostgreSQL, Compose, OAuth and Terraform checks

## Skills demonstrated by the foundation

HTTP status/headers, bearer authentication, JSON, Python, log correlation, reproduction and regression tests.
Learner competence remains unassessed until independently demonstrated.

## Working method

Customer report → scope impact → reproduce → collect evidence → inspect logs/metrics → rank hypotheses → test → establish root cause → fix or escalate → validate → prevent recurrence → document → update customer.

Every investigation records expected versus actual behavior, timestamps, request IDs, unsuccessful hypotheses, rollback and customer impact. A successful request alone does not establish the cause of a failure.

## Scope and safety

Synthetic customers and orders only. The demonstration credentials are public and local-only. This is not production software: no production TLS, rate limiting or secret management. OAuth/JWT is available in a separate local demonstration profile. The foundation on port 8080 remains static; the Docker profile on 8081 uses PostgreSQL. See [security](docs/security.md). Never expose it publicly.

## Attribution

Initial scaffold and tests were AI-assisted. Learner investigations must identify hints used and evidence personally collected. Only verified work may be described in a CV.
