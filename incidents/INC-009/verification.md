# INC-009 — Diagnostic verification evidence

**Status:** assistant-executed synthetic checks. Learner investigation pending. No external customer system was contacted.

The local Python test suite ran the network diagnostic against:

- A local temporary HTTP server: DNS resolution for the loopback address succeeded, TCP connected, and the HTTP response was 200.
- A reserved `.invalid` hostname: resolution failed before a TCP check was attempted.
- A local plain-HTTP server with TLS requested: TCP connected but TLS negotiation failed.
- A hostname containing a line break: input was rejected.

These tests check error separation and the behavior of the utility. They do not demonstrate an expired certificate, a real DNS outage, or production latency. The test file is `tests/test_netdiag.py`. The Compose workflow includes a separate container DNS and transport smoke check; consult CI for its current status.

**Hypotheses:** DNS failure, TCP refusal, TLS mismatch, invalid certificate and an application response are distinct possibilities. The local tests establish only the specific injected conditions above.

**Customer-facing example:** “We are checking where the connection fails. Please share the endpoint hostname, approximate time and error text, with any credentials removed.”

**Engineering handoff:** Record sanitized DNS results, the port and network context, TCP result, TLS error category and HTTP status where available. Do not disable certificate validation. No customer message was sent.
