# Linux service troubleshooting lab

This optional lab runs a small synthetic status service under a **transient systemd unit**. It is separate from the Docker application; it does not represent a deployed customer agent. The service binds only to `127.0.0.1` and has one `/health` endpoint. Its successful startup log includes the synthetic instance ID and port; invalid configuration values and unrelated environment variables are not echoed. Never put a secret in the instance ID.

The exercises reproduce a missing configuration value and an occupied listening port. They use `systemctl`, `journalctl`, process identity and socket inspection, then validate recovery. A fresh GitHub-hosted Ubuntu runner has exercised the service manager and journal; this does not establish compatibility with the learner's laptop or WSL installation.

## Requirements and boundaries

Use a disposable or appropriately authorized Linux environment with systemd as its system service manager, Python 3, `curl`, and permission to use `sudo`. `ss` is useful for the port investigation. Check first:

```bash
ps -p 1 -o comm=
command -v systemd-run
command -v systemctl
command -v journalctl
command -v python3
command -v curl
command -v ss
```

The commands below expect an ordinary unprivileged login and Bash, from the repository root. The transient unit runs as that login, not as root; `sudo` is used to ask the system service manager to create and control only the named lab units. The units are not enabled at boot and no permanent unit file is installed. Running these commands on a shared or production server is outside the lab scope. A Windows machine needs a suitable Linux environment for this optional exercise; WSL and the learner's laptop have not been verified here.

## 1. Reproduce the configuration failure

Keep the same Bash terminal open so the `LAB_*` variables remain available. Choose a currently free loopback port; there is a small race between selecting the port and binding it.

```bash
LAB_REPO="$(pwd -P)"
LAB_DIR="$(mktemp -d /tmp/relaydesk-systemd.XXXXXX)"
LAB_UNIT="relaydesk-lab-$(date +%s)-$$.service"
LAB_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
printf 'RELAY_LAB_INSTANCE=\nRELAY_LAB_PORT=%s\n' "$LAB_PORT" > "$LAB_DIR/alpha.env"
printf 'Unit: %s  Port: %s\n' "$LAB_UNIT" "$LAB_PORT"
sudo systemd-run --unit="$LAB_UNIT" --service-type=exec \
  --property=Restart=no --property=NoNewPrivileges=yes \
  --property="User=$(id -un)" --property="EnvironmentFile=$LAB_DIR/alpha.env" \
  /usr/bin/python3 "$LAB_REPO/linux/status_service.py"
```

The unit can be created successfully even though the process exits shortly afterward. Give it a moment, then collect evidence:

```bash
sudo systemctl status "$LAB_UNIT" --no-pager -l
sudo systemctl show "$LAB_UNIT" -p ActiveState -p ExecMainStatus -p MainPID
sudo journalctl -u "$LAB_UNIT" -n 50 --no-pager -o cat
```

The lab process exits with status `2` and logs `configuration_error` with reason `missing_instance`. It does not echo the bad value. `systemctl status` normally returns a nonzero command status for a failed service; that is evidence, not a reason to repeat changes blindly. Compare hypotheses: missing configuration, missing executable, port conflict and host networking. The reason in the unit's journal is one clue; corroborate it against the synthetic configuration without publishing secret values.

Correct the lab value and restart the same unit:

```bash
printf 'RELAY_LAB_INSTANCE=alpha-demo\nRELAY_LAB_PORT=%s\n' "$LAB_PORT" > "$LAB_DIR/alpha.env"
sudo systemctl restart "$LAB_UNIT"
sudo systemctl is-active "$LAB_UNIT"
curl --fail --silent --show-error "http://127.0.0.1:$LAB_PORT/health"
```

The configuration file is read at service start; editing it does not change an already running process. A successful restart should produce `active` and a health response identifying `alpha-demo`. If the request arrives before the listener is ready, wait briefly and repeat the health check. Preserve timestamps, the exit status, journal evidence and validation in [INC-018](../incidents/INC-018/brief.md).

