# Windows setup and first checks

This guide is for the local, synthetic RelayDesk lab. Docker Desktop support depends on your Windows version, virtualization and Docker's current requirements. Do not assume it will run on every Windows installation. The Python foundation works separately and does not require Docker or VirtualBox.

## Check prerequisites

Open PowerShell in the repository folder:

```powershell
git --version
python --version
docker version
docker compose version
```

You can also run `powershell -ExecutionPolicy Bypass -File .\scripts\windows-check.ps1` for a read-only check. If Python is installed as `py`, use `py` in place of `python`. If Docker's client appears but its server does not, start Docker Desktop and retry. Do not change virtualization or Windows security settings blindly; identify the exact error first.

## Start the Docker lab

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:8081/health
Invoke-RestMethod http://127.0.0.1:8081/ready
```

Give the database time to become healthy. If readiness fails, inspect `docker compose logs --tail=50 db api`; do not share credentials or full connection strings.

Create a synthetic order without shell-escaping JSON:

```powershell
$headers = @{ Authorization = 'Bearer acme-local-key' }
$body = @{ external_id = "windows-$([guid]::NewGuid())" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8081/v1/orders -Headers $headers -ContentType 'application/json' -Body $body
docker compose logs --tail=50 worker partner
```

The key is public and only for this isolated lab. An accepted order does not prove delivery. Inspect delivery state with:

```powershell
docker compose exec db psql -U lab -d relaydesk -c 'SELECT id,order_id,state,attempts,last_error FROM deliveries;'
```

Stop the stack with `docker compose down`. This retains the database volume; `down -v` removes it and should only be used when you deliberately want to discard disposable lab data.

## Common checks

- Port 8081 busy: identify the process using `Get-NetTCPConnection -LocalPort 8081` and resolve the conflict before starting.
- Database unhealthy: inspect database logs and check available disk space; never publish passwords or database URLs.
- Build or image download fails: record the exact message and check connectivity and Docker engine status.
- A stale partner fault mode can persist in your PowerShell session. Inspect `$env:LAB_PARTNER_MODE`; remove it with `Remove-Item Env:LAB_PARTNER_MODE -ErrorAction SilentlyContinue` and recreate the partner when returning to the default mode.

The PowerShell prerequisite script passed a syntax check and foundation triage tests passed on a [GitHub-hosted Windows runner](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40964603583). The full setup and Docker commands have not yet been tested on the learner's laptop. Do not treat this document as evidence that Docker Desktop runs on that machine.
