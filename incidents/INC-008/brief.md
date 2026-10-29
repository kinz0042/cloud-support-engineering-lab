# INC-008 — Container name resolution

**Synthetic customer:** “The application cannot connect to its database after a configuration change.”

Environment: disposable Compose stack. Compare the database service name in `DATABASE_URL` with the service names in `compose.yaml`. From the API container, use the Python socket resolver to inspect `db`; compare with an intentionally invalid name. Test DNS separately from TCP and authentication. Do not print the complete database URL because it contains a password.

```sh
docker compose exec api python -c "import socket; print(socket.getaddrinfo('db', 5432, type=socket.SOCK_STREAM))"
docker compose exec api python -c "import socket; print(socket.getaddrinfo('missing-db.invalid', 5432, type=socket.SOCK_STREAM))"
```

The second command should fail; capture the error. These are read-only checks and do not modify the network. A name resolving does not prove the database accepts connections or credentials. Cross-check readiness, container state and logs. Complete [the template](../TEMPLATE.md) with a customer update and engineering handoff. No real customer or production network is involved.

Status: DNS success and failure checks passed in the Compose CI network step; learner investigation pending. [CI run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40960442415).
