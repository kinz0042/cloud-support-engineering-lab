# INC-020 — Application cannot write a local record

**Synthetic customer complaint:** “Our integration has started failing when it saves its local record. The application is still running. Are records being lost?”

**Status:** isolated local Linux teaching fixture verified in [CI](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41024848468); no real customer, full filesystem or learner investigation has been verified. Triage severity using impact, duration, affected writes, retry behavior and possible data loss; an error code alone does not establish severity.

## Reproduction and evidence

The [Linux write-failure lab](../../docs/linux-space-lab.md) invokes a small synthetic writer against `/dev/full`. Its structured output reports a real `ENOSPC` write error without filling a disk. Record the command, UTC time, exit status and event. Confirm separately that the affected production-like path, mount, service and request are known before comparing evidence; this fixture does not supply a real application request ID or real customer logs.

## Hypotheses and investigation

| Hypothesis | Evidence to seek in a real environment |
| --- | --- |
| Block capacity exhausted on the affected mount | Identify the exact path and mount; compare block usage and available capacity. |
| Inodes exhausted | Check inode usage on the same mount and investigate the file population safely. |
| Quota or a different resource limit | Check the relevant user, project, container or filesystem limits; confirm the actual error and scope. |
| Permission or other I/O failure | Compare the real error number, process identity and path permissions; do not label every failure as disk exhaustion. |

For this fixture only, the demonstrated cause is the intentionally selected `/dev/full` sink. It says nothing about the actual capacity of `/tmp` or any application filesystem.

## Resolution and validation

The exercise's separate temporary-file check writes and reads one synthetic event, then cleans up its own directory. This is a control demonstrating that a different write path works; it does not repair the original device or a full production filesystem. A real resolution must address the identified mount or limit with the appropriate owner, then retry the original operation, monitor the relevant resource and consider lost or queued work. Treat a cached readback as a functional check, not proof of durable storage.

**Customer update example:** “We are investigating the write failures and checking the affected storage path and impact. We will confirm the outcome of affected records before stating whether any were lost.”

**Internal handoff:** include the relevant service, scoped path and mount, timestamps, error number, block and inode evidence, owner, safe remediation, validation, possible queued or missing writes and remaining uncertainty. Redact credentials and sensitive names.

**Prevention:** review retention and storage-capacity monitoring, including inode usage where relevant, and agree an escalation path. Complete the [incident template](../TEMPLATE.md) using only observed evidence and record any assistance.
