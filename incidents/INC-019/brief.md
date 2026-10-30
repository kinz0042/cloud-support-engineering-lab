# INC-019 — A Linux service cannot bind its port

**Synthetic customer report:** "A second instance won't start after deployment, but the existing status endpoint still works."

**Severity:** provisional; determine whether redundancy, rollout or customer operations are affected. **Environment:** the optional, isolated Linux systemd lab with two synthetic services on loopback.

## Reproduce and collect evidence

First recover the `alpha-demo` service from [INC-018](../INC-018/brief.md). Then use the [Linux service lab](../../docs/linux-service-lab.md) to start `bravo-demo` on the same port. Record both unit names, the port, UTC time, the second unit's state and exit status, relevant journal events and the first instance's health response. The deliberately conflicting service reports `listen_failed` and `address_in_use`; the existing instance remains available.

## Investigate

Compare configuration errors, a bind conflict, firewall filtering and a crashed incumbent. Inspect the two units' `MainPID` values and the local listener with `ss` when available. A bind failure means the new process could not acquire the local socket; it does not by itself prove external traffic is blocked. Avoid exposing environment files or terminating an unknown process.

## Resolve and validate

Only because both services belong to this disposable exercise, stop the first unit and restart the second. Confirm the second unit is active and its health endpoint identifies `bravo-demo`. Verify the first no longer owns the port. A real incident may require allocating a different approved port or coordinating with the existing service owner.

Prevent recurrence with reviewed port allocation and deployment checks. Complete [the incident template](../TEMPLATE.md), including tested hypotheses, evidence, containment/rollback, customer response and internal handoff. Do not claim a real customer outage or personal investigation until you have performed and recorded the exercise.

## Verification status

The process and systemd checks are automated in `tests/test_linux_service.py` and `scripts/systemd_smoke.py`. See [CI verification](verification.md) once recorded. The learner's investigation remains pending.
