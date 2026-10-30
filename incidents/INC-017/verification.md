# Order latency and PostgreSQL lock — CI verification

Status: assistant-executed synthetic lab. No customer incident or independently completed learner investigation is claimed. The code and tests ran at commit `167d23737eebc70937c8dfa9b57985bfacdd1ceb`.

## Observed checks

The [PostgreSQL-backed workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40971064030) passed all 62 tests. Its lock-wait test held an actual conflicting table lock, verified that API liveness and database readiness stayed healthy, observed the order-list read return a correlated 503 cancellation after the configured statement limit, then confirmed the read succeeded after the lock was released. Other tests cover histogram bucket boundaries, bounded route labels and the duration in the JSON request log.

The complete [Compose workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40971064055) passed, including Prometheus configuration and rule tests and the live `Verify lock-induced API latency and recovery` step. In that step:

1. The API was recreated for an isolated counter baseline; the disposable database and partner history were retained.
2. Three short PostgreSQL lock transactions were applied. For each burst, the test observed four blocked sessions and made four concurrent order-list reads. The CI log records 12 HTTP 200 responses with request IDs.
3. The order-latency alert fired. The test confirmed the lock-holder sessions had exited, sent healthy reads, then observed the rolling-window alert clear.
4. Existing delivery recovery, database alert, stopped-worker backlog, SQL and network checks also passed in the same full-stack run.

The [OAuth end-to-end workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40971064042) also passed with this code.

## Limits

The live Compose burst observed slow successful responses; the separate PostgreSQL integration test verified cancellation under a longer-held lock. The CI script does not record individual client duration measurements in its output, so no numerical speedup or customer-facing latency is claimed. Alert thresholds and synthetic traffic are for practice, not an SLO or a load benchmark. Application processing duration excludes DNS, connection setup, response transfer and asynchronous webhook delivery. SQLSTATE `57014` denotes cancellation; production investigations need evidence before deciding whether a timeout, an operator action or another cause triggered it.

These results do not establish AWS deployment experience or laptop compatibility. The incident should be completed independently using the [investigation template](../TEMPLATE.md) before being presented as personal troubleshooting work.
