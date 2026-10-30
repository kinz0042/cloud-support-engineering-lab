# INC-019 — synthetic port conflict: CI evidence

**Status:** assistant-executed simulation; learner investigation pending. **Customer report:** synthetic. **Severity:** not assigned because no real customer or business process was affected.

The [Linux workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41017578954) passed on a disposable GitHub-hosted Ubuntu runner at commit `9a490201649ee7d056094a2fb5ff059cbfaaa2ea`. It started two uniquely named transient units using the same loopback port.

The first service responded with `alpha-demo`. The second entered `failed`, with process exit status `1`; its structured journal event was `listen_failed`, reporting `address_in_use` and Linux error number `98`. The first service remained healthy. The test stopped only the first synthetic unit, restarted the second, and verified its health response identified `bravo-demo`. Cleanup stopped the generated lab units.

The injected root cause was competition for the same local socket. The safe lab recovery released the socket by stopping its known owner; a real fix may require choosing an approved port or coordinating with the owner. The local process tests also exercise address-in-use handling without systemd. Complete [the investigation template](../TEMPLATE.md) with your own evidence, hypothesis tests, validation and customer/internal responses.

**Limits:** The CI test established the conflict from the unit journal and known synthetic listener. It did not run the optional `ss` command or verify that process-owner details are visible on the learner's machine. No customer message was sent, no real workload was stopped and WSL/laptop compatibility is unverified.

The same source's standalone Python process tests also passed on a [GitHub-hosted Windows Server runner](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41017578989). That check does not run systemd and does not verify the learner's laptop.
