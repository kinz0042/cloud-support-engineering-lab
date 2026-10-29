# INC-004 — Partner rejects webhook deliveries

**Customer report:** “Our order was accepted, but our integration did not receive the notification.”

**Environment:** disposable local Docker Compose lab, synthetic customer Acme. Treat the priority as provisional until you know the affected customers, duration and business impact.

## Start the scenario

From the repository root in a POSIX shell:

```sh
LAB_PARTNER_MODE=reject docker compose up -d --build
docker compose ps
curl -i http://127.0.0.1:8081/ready
curl -i http://127.0.0.1:8081/v1/orders \
  -H 'Authorization: Bearer acme-local-key' \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"inc-004-example"}'
```

On PowerShell set `$env:LAB_PARTNER_MODE = "reject"` before `docker compose up -d --build`; use `curl.exe` and shell-appropriate JSON quoting. The key is a public, synthetic lab credential. Use a new external ID for each fresh test. A successful order response establishes persistence, not successful notification.

## Investigate

Record the response status, order ID, request ID and UTC time. Inspect each part of the path:

```sh
docker compose logs --tail=100 api worker partner
docker compose exec db psql -U lab -d relaydesk -c "SELECT id,order_id,state,attempts,last_error FROM deliveries ORDER BY id;"
```

Compare the order ID with the delivery record. Consider competing explanations: order creation failed, the worker cannot reach the partner, or the partner is responding with an error. Which evidence distinguishes each? The injected partner mode returns HTTP 503; the worker retries with bounded backoff. An HTTP response from the partner distinguishes an application-level rejection from a DNS failure, but does not by itself establish why a real partner rejected a request.

## Recover and validate

Before replaying anything, check whether the recipient processed the event and whether the delivery is already dead. Duplicates can have side effects. To restore the synthetic partner in a POSIX shell:

```sh
LAB_PARTNER_MODE=normal docker compose up -d --no-deps --force-recreate partner
docker compose logs --tail=100 worker partner
docker compose exec db psql -U lab -d relaydesk -c "SELECT id,order_id,state,attempts,last_error FROM deliveries ORDER BY id;"
```

For PowerShell, change `$env:LAB_PARTNER_MODE` to `normal` and run the Compose command without the leading environment assignment. Pending retries may succeed after recovery; once a delivery is dead it requires a separately reviewed replay. Do not claim recovery merely because the partner container restarted: confirm the relevant delivery state and recipient evidence. Do not run destructive volume cleanup on data you want to keep.

## Record and communicate

Use [the investigation template](../TEMPLATE.md) to record observations, failed hypotheses, root cause, evidence, resolution and prevention. Draft a customer update that explains impact and next steps without sharing internal credentials. Include a separate engineering handoff with the order ID, timestamps, status and relevant redacted logs.

**Verification:** the injected 503 and recovery have passed the automated [webhook failure smoke test](../../scripts/webhook_fault_smoke.py) in GitHub Actions. That automated check is evidence about the simulation, not evidence of a learner's independent investigation. See [verification evidence](../webhook-verification.md).
