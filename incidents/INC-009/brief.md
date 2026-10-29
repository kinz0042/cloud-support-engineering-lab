# INC-009 — DNS and TLS troubleshooting

**Synthetic customer:** “The integration cannot connect to the API. We think the certificate is broken.”

Environment: disposable local RelayDesk stack. Start by testing the reported endpoint and time, and determine whether failure occurs during DNS, TCP, TLS, or HTTP. Avoid assuming that a connection failure proves a certificate problem.

Use `python scripts/netdiag.py bad-name.invalid --port 8081` to simulate an unresolvable name, then `python scripts/netdiag.py 127.0.0.1 --port 8081` for the working local HTTP service. To simulate a protocol mismatch, use `python scripts/netdiag.py 127.0.0.1 --port 8081 --tls`: the lab API serves plain HTTP, so TLS negotiation should fail. This is a protocol mismatch, not an expired-certificate example.

The tool uses the system trust store and hostname verification; it does not turn off certificate checks. A successful HTTP response means HTTP was reached, not that its status is successful. Test only systems you are authorized to contact. Record the error class, timestamps, configuration and competing hypotheses in [the template](../TEMPLATE.md), then write an escalation and customer update. Do not include sensitive hostnames or addresses in a public incident report.

Status: synthetic diagnostic drill authored. Unit tests cover DNS failure, local HTTP success and TLS protocol failure; the Compose CI network step also passed. [CI run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40960442415).
