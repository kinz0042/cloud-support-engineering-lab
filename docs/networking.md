# Network investigation guide

A request can fail at several points. Start with the exact hostname, port, protocol, time and network location reported by the customer; don't assume a 401, timeout or certificate error has the same cause.

The included `scripts/netdiag.py` checks a single explicitly specified endpoint in order: DNS resolution, TCP connection, optional TLS validation using the system trust store and hostname, then one HTTP GET. It reports the HTTP status separately. A syntactically valid HTTP response such as 401 or 500 still indicates that HTTP was reached; it does not mean the request succeeded.

```sh
python scripts/netdiag.py 127.0.0.1 --port 8081
python scripts/netdiag.py bad-name.invalid --port 8081
python scripts/netdiag.py 127.0.0.1 --port 8081 --tls
```

The last command demonstrates TLS against a plain-HTTP endpoint. It is a protocol mismatch, not proof of an expired or untrusted certificate. Use `--tls` only for an HTTPS service; verification is always enabled. The program uses a five-second connection timeout, though operating-system DNS lookup timing is outside its direct control. It does not send credentials or probe ranges, and it doesn't follow HTTP redirects.

For container issues, compare the hostname used inside the container with Docker Compose service names; host `localhost` and container `localhost` refer to different network namespaces. A DNS answer doesn't prove the port is open, and a TCP connection doesn't prove credentials or an application route are correct.

See [container DNS](../incidents/INC-008/brief.md) and [DNS/TLS](../incidents/INC-009/brief.md). Test only destinations you are authorized to access and redact sensitive hostnames or addresses from public evidence.
