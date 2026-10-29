# INC-013 — Database readiness alert

**Synthetic report:** "Order requests are failing. The monitoring dashboard shows the database readiness alert firing."

Run the observability profile with the disposable lab. Stop only the lab database, then inspect Prometheus alerts, the `relaydesk_database_ready` gauge, `/health`, `/ready`, and timestamped API logs. Compare monitoring signals with a request made using a synthetic tenant key. Explain what each signal proves and what it does not prove. Restart the lab database, wait for readiness, repeat the customer request, and observe the alert return to inactive.

Use [the incident template](../TEMPLATE.md) for evidence, hypothesis tests, validation, prevention, an initial customer update and an engineering handoff. The rules are demonstrations with short thresholds; no external notification receiver is configured. This is not a real customer incident.
