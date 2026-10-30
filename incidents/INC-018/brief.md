# INC-018 — Linux status service exits during startup

**Synthetic customer report:** "Our local status endpoint stopped responding after a configuration change. Can you help us restore it?"

**Severity:** provisional; establish whether this endpoint is informational or blocks a business process, which users are affected, and when the symptoms began. **Environment:** the optional, isolated Linux systemd lab. It is a synthetic service, not a deployed customer agent.

## Reproduce and collect evidence

Use the [Linux service lab](../../docs/linux-service-lab.md) to start the service with an empty instance value. Record the unit name, UTC time, expected versus actual behavior, `systemctl` state and exit status, and relevant redacted `journalctl` entries. The injected process exits with status `2` and reports `configuration_error` / `missing_instance`; collect the actual output before treating that as your finding.

## Investigate

Consider a missing or invalid environment value, an incorrect executable path, a port already in use and host networking. Which evidence would distinguish a process that never started from a running process that cannot be reached? Check the unit's configuration source and process state without exposing any secrets. A failed service does not by itself establish a network failure.

## Resolve and validate

Set a synthetic instance value in the lab environment file and restart the same unit. Confirm it is active, has a running process, and serves the expected `alpha-demo` health response. Check the journal for the new startup and verify that editing the environment alone did not automatically restart the failed service. Stop the lab unit and clean up the temporary files when finished.

Prevent recurrence by validating required configuration before deployment and documenting the service restart/rollback process. Complete [the investigation template](../TEMPLATE.md) with your actual evidence, tested hypotheses, resolution, validation, escalation notes and remaining uncertainty. A suitable initial customer update explains that service startup is under investigation and sets an agreed next-update time without asserting an unverified cause.

## Verification status

The process and systemd checks are automated in `tests/test_linux_service.py` and `scripts/systemd_smoke.py`. See [CI verification](verification.md) once recorded. The learner has not yet completed this investigation independently.
