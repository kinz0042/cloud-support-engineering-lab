# INC-022: An order submission stalls while health remains green

**Scenario:** Synthetic customer integration; local RelayDesk API. **Suggested severity:** SEV-3 for an isolated blocked submission; reassess if many customers or submissions are affected. **Learner investigation:** pending.

## Customer report

“Our integration hangs when sending an order. The health endpoint is responding. We need to know whether to retry.”

## Environment and reproduction

The direct local API uses Python's threaded HTTP server. A client sends a POST with a valid tenant key and a `Content-Length` larger than the bytes it actually transmits, then leaves the connection open. Run the automated local TCP reproduction from the repository root:

```sh
python -m unittest discover -s tests -p test_http_request_body.py -v
```

The fixture sends a partial body to both the order and callback endpoints. It also sends a half-closed incomplete body and ambiguous framing. It uses synthetic credentials and data, a fake store, and a shortened idle timeout for the test. No database or external service is required.

## Evidence and investigation

1. Confirm time, route, request ID and impact; request sanitized client timing and headers, excluding authorization and payload contents. Do not ask the customer to disclose secrets.
2. Compare `/health` with the affected POST. A healthy process proves neither complete uploads nor successful database writes.
3. Inspect the sanitized `request_completed` log for the matching request ID. In the fixed service, `body_read_timeout` with status 408 identifies this local body-read timeout; `bad_body` with 400 signals an invalid body or framing and needs further evidence. A missing log alone does not prove the cause.
4. Compare declared `Content-Length` in bytes with the actual UTF-8 payload length and check whether the client or proxy sent `Transfer-Encoding` or repeated length headers. Capture only synthetic or suitably redacted evidence. Test from a controlled client with a complete body; compare with a deliberately incomplete request.
5. Consider authorization failure, network interruption, proxy behavior, API body framing and database failure. A 408 from this handler occurs before any store write; a client-side timeout alone does not establish whether a write occurred in another architecture. Check the order by external ID before deciding whether to retry.

## Root cause and resolution

In this reproducible scenario, the declared body length exceeds the bytes provided and the client leaves the connection idle. Previously the handler waited without an application-configured body-read timeout. The updated handler bounds idle reads, rejects incomplete or ambiguous framing, and returns a 408 or 400 before touching the store. Fix the integration to send a single accurate byte length and complete JSON. Then retry using the same external ID, verify the resulting order and, separately, the webhook delivery.

The API's external-ID idempotency applies per tenant to order creation in this lab; it does not prove arbitrary real services are safe to retry. It also does not prove a webhook reached the partner.

## Validation and prevention

The socket tests check stalled order and callback uploads return 408, half-closed and ambiguous requests return 400, no fake-store mutation occurs for these requests, and a correctly framed order succeeds. Logs must not include the test bearer key. Confirm expected results on the revision under test; a passing local test is not evidence of a real customer incident or learner investigation.

The three-second limit is a socket **idle** timeout during body reads, not a total request deadline, concurrency limit, header timeout or DDoS protection. A slow stream can extend the total read. Python's built-in HTTP server is for the isolated lab, not public deployment; a production edge would need separately designed resource limits, timeout policy, supported framing, TLS and monitoring.

## Customer-facing update

“We reproduced a stalled submission in the test environment when the declared request body length did not match the bytes sent. Please check the integration's request framing and send a complete JSON body. Before retrying, check whether the original order exists; in this lab you can use the same external ID to avoid creating another order. Please share the request ID and timestamp if the issue continues, without credentials or the full payload.”

## Internal engineering notes

Capture the request ID, sanitized route/status/reason, client/library version, framing behavior and whether the order exists. Never paste tokens, webhook secrets or customer payloads into tickets. Check proxy and application logs together before attributing the failure. The handler logs the timeout reason but does not log request bodies or credentials. Use the test above to prevent regressions and track any production-grade deadline or edge controls as separate work.
