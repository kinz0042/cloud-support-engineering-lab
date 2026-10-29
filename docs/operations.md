# RelayDesk operations (Docker profile)

Prerequisites: Docker Engine with Compose; about 4 GB free RAM recommended, not yet measured. The Docker profile is a local synthetic system. A GitHub Actions job has verified the PostgreSQL schema, order/outbox writes, tenant separation, callback uniqueness and delivery functions against a real Postgres service. Full Compose startup has not been executed in the authoring workspace, so container networking and service startup still need verification.

```sh
docker compose up -d --build
docker compose ps
curl -i http://127.0.0.1:8081/health
curl -i http://127.0.0.1:8081/ready
curl -i http://127.0.0.1:8081/v1/orders -H 'Authorization: Bearer acme-local-key'
curl -i http://127.0.0.1:8081/v1/orders -H 'Authorization: Bearer orbit-local-key'
curl -i http://127.0.0.1:8081/v1/orders -H 'Authorization: Bearer acme-local-key' -H 'Content-Type: application/json' -d '{"external_id":"customer-order-001"}'
curl http://127.0.0.1:8081/metrics
docker compose logs --tail=50 api worker partner
```

Windows PowerShell: use `curl.exe` for these commands; quoting JSON differs by shell. The HTTP foundation on port 8080 remains separately runnable without Docker. The Compose application uses 8081.

`/health` reports process liveness. `/ready` probes PostgreSQL. `X-Request-ID` appears in API responses and structured logs. A 201 means the order was stored and queued; webhook delivery is asynchronous. Tenant credentials are `acme-local-key` and `orbit-local-key` in this disposable lab. They are public demonstrations, not real secrets.

Postgres schema initializes only on a fresh volume. To inspect tables: `docker compose exec db psql -U lab -d relaydesk -c "SELECT id,state,attempts,last_error FROM deliveries;"`. To stop without deleting data: `docker compose down`. Never run `down -v` against valuable data; it destroys the lab database volume.

Failure drills: [database](../incidents/INC-003/brief.md), [delivery](../incidents/INC-004/brief.md), [duplicate callback](../incidents/INC-005/brief.md), [rate limit](../incidents/INC-012/brief.md). Keep timestamps, request IDs, a hypothesis table, a tested fix and clear customer update. Never paste raw API keys or database URLs into public incident reports.
