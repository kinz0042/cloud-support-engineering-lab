# INC-007 — JWT rejected by the API

**Synthetic customer:** “Our service receives a 401 when calling your orders endpoint. We successfully obtained a token earlier.”

Environment: disposable OAuth/Keycloak Compose profile; expected tenant Acme. Investigate whether the token is missing, malformed, expired, intended for a different audience or issued by the wrong provider. Use the token failure checks in `scripts/oauth_smoke.py`, gateway request IDs and redacted logs; do not paste a real token into the report. The synthetic realm issues 20-second tokens.

Form hypotheses before selecting a cause. Validate the correct issuer, audience, expiry and signature, then test a newly issued token and a negative control. Decoding a JWT is not signature verification. Explain what the evidence rules out and what remains uncertain. Complete [the template](../TEMPLATE.md), including an initial customer update and engineering handoff.

This is a lab simulation. CI verification of this profile should be checked before asserting it works.
