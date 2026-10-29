# INC-013 — Monitoring verification evidence

**Status:** assistant-executed synthetic verification; learner investigation pending. No customer or production system was involved.

[GitHub Actions run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40957624439) built and started the Compose lab and optional Prometheus profile. The monitoring step validated Prometheus configuration and alert-rule tests, then:

1. Observed the API scrape and a database readiness gauge of 1.
2. Stopped the disposable PostgreSQL container.
3. Waited until `RelayDeskDatabaseUnavailable` entered the firing state.
4. Restarted PostgreSQL, observed readiness return to 1 and verified the alert cleared.

The workflow used a synthetic environment and test thresholds. It did not verify any external alert notification, customer impact, latency, traces, or the other alert rules firing in a live outage. The API and worker logs provide additional context. Follow the [brief](brief.md) and [incident template](../TEMPLATE.md) for a complete independent investigation.

## Support record

**Customer complaint:** fictional report in [the incident brief](brief.md). There was no actual customer.

**Severity:** not assigned; real severity depends on scope, duration and customer impact. The automated test did not measure either.

**Reproduction:** the CI script stopped the disposable database service. The API metrics and alert were observed via Prometheus, then the database was restarted. The exact commands and waits are in `scripts/monitoring_smoke.py`.

**Investigation and hypotheses:** an unreachable metrics endpoint, a failed database, and a monitoring configuration error are different possibilities. The test first established that the metrics target was up and the database gauge was 1. It then stopped the database and observed the database-specific alert. Those observations support the injected database outage as the cause in this synthetic case; they do not rule out unrelated causes in a real incident.

**Resolution and validation:** restarting the database restored the readiness gauge to 1 and the firing alert cleared. This check validates the monitoring and recovery path; it does not prove that every queued webhook was delivered during an outage.

**Prevention:** production teams should investigate the reason a real database stopped, define an appropriate alert threshold and recovery owner, and test notification delivery and resilience. This lab alert has no external receiver.

**Example initial customer response:** “We’re investigating the order failures and checking service availability. We’ll share another update when we have more information.”

**Example resolution response:** “The service is responding again in our test environment. We are checking queued deliveries before confirming that all notifications have recovered.”

**Engineering note:** Preserve the request ID and UTC timestamps, correlate the readiness signal with connection errors and deployment changes, and verify the queue after recovery. No real customer message was sent.
