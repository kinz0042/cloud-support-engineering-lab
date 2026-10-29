# Security boundaries

Local synthetic lab only. Bind HTTP and any future dashboards to loopback. Never publish credentials, customer data, cookies, bearer tokens, JWTs or raw support bundles. Redact values, preserve request IDs and necessary diagnostic context.

The demo tokens are intentionally public. The Docker profile isolates order reads/writes by tenant key and uses parameterized SQL; that does not make the lab production-safe. Real deployments require a secret manager, TLS, rotation, tested least privilege and audits. OAuth, JWT and API keys are different mechanisms; successful decoding does not validate a JWT.

Fault injection is restricted to this lab. No external scanning or third-party fault injection. AWS work requires a user-owned sandbox, approved spending limit, billing alerts (not a hard spending cap), restricted IAM and teardown checks. Do not deploy AWS during the foundation phase.

The local webhook signs a timestamp and body with HMAC, rejects messages outside a five-minute window, and deduplicates event IDs. The Compose mock partner stores duplicate IDs in a named SQLite volume; the API stores callback IDs in PostgreSQL. The standalone in-memory partner mode loses IDs on restart. The fixed worker destination is restricted to its internal mock service. A production implementation must persist receiver idempotency, rotate secrets and constrain destinations to prevent SSRF. SQL must use parameter binding and read-only support access by default. Never disable certificate validation as a resolution.

The delivery recovery CLI is an operator tool using the API container's database privileges, not a separate authorization boundary. Inspection uses a read-only transaction. Replay changes one eligible dead delivery and writes an audit record atomically. Its actor label and recipient-review flag are operator assertions, not verified identities or proof of safe recipient processing. A privileged database user can alter the audit; do not describe it as tamper-proof.

