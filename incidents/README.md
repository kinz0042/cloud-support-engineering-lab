# Incident catalogue

| ID | Customer symptom | Status | Evidence required |
|---|---|---|---|
| [INC-001](INC-001/brief.md) | Order sync receives 401 while health is green | Runnable; learner investigation pending | Redacted HTTP responses, correlated logs, hypothesis tests |
| [INC-002](INC-002/brief.md) | Order listing returns 500 while liveness is green | Runnable; learner investigation pending | Correlated request log, readiness comparison, recovery and regression check |
| [INC-003](INC-003/brief.md) | Database connection refused | Verified in CI; learner investigation pending | DNS/port/config tests and database health |
| [INC-004](INC-004/brief.md) | Partner rejects webhook delivery | Recovery verified in CI; learner investigation pending | Sender/receiver logs and delivery attempts |
| [INC-005](INC-005/brief.md) | Duplicate signed callback | Verified in CI; learner investigation pending | Event IDs and idempotency test |
| [INC-006](INC-006/brief.md) | Queries become slow with growing data | SQL drill verified in CI; learner investigation pending | EXPLAIN ANALYZE before/after and dataset size |
| [INC-007](INC-007/brief.md) | JWT rejected | Verified in OAuth CI; learner investigation pending | Redacted claims, clock/issuer/audience/signature checks |
| [INC-008](INC-008/brief.md) | Container cannot reach database | Diagnostic checks verified in CI; learner investigation pending | Network inspection and service-name resolution |
| [INC-009](INC-009/brief.md) | DNS or TLS connection fails | DNS and TLS protocol mismatch verified in CI; learner investigation pending | Lookup, connection and certificate-chain evidence |
| [INC-010](INC-010/brief.md) | IAM denies private S3 object access | Designed; AWS deployment and investigation pending | Caller identity, exact API, policy evaluation |
| INC-011 | Security group blocks application traffic | Planned | Flow/path tests and narrowly scoped rule change |
| [INC-012](INC-012/brief.md) | Partner rate limits delivery | Recovery verified in CI; learner investigation pending | Retry-After, bounded retries, recovery test |
| [INC-013](INC-013/brief.md) | Database readiness alert | Monitoring drill verified in CI; learner investigation pending | Gauge, alert state, logs and recovery evidence |
| [INC-014](INC-014/brief.md) | OAuth client credentials rejected | Verified in OAuth CI; learner investigation pending | Token endpoint status and redacted configuration |

Planned incidents are not implemented or completed. Severity depends on demonstrated impact, not status code alone.

