# INC-014 — Client credentials rejected

**Synthetic customer:** “We cannot obtain an access token. The token endpoint rejects our integration.”

Environment: disposable Keycloak client-credentials profile. Investigate the token endpoint, grant type, client ID, credential configuration and request format. The automated test uses an intentionally wrong demo client secret, then requests a token with the correct demo credential. Never request or record an actual customer secret.

Distinguish failure to obtain a token from a token rejected by the API. Preserve redacted HTTP status, timestamps and request IDs where available; record competing hypotheses, validation, safe credential rotation guidance and a customer update in [the template](../TEMPLATE.md).

This is a synthetic scenario, not a real customer case. OAuth integration CI must pass before this scenario is considered verified.
