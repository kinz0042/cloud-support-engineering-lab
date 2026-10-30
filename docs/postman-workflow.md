# Postman investigation workflow

These collections send requests to the **local synthetic RelayDesk lab**, not a public SaaS account. They create demo orders and may trigger deliveries to the mock partner. Never enter real API keys, OAuth secrets, access tokens or customer data into the shared collection.

## Before you run

1. Start the [Docker application](operations.md) for the API collection. For the OAuth collection, also start the [OAuth profile](oauth.md) and allow the identity provider time to start.
2. Import [`RelayDesk.postman_collection.json`](../postman/RelayDesk.postman_collection.json) and, for OAuth, [`RelayDesk-OAuth.postman_collection.json`](../postman/RelayDesk-OAuth.postman_collection.json) into Postman. No separate environment is required for the default local ports.
3. Run each collection **in order**, using the collection runner. The API collection creates a new synthetic order and then reuses its ID; the OAuth collection obtains short-lived tokens immediately before using them. Running an individual dependent request without its preceding request will not reproduce the sequence.
4. Inspect the response status, the assertion results and `X-Request-ID`. The OAuth gateway has its own request ID and may also return `X-Upstream-Request-ID` when it forwards a request. Record IDs and timestamps; do not record bearer tokens or secrets.

Each API collection run creates another synthetic order; existing lab data remains in the database. For a disposable lab only, `docker compose -f compose.yaml -f compose.auth.yaml down -v` removes its volumes and data. Do not use that command if you need to retain the data.

## What the checks establish

| Request sequence | Expected observation | Investigation value |
| --- | --- | --- |
| Health and readiness | 200 when the process and database are available | A healthy process alone does not establish database readiness. |
| Missing or incorrect API key | 401 | Compare the authorization header and affected tenant before changing credentials. |
| Create, then replay | 201 with `created: true`; then 200 with `created: false` and the same order ID | Repeating the same external ID for the same tenant does not create a second order. |
| Acme and Orbit visibility | Acme sees the new order; Orbit does not | A specific cross-tenant isolation check, not a complete security audit. |
| First order page | At most one order and a `next_cursor` field | The collection checks the response shape; use the [pagination investigation](api-pagination.md) for full traversal. |
| Invalid JSON | 400 with `invalid_request` | Inspect the body and content type before escalating a client error. |
| OAuth token then gateway | Valid demo token returns 200 | A token being issued and the gateway accepting it are separate checks. |
| Wrong client secret | Identity provider returns 401 | Failure is at token issuance, before the API call. |
| Wrong token audience | Gateway returns 401 | A signed token can still be rejected for the wrong audience. |
| Valid token for unmapped tenant | Gateway returns 403 | Authentication succeeded, but this lab cannot map the tenant to an API credential. |

If a check fails, note the request and expected versus actual status, copy the request ID, inspect the relevant API or gateway logs, and test one hypothesis at a time. For example, if `/health` succeeds but `/ready` returns 503, investigate database connectivity before restarting the API. A 401 from the identity provider is a different failure location from a 401 at the gateway. Confirm recovery by rerunning the failing request and checking a control request for an unaffected tenant.

The exported collections are also configured to run against real disposable containers in [GitHub Actions](../.github/workflows/postman.yml) using Newman, a Postman collection runner. Node 22 and Newman 6.2.3 are used on the CI runner; the direct Newman version is pinned, while its transitive npm dependencies are not locked. Check the workflow run for the actual result. This CI execution does not verify importing or operating the desktop Postman application on your computer.

On 30 October 2026, [this successful CI run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41018854143) used commit `526d991fa9388573a1e216aa3bbf2d5d73ea12d3`. The API collection completed 11 requests and 27 assertions; the OAuth collection completed 8 requests and 16 assertions, with no failures. The run also executed the separate Compose and OAuth smoke scripts before the collections. This is automated evidence from a disposable runner, not a record of an independently performed learner investigation.

A [later run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41026525509) at commit `ed42c02a99ecaa19611cc5b818e279b75dd54a6b` included the first-page check: 12 API requests and 30 assertions, plus eight OAuth requests and 16 assertions, all passing. The collection checks the first page; full pagination traversal is covered separately in [INC-021](../incidents/INC-021/verification.md).

The OAuth collection stores short-lived **demo** tokens in collection variables while it runs. It does not test token expiration; [the OAuth smoke test](../scripts/oauth_smoke.py) separately exercises expiration. Do not export or share collection variables containing real tokens. The 20-second demo lifetime makes slow or manually spaced OAuth requests expire; obtain a new token and immediately retry if that happens.
