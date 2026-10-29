# Delivery visibility — verification

Status: assistant-executed simulation, checked on 29 October 2026. Code and tests ran at commit `e7928f4fb46c33140131f34b5ae313c3a8e9b5dd`. No real customer or independently completed learner investigation is claimed.

## Results

The [PostgreSQL-backed workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40969544632) passed all 56 tests. New cases checked the four bounded queue counts, omission of queue samples on collection failure, secret-safe failure output, future retry exclusion, due pending age and expired lease age. Database tests used actual PostgreSQL; HTTP failure cases included an injected store exception.

The complete [Compose workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40969544730) passed. It validated Prometheus configuration and rule tests for threshold timing, firing, clearing and suppression of the collector alert during a database outage. Its live drills also verified:

1. A dead-delivery gauge and alert after real retry exhaustion, followed by audited replay, actual delivery recovery, zero dead count and alert clearing.
2. Queue-metric availability becoming zero and queue samples disappearing when PostgreSQL stopped, then availability recovering when PostgreSQL restarted.
3. A delivery backlog alert with the worker stopped while API liveness, database readiness and queue-metric availability remained healthy.
4. The original queued order reaching delivered after the worker restarted, due-work age returning to zero and the backlog alert clearing.

Base API, tenant isolation, network diagnostics, persistent partner deduplication, webhook 503/429 recovery and the SQL drill also passed in this run. The [OAuth workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40969544768) passed with the same code.

## Limits

These short thresholds serve a deterministic lab; they are not production service-level objectives. The collection-failure alert was tested with synthetic Prometheus series, not a live database-permission incident. A real outage may involve deployment faults, credentials, lock contention, resource exhaustion, partner errors or several overlapping causes.

Metrics aggregate across tenants. Missing samples are unknown state, not an empty queue; always inspect availability, scrape health, timestamps and the actual delivery record. Alert clearing alone does not prove recovery. No external notification receiver or customer messaging was configured, and no laptop or AWS execution is implied.
