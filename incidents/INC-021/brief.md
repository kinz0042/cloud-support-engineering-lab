# INC-021 — Integration imports only the first 100 orders

**Synthetic customer complaint:** “Our integration sees only 100 recent orders, but the dashboard says there are more. Did the older orders disappear?”

**Environment:** disposable RelayDesk API and PostgreSQL. The original implementation silently capped the list at 100; the updated API returns an explicit `next_cursor`. No real customer, data loss or independently completed learner investigation is implied. Set severity only after confirming impact, affected integrations, duration and the availability of a workaround.

## Reproduce and collect evidence

Follow the [pagination runbook](../../docs/api-pagination.md) to add 105 synthetic same-timestamp orders to a disposable database and request pages. Compare the first page, `next_cursor`, the read-only client's total and a tenant-scoped database count. Record your own statuses, request IDs, timestamps, page sizes and redacted evidence. SQL fixture rows bypass the outbox, so this exercise does not establish webhook delivery.

## Competing hypotheses

1. The integration stops after the first page: inspect its pagination behavior and compare the next page.
2. The customer is using a different tenant credential: verify identity and scope without requesting a secret.
3. Data changed while pagination was in progress: compare a stable fixture and discuss the absence of snapshot guarantees.
4. Records are absent or filtered: compare an appropriately authorized, tenant-scoped database count and the API result.

## Resolution and validation

For the original simulated issue, add stable keyset pagination and teach the client to continue until `next_cursor` is null. Verify a fixed dataset with equal timestamps has no gaps or duplicates, another tenant does not see Acme records, invalid cursors fail, and the existing authenticated first-page request still succeeds. Validate through the OAuth gateway as well as the direct API. Existing lab volumes can add the index with the repeatable migration; a real migration requires a separate locking and deployment review.

Pagination does not guarantee a snapshot or solve concurrent-write reconciliation. An encoded cursor is neither a secret nor authorization. Explain any remaining uncertainty and avoid claiming records were lost until supported by evidence.

**Initial customer response:** “We’re comparing the API pages with the expected order count. The first response may contain only part of the results; we’ll confirm the remaining records and update you.”

**Engineering handoff:** include time range, tenant-safe identifier, endpoint, response status, request IDs, page size, whether a continuation was present, reconciliation evidence, affected client behavior, verified fix and remaining concurrency concerns. Redact credentials and customer records.

**Prevention:** document the paging contract and test traversal, ties, malformed cursors and tenant isolation. Use [the incident template](../TEMPLATE.md) to record your own actions and any assistance.
