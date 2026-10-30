# Linux write-failure investigation

This optional exercise triggers a real Linux `ENOSPC` write error using `/dev/full`. It does **not** fill a filesystem, change quotas, or represent an actual customer outage. A separate recovery check writes and reads one synthetic record in a temporary directory, which the script removes. The lab never accepts a user-specified destination path.

Requirements: Linux, Python 3.11+ and the real `/dev/full` character device. Use an authorized disposable environment. The script verifies the device type and Linux device number before writing. It does not create or modify `/dev/full`. The learner's Windows laptop and WSL setup have not been verified.

## Reproduce and observe

From the repository root:

```bash
python3 scripts/enospc_lab.py --mode fault
```

The expected result is a nonzero exit status and a JSON event with `write_failed`, `no_space`, and the Linux `ENOSPC` error number. A `fixture_unavailable` event with exit status 2 means the device or permission prerequisite was not met; it is **not** a reproduced disk-full result. Another I/O error is reported separately. The error is deliberately induced by the device; it is not evidence that the filesystem is full.

For an actual incident, first identify the exact process, affected write path, mount and error time. On an authorized Linux host, read-only observations may include the following; replace `/tmp` with the relevant **known** directory when investigating a real service:

```bash
findmnt --target /tmp
df -h /tmp
df -i /tmp
```

`df -h` concerns filesystem blocks, while `df -i` concerns inode availability. Neither command identifies the cause of this `/dev/full` fixture. Quotas, a different mount, deleted-but-open files, filesystem-specific behavior or other limits can also matter. If appropriate and authorized, investigate them with the responsible host owner. Record observations without publishing sensitive paths or file names.

## Controlled recovery check

```bash
python3 scripts/enospc_lab.py --mode recovery
```

This writes a small synthetic event to a newly created temporary file, checks its contents and removes its temporary directory. A `write_succeeded` event and `readback_verified: true` show that this separate temporary write and read worked. They do **not** repair or prove capacity on an actual affected filesystem, and readback is not a durability guarantee.

For a real incident, coordinate an approved remediation based on evidence: for example, address an identified retention problem or request capacity from the responsible owner. Validate the original operation on the original mount, monitor relevant block and inode usage, and communicate what was actually checked. Do not delete unknown files, restart unrelated services, or assume that moving a write to `/tmp` fixes production storage.

Use [INC-020](../incidents/INC-020/brief.md) for the incident workflow. The Python checks cover the real device error, separate successful write/readback, error classification and a short-write control. They do not create a genuinely full filesystem or measure quota behavior.

References: [Linux `/dev/full` manual](https://man7.org/linux/man-pages/man4/full.4.html), [`df` manual](https://man7.org/linux/man-pages/man1/df.1.html), and [`findmnt` manual](https://man7.org/linux/man-pages/man8/findmnt.8.html).
