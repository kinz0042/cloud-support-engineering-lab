"""Safely reproduce Linux ENOSPC and a disposable write recovery.

The fault uses /dev/full and does not consume disk capacity. No user path is accepted.
"""
import argparse
import errno
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

PAYLOAD = b'{"event":"synthetic_write"}\n'


def write_once(fd, fixture):
    try:
        count = os.write(fd, PAYLOAD)
    except OSError as exc:
        return 1, {"event": "write_failed", "fixture": fixture, "errno": exc.errno,
                   "reason": "no_space" if exc.errno == errno.ENOSPC else "other_io_error"}
    if count != len(PAYLOAD):
        return 1, {"event": "write_failed", "fixture": fixture, "reason": "short_write"}
    return 0, {"event": "write_succeeded", "fixture": fixture, "bytes": count}


def fault():
    if not sys.platform.startswith("linux") or not hasattr(os, "O_NOFOLLOW"):
        return 2, {"event": "fixture_unavailable", "fixture": "linux_dev_full"}
    fd = None
    try:
        # Open only the real Linux /dev/full character device, never a user-selected path.
        fd = os.open("/dev/full", os.O_WRONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
        info = os.fstat(fd)
        if not stat.S_ISCHR(info.st_mode) or info.st_rdev != os.makedev(1, 7):
            return 2, {"event": "fixture_unavailable", "fixture": "linux_dev_full"}
        return write_once(fd, "linux_dev_full")
    except OSError as exc:
        return 2, {"event": "fixture_unavailable", "fixture": "linux_dev_full", "errno": exc.errno}
    finally:
        if fd is not None:
            os.close(fd)


def recovery():
    try:
        with tempfile.TemporaryDirectory(prefix="relaydesk-enospc-") as directory:
            path = Path(directory) / "synthetic-event.json"
            with path.open("xb", buffering=0) as handle:
                status, event = write_once(handle.fileno(), "temporary_file")
            if status:
                return status, event
            if path.read_bytes() != PAYLOAD:
                return 1, {"event": "validation_failed", "fixture": "temporary_file"}
            return 0, {**event, "readback_verified": True}
    except OSError as exc:
        return 1, {"event": "recovery_failed", "fixture": "temporary_file", "errno": exc.errno}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("fault", "recovery"))
    args = parser.parse_args()
    status, result = fault() if args.mode == "fault" else recovery()
    print(json.dumps(result, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
