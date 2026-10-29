# Observability profile

The optional Prometheus profile scrapes the lab API every five seconds and evaluates three demo alerts: API unreachable, database unavailable, and more than three server errors in five minutes. The metric endpoint also exposes request counts by bounded route and HTTP status and a database readiness gauge. Counts reset on API restart; the lab does not yet provide latency histograms, distributed traces, durable dashboards or external alert notification.

Start the lab and monitoring profile:

```sh
docker compose --profile observability up -d --build
```

Open http://127.0.0.1:9090 and inspect **Status → Targets** and **Alerts**. Try queries `up{job="relaydesk"}`, `relaydesk_database_ready`, and `sum by (status) (relaydesk_requests_total)`. Scraping the API measures whether Prometheus can reach `/metrics`; it does not establish that customers can use the entire service. A failing readiness gauge calls for correlation with `/ready`, API logs, and database connectivity.

For [INC-013](../incidents/INC-013/brief.md), stop the disposable database with `docker compose stop db`, wait at least 30 seconds plus a scrape interval, inspect the alert, then restore it using `docker compose start db`. Never stop shared or production infrastructure. Use `docker compose --profile observability down` to stop the lab while retaining the database volume. Alert rules are local demonstrations; there is no Alertmanager or email integration.

The alert thresholds are for practice, not service-level objectives. A short outage may clear before the `for` duration, and an absent or unreachable metrics endpoint is a different signal from a database gauge showing zero. The partner and worker currently have structured logs but no dedicated metrics.

The live scrape, database outage alert and recovery were verified in [GitHub Actions](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40957624439). Other alerts and external notifications were not tested by that workflow.
