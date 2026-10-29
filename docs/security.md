# Security boundaries

Local synthetic lab only. Bind HTTP and any future dashboards to loopback. Never publish credentials, customer data, cookies, bearer tokens, JWTs or raw support bundles. Redact values, preserve request IDs and necessary diagnostic context.

The demo token is intentionally public. Real deployments require a secret manager, TLS, rotation, tenant-scoped authorization, audit logging and tested least privilege. OAuth, JWT and API keys are different mechanisms; successful decoding does not validate a JWT.

Fault injection is restricted to this lab. No external scanning or third-party fault injection. AWS work requires a user-owned sandbox, approved spending limit, billing alerts (not a hard spending cap), restricted IAM and teardown checks. Do not deploy AWS during the foundation phase.

Future webhook work must verify signatures, reject stale replays and constrain destinations to prevent SSRF. SQL must use parameter binding and read-only support access by default. Never use disabled certificate validation as a resolution.
