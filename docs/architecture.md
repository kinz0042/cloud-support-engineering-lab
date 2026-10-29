# Architecture and delivery boundaries

## Implemented foundation

A customer client calls a loopback HTTP server. `/health` checks liveness; `/ready` checks the synthetic order dependency. `/v1/orders` checks a bearer credential and reads synthetic data through an order store interface. When the store is unavailable, the authorized request returns a generic 500 and the server records a reason with the same request ID. Each GET receives a generated correlation ID, returned to the client and recorded in structured logs. The foundation uses static storage; the separate Docker profile below uses PostgreSQL.

## RelayDesk Docker profile (database integration and Compose smoke verified in CI)

A simulated B2B order integration service. Two synthetic tenants submit orders with separate demonstration keys. The API stores each order and one outbox delivery in the same PostgreSQL transaction. A worker leases due deliveries with `FOR UPDATE SKIP LOCKED`, signs a JSON payload, retries failures with capped backoff and marks exhausted attempts dead. The mock partner checks signatures and recognizes repeated event IDs. The API accepts signed callbacks and stores unique event IDs. Local HTTP tests cover tenant isolation, failure paths and signatures. GitHub Actions verifies real PostgreSQL operations. The full Compose smoke test has passed in GitHub Actions.

```mermaid
flowchart TD
  Client[Customer client] --> API[RelayDesk API]
  API --> DB[(PostgreSQL)]
  Worker[Delivery worker] --> DB
  Worker --> Partner[Mock partner]
  Prometheus[Prometheus optional] --> API
```

The API writes an order and an outbox record to PostgreSQL. The worker reads the outbox and sends signed events to the mock partner. A separate signed callback endpoint can be exercised with the callback script. Prometheus scrapes API metrics; API, worker and partner emit logs. The current implementation has no reverse proxy, TLS termination or distributed tracing.


The Compose mock partner persists event IDs in a separate SQLite volume, so container recreation does not erase its history. The in-memory test mode remains available. Event deduplication alone does not make arbitrary business side effects exactly-once. Remaining work includes richer telemetry and a real AWS sandbox deployment with teardown verification. Local OAuth, network diagnostics, token-expiry and webhook-recovery checks are already implemented. These simulations do not establish AWS experience or learner competence.

Decisions: Python first to read and automate investigations. SQL receives substantial practice. Basic JavaScript/DevTools later for customer integration reproduction; React and Kubernetes await stronger role-specific evidence. Local default, lightweight optional services, no always-on cloud bill.

Resource target (unmeasured): core containers comfortably below 4 GB RAM; measure before adding telemetry. Current laptop/OS must be rechecked before installation.

## Optional OAuth profile

Keycloak issues synthetic client-credentials tokens. An OAuth gateway validates JWT signature, issuer, audience and expiry, maps the verified tenant claim to the local API credential and forwards to the API. It adds a second request ID for tracing. This profile is local-only and uses an HTTP development identity provider. See [OAuth lab](oauth.md).
