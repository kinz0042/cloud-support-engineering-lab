# INC-013 — Monitoring verification evidence

**Status:** assistant-executed synthetic verification; learner investigation pending. No customer or production system was involved.

[GitHub Actions run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40957624439) built and started the Compose lab and optional Prometheus profile. The monitoring step validated Prometheus configuration and alert-rule tests, then:

1. Observed the API scrape and a database readiness gauge of 1.
2. Stopped the disposable PostgreSQL container.
3. Waited until `RelayDeskDatabaseUnavailable` entered the firing state.
4. Restarted PostgreSQL, observed readiness return to 1 and verified the alert cleared.

The workflow used a synthetic environment and test thresholds. It did not verify any external alert notification, customer impact, latency, traces, or the other alert rules firing in a live outage. The API and worker logs provide additional context. Follow the [brief](brief.md) and [incident template](../TEMPLATE.md) for a complete independent investigation.
