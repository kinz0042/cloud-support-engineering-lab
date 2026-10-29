# Incident catalogue

| ID | Customer symptom | Status | Evidence required |
|---|---|---|---|
| INC-001 | Order sync receives 401 while health is green | Runnable; learner investigation pending | Redacted HTTP responses, correlated logs, hypothesis tests |
| INC-002 | API returns 500 during order creation | Planned | Traceback, request ID, regression test |
| INC-003 | Database connection refused | Planned | DNS/port/config tests and database health |
| INC-004 | Webhook missed after timeout | Planned | Sender/receiver logs and delivery attempts |
| INC-005 | Duplicate events create duplicate orders | Planned | Event IDs and idempotency test |
| INC-006 | Queries become slow with growing data | Planned | EXPLAIN ANALYZE before/after and dataset size |
| INC-007 | OAuth refresh fails / JWT rejected | Planned | Redacted claims, clock/issuer/audience/signature checks |
| INC-008 | Container cannot reach database | Planned | Network inspection and service-name resolution |
| INC-009 | DNS or TLS connection fails | Planned | Lookup, connection and certificate-chain evidence |
| INC-010 | IAM denies private S3 object access | Planned | Caller identity, exact API, policy evaluation |
| INC-011 | Security group blocks application traffic | Planned | Flow/path tests and narrowly scoped rule change |
| INC-012 | Integration loops on rate limits | Planned | Retry-After, bounded backoff, recovery test |

Planned incidents are not implemented or completed. Severity depends on demonstrated impact, not status code alone.
