# INC-018 — synthetic configuration failure: CI evidence

**Status:** assistant-executed simulation; learner investigation pending. **Customer report:** synthetic. **Severity:** not assigned because no real customer or business process was affected.

The [Linux workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41017578954) passed on a disposable GitHub-hosted Ubuntu runner at commit `9a490201649ee7d056094a2fb5ff059cbfaaa2ea`. It ran the process/socket tests and a real systemd/journal investigation. `scripts/systemd_smoke.py` is designed for that disposable runner. Its environment-variable check is not an attestation that a host is disposable.

The test created a uniquely named transient service with an empty `RELAY_LAB_INSTANCE`. The unit reached `failed`, systemd reported process exit status `2`, and the unit journal contained a structured `configuration_error` event with reason `missing_instance`. The test corrected the synthetic environment file and confirmed the failed state persisted until an explicit restart. After restart the unit became active and its loopback health endpoint identified `alpha-demo`. The test also confirmed that its effective user was the unprivileged runner and `NoNewPrivileges` was enabled. Cleanup stopped the two generated lab units; no actual customer message was sent.

The injected root cause was an empty required instance value. Prevention in this simulation includes explicit startup validation and an error without echoing the configuration value; deployment-time validation and a reviewed restart procedure remain recommended improvements. A learner should still record their own hypotheses, evidence, customer update and engineering notes using [the template](../TEMPLATE.md).

**Limits:** This is an intentionally induced failure on a CI runner. It does not verify a production service, the user's laptop, WSL, or the learner's independent skill. The process tests check that unrelated synthetic secret values are not printed; never publish real environment files or unredacted customer logs.

The same source's standalone Python process tests also passed on a [GitHub-hosted Windows Server runner](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41017578989). That check does not run systemd and does not verify the learner's laptop.