## 2. Reproduce the port conflict

With the first service still healthy in the same terminal, start a second unit on the **same** port:

```bash
LAB_SECOND="${LAB_UNIT%.service}-second.service"
printf 'RELAY_LAB_INSTANCE=bravo-demo\nRELAY_LAB_PORT=%s\n' "$LAB_PORT" > "$LAB_DIR/bravo.env"
sudo systemd-run --unit="$LAB_SECOND" --service-type=exec \
  --property=Restart=no --property=NoNewPrivileges=yes \
  --property="User=$(id -un)" --property="EnvironmentFile=$LAB_DIR/bravo.env" \
  /usr/bin/python3 "$LAB_REPO/linux/status_service.py"
sudo systemctl status "$LAB_SECOND" --no-pager -l
sudo journalctl -u "$LAB_SECOND" -n 50 --no-pager -o cat
sudo ss -ltnp "sport = :$LAB_PORT"
sudo systemctl show "$LAB_UNIT" -p MainPID
```

On Linux the second process exits with status `1` and emits `listen_failed` with `address_in_use` and the operating-system error number. The first service still responds as `alpha-demo`. Compare its `MainPID` with the listening process where `ss` shows an owner; socket tools or privileges can affect whether the process name is displayed. A bind failure at startup is distinct from a firewall blocking traffic to an already listening process.

For this deliberately owned conflict, stop only the first lab unit, then retry the second:

```bash
sudo systemctl stop "$LAB_UNIT"
sudo systemctl restart "$LAB_SECOND"
sudo systemctl is-active "$LAB_SECOND"
curl --fail --silent --show-error "http://127.0.0.1:$LAB_PORT/health"
```

Validate that the response now identifies `bravo-demo`, the second unit is active and the original unit no longer owns the listener. A real system may need a different approved port or coordination with another service owner; never terminate an unknown process merely to free a port. Record your own evidence in [INC-019](../incidents/INC-019/brief.md).

## Clean up the lab

Run the following in the same terminal. It acts only on the generated `relaydesk-lab-*` unit names:

```bash
for LAB_CLEANUP_UNIT in "${LAB_SECOND:-}" "${LAB_UNIT:-}"; do
  case "$LAB_CLEANUP_UNIT" in
    relaydesk-lab-*.service)
      if sudo systemctl is-active --quiet "$LAB_CLEANUP_UNIT"; then
        sudo systemctl stop "$LAB_CLEANUP_UNIT"
      fi
      sudo systemctl reset-failed "$LAB_CLEANUP_UNIT" 2>/dev/null || true
      ;;
  esac
done
sudo systemctl list-units 'relaydesk-lab-*' --all
```

Verify that the generated units are no longer active. A transient unit may already have been unloaded after stopping. Then remove the two disposable configuration files:

```bash
case "${LAB_DIR:-}" in
  /tmp/relaydesk-systemd.*) rm -f -- "$LAB_DIR/alpha.env" "$LAB_DIR/bravo.env"; rmdir -- "$LAB_DIR";;
  *) printf 'Lab directory not identified; inspect manually.\n';;
esac
```

Do not delete unrelated files, stop unrelated services, or publish real environment files.

## Verification and limitations

The standalone service has process/socket tests that passed on a [Windows Server runner](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/41017578989); this check does not run systemd. `scripts/systemd_smoke.py` is designed for a disposable GitHub Actions Linux runner: it creates unique transient units, reproduces both failures, checks the journal and exit codes, verifies health after recovery, and stops only its own units. Its `GITHUB_ACTIONS` environment check is not proof that a machine is disposable; do not set that flag to run it on a valuable host. See each incident's verification link for the actual run. This is not a test of every Linux distribution, WSL release or the user's laptop, and these synthetic exercises are not employment experience.

References: [systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html) and [systemd service configuration](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).
