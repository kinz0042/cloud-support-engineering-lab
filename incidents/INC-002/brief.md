# INC-002 — Order API fails while health is green

**Synthetic customer report:** “The order list has returned a server error for the last ten minutes. Your health endpoint says OK. Are our orders lost?”

Environment: local Python API with a synthetic order dependency. No real customer data or PostgreSQL yet. Severity: investigate affected customers and duration before assigning; a 500 alone does not establish severity or data loss.

Start the service in failure mode:

PowerShell:

```powershell
$env:LAB_ORDER_STORE_MODE = 'unavailable'
py app/server.py
```

Other shells:

```sh
LAB_ORDER_STORE_MODE=unavailable python app/server.py
```

In another terminal, use `curl.exe` on Windows:

```sh
curl -i http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/ready
curl -i http://127.0.0.1:8080/v1/orders -H "Authorization: Bearer lab-demo-token-not-a-secret"
```

Record actual status codes, request IDs and sanitized server log entries. Form two hypotheses before looking at `app/server.py`. Explain why `/health` and `/ready` disagree and what evidence would be needed before telling the customer about data loss. Restart without the failure setting, repeat the requests, and verify recovery and a negative control. Fill in the incident template with a customer update and an internal engineering note.

This is an intentional **synthetic dependency outage**. It is not evidence of a real PostgreSQL failure. Do not claim you repaired a production system.
