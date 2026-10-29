# Observability profile

The optional Prometheus profile scrapes the lab API every five seconds. It evaluates demo alerts for API reachability, database connectivity, server errors, exhausted webhook deliveries, overdue delivery work and queue telemetry failures. Request counters reset on API restart; queue gauges are rebuilt from PostgreSQL. The lab does not yet provide latency histograms, distributed traces, durable dashboards or external alert notification.

Start the lab and monitoring profile:

```sh
docker compose --profile observability up -d --build
```

Open http://127.0.0.1:9090 and inspect **Status → Targets** and **Alerts**. Try queries `up{job="relaydesk"}`, `relaydesk_database_ready`, and `sum by (status) (relaydesk_requests_total)`. Scraping the API measures whether Prometheus can reach `/metrics`; it does not establish that customers can use the entire service. A failing readiness gauge calls for correlation with `/ready`, API logs, and database connectivity.

For [INC-013](../incidents/INC-013/brief.md), stop the disposable database with `docker compose stop db`, wait at least 30 seconds plus a scrape interval, inspect the alert, then restore it using `docker compose start db`. Never stop shared or production infrastructure. Use `docker compose --profile observability down` to stop the lab while retaining the database volume. Alert rules are local demonstrations; there is no Alertmanager or email integration.

The alert thresholds are for practice, not service-level objectives. A short outage may clear before the `for` duration, and an absent or unreachable metrics endpoint is a different signal from a database gauge showing zero. The partner and worker have structured logs; the API aggregates queue metrics from the delivery table rather than scraping these processes directly.

The live scrape, database outage alert and recovery were verified in [GitHub Actions](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40957624439). Other alerts and external notifications were not tested by that workflow.

## Delivery visibility

| Metric | Meaning | Interpretation |
|---|---|---|
| `relaydesk_deliveries{state="pending"}` | Pending rows, including future retry backoff | A count alone does not prove work is overdue |
| `relaydesk_deliveries{state="leased"}` | Work claimed by a worker | It may still be in progress or awaiting lease expiry |
| `relaydesk_deliveries{state="delivered"}` | Completed delivery rows | Sender-side acknowledgement, not proof of a real recipient's business effects |
| `relaydesk_deliveries{state="dead"}` | Exhausted deliveries | Investigate before any replay |
| `relaydesk_oldest_due_delivery_age_seconds` | Age of the oldest pending work eligible now, or an expired lease | Future retries and unexpired leases do not contribute; zero means no currently due work |
| `relaydesk_delivery_metrics_available` | Whether the queue aggregate query succeeded | Zero means queue state is unknown |

Counts have only four fixed state labels. They aggregate across tenants and contain no event IDs, order IDs, tenant keys or customer-supplied labels. Use logs and the tenant-scoped inspection command to investigate a specific order. This deliberately avoids an unbounded number of metric series, but does not provide per-customer alerts.

The aggregate query runs in a read-only transaction with a two-second statement timeout. If it fails, the exporter emits availability zero and omits queue count/age samples; it does not report an empty queue. On an observed database outage, it avoids a second connection attempt for queue collection. Prometheus may show the previous scrape until the next scrape marks omitted samples stale, so check timestamp, availability, database readiness and target reachability together. An alert clearing when telemetry disappears is not evidence that a delivery recovered.

Three delivery rules use short lab thresholds:

- `RelayDeskDeadDeliveries`: a positive dead count for 30 seconds.
- `RelayDeskDeliveryBacklog`: due-work age above 30 seconds continuously for another 30 seconds.
- `RelayDeskDeliveryMetricsUnavailable`: queue collection unavailable for 30 seconds while the database connectivity probe succeeds. During a database outage the database alert handles that condition instead.

For the dead-delivery alert, use [INC-015](../incidents/INC-015/brief.md) and the reviewed replay runbook. For a backlog with a healthy API, use [INC-016](../incidents/INC-016/brief.md). The live checks verify that actual delivery recovers as well as the alert clearing; a disappearing alert alone is insufficient.

This is a direct aggregate over the lab table and adds database work to each scrape. It is not a benchmarked production metrics design. Rule tests and live dead-delivery/backlog alert recovery passed in [Compose CI](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40969544730). See [verification details](../incidents/INC-016/verification.md) for coverage and limits.

