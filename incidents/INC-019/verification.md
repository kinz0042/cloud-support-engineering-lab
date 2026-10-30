# INC-019 — synthetic port conflict: CI evidence

**Status:** assistant-executed simulation; learner investigation pending. **Customer report:** synthetic. **Severity:** not assigned because no real customer or business process was affected.

The [Linux workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41016015779) passed on a disposable GitHub-hosted Ubuntu runner at commit `2373e3b7189e2c36ea1f99f1197884895456d84c`. It started two uniquely named transient units using the same loopback port.

The first service responded with `alpha-demo`. The second entered `failed`, with process exit status `1`; its structured journal event was `listen_failed`, reporting `address_in_use` and Linux error number `98`. The first service remained healthy. The test stopped only the first synthetic unit, restarted the second, and verified its health response identified `bravo-demo`. Cleanup stopped the generated lab units.

The injected root cause was competition for the same local socket. The safe lab recovery released the socket by stopping its known owner; a real fix may require choosing an approved port or coordinating with the owner. The local process tests also exercise address-in-use handling without systemd. Complete [the investigation template](../TEMPLATE.md) with your own evidence, hypothesis tests, validation and customer/internal responses.

**Limits:** The CI test established the conflict from the unit journal and known synthetic listener. It did not run the optional `ss` command or verify that process-owner details are visible on the learner's machine. No customer message was sent, no real workload was stopped and WSL/laptop compatibility is unverified.
