# OAuth and JWT lab

This optional local profile adds a Keycloak identity provider and an OAuth gateway to the existing Compose lab. Its clients, secrets and data are **public synthetic fixtures**. Keycloak runs in development mode with local HTTP and must never be exposed publicly or reused for production.

Start with `docker compose -f compose.yaml -f compose.auth.yaml up -d --build`. Keycloak can take a while to start. The gateway listens only on host loopback port 8083, the test identity endpoint on 8085, and the underlying API on 8081. Stop while retaining the database using `docker compose -f compose.yaml -f compose.auth.yaml down`. Deleting volumes destroys lab data.

The provider issues short-lived access tokens through OAuth 2.0 client credentials. The gateway validates RS256 signatures using the configured provider's JWKS, verifies issuer, audience and expiry, and maps the validated `tenant_id` claim to a synthetic tenant credential. It forwards to the fixed internal API and returns its request ID in `X-Upstream-Request-ID`; the gateway generates its own request ID. An invalid, expired or wrong-audience token yields 401; a valid token for an unmapped tenant yields 403; an unavailable JWKS service yields 503. These categories are deliberately distinct.

The service account fixtures are `acme-client`, `orbit-client`, `unknown-tenant` and `wrong-audience`, each with a demo secret formed by adding `-local-secret` to its ID. The realm deliberately uses a 20-second token lifetime. The automated `scripts/oauth_smoke.py` assumes a fixture order has already been created; CI creates it with `scripts/compose_smoke.py`. It never prints access tokens. Real credentials and raw tokens must never be committed or shared.

For incident investigation use [INC-007](../incidents/INC-007/brief.md) and [INC-014](../incidents/INC-014/brief.md). Inspect request IDs, gateway logs, token endpoint status, issuer, audience, expiry and system clock. Decode only redacted synthetic tokens; decoding a token alone does not validate its signature. Do not turn off signature, TLS or audience checks to make an integration work.

This is an integration demonstration, not production-grade authorization: fixed demo credentials, no TLS, no secret manager, no token revocation checks and a simplified tenant mapping. Only client-credentials flow is configured; browser authorization-code flow and refresh-token lifecycle are not implemented. CI status is the source of truth for current validation.

## Postman and boundaries

Import [the OAuth Postman collection](../postman/RelayDesk-OAuth.postman_collection.json) and run its requests in order. It checks valid and missing tokens, a wrong client secret, a wrong audience and an unmapped tenant. The collection stores synthetic tokens in collection variables; never put real credentials or tokens into a shared collection. See the [Postman investigation workflow](postman-workflow.md) for the 20-second lifetime, expected results and CI verification. Desktop Postman import has not been verified here.

The base API is also reachable on loopback port 8081 using demo API keys, bypassing the gateway. This arrangement allows side-by-side troubleshooting exercises and is not a production security boundary. Do not expose either service publicly.
