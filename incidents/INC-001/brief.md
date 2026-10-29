# INC-001 — Order sync rejected

**Synthetic customer report:** “Our order integration stopped syncing. The health page still says OK. Please investigate without changing our order data.”

Environment: local Python foundation API; synthetic orders. Suggested severity: SEV-3 if one integration is affected and no data loss; reassess after scoping impact.

Reproduce the customer's request:

```sh
curl -i http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/v1/orders -H "Authorization: lab-demo-token-not-a-secret"
```

Use `curl.exe` in PowerShell. The support sandbox uses a public demonstration token. Do not use real credentials.

Your first task is observation, not a fix:
1. Record the two status codes, response bodies and request IDs.
2. Explain what a healthy health endpoint does and does not prove.
3. Propose two hypotheses and one test for each.
4. Ask the customer at most three targeted questions. Never ask for their secret token.

Then investigate, validate the correction and a negative control, and complete the template. Do not label yourself independently competent after following an answer. This brief is intentionally a simple baseline; later incidents will have incomplete reports and multiple plausible causes.
