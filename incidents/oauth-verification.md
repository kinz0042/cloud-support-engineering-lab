# INC-007 and INC-014 — OAuth verification evidence

**Status:** assistant-executed synthetic verification, learner investigations pending. No real customer, credential or production system was involved.

[GitHub Actions OAuth run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40959565988) started the disposable Keycloak and RelayDesk stack. Its `scripts/oauth_smoke.py` check confirmed:

- A valid Acme client-credentials token could read Acme orders; an Orbit token saw Orbit's separate data.
- Missing, malformed and wrong-audience tokens returned 401.
- A valid token with an unmapped tenant returned 403.
- The token endpoint rejected an incorrect client secret.
- The fixture's intentionally short-lived token was rejected after expiry.

The test does not establish real customer impact, a production root cause, TLS behavior, browser authorization-code flow, or refresh-token behavior. A previous CI run failed during identity startup with a connection reset. The test now retries transient connection resets while waiting for readiness; the linked rerun completed successfully.

For an actual case, record the endpoint and status, UTC time, request ID, client and audience configuration, expiry and issuer. Keep raw tokens and secrets out of tickets. A 401 at the resource server and a client authentication failure at the token endpoint point to different stages, so reproduce each separately.

**Illustrative customer update:** “We are checking the token request and the API's authorization response. Please share the request time and request ID, but do not send your client secret or access token.”

**Engineering handoff:** Include the sanitized reproduction, expected and actual statuses, configuration identifiers, expiry timing, tests performed and any remaining uncertainty. No message was sent.
