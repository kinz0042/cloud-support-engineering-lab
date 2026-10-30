# Check the first incident's real process and curl.exe commands on disposable CI.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) {
    throw 'This helper is intended only for a disposable GitHub Actions runner.'
}

$work = Join-Path $env:RUNNER_TEMP ('relay-foundation-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
$server = $null

function Assert-Response($Lines, [int]$Expected, [string]$Name) {
    $response = $Lines -join "`n"
    if ($response -notmatch "(?m)^HTTP/\S+\s+$Expected(?:\s|$)") {
        throw "$Name did not return HTTP $Expected."
    }
    if ($response -notmatch '(?im)^X-Request-ID:\s+\S+') {
        throw "$Name did not return a request ID."
    }
}

try {
    # The fixed port mirrors the documented first exercise. Never stop a different process.
    $listener = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if ($listener) { throw 'Port 8080 is occupied on the CI runner.' }
    $python = (Get-Command python -CommandType Application).Source
    $server = Start-Process -FilePath $python -ArgumentList 'app/server.py' -PassThru -NoNewWindow `
        -RedirectStandardOutput (Join-Path $work 'server.out') `
        -RedirectStandardError (Join-Path $work 'server.err')
    $healthy = $false
    for ($i = 0; $i -lt 40; $i++) {
        $server.Refresh()
        if ($server.HasExited) { throw 'Foundation server exited before becoming ready.' }
        $health = & curl.exe -s -i --max-time 2 http://127.0.0.1:8080/health
        if ($LASTEXITCODE -eq 0 -and (($health -join "`n") -match '(?m)^HTTP/\S+\s+200\b')) {
            $healthy = $true
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $healthy) { throw 'Foundation server did not become healthy.' }
    $server.Refresh()
    if ($server.HasExited) { throw 'Foundation server stopped unexpectedly.' }
    Assert-Response $health 200 'Health'

    $bad = & curl.exe -sS -i --max-time 3 http://127.0.0.1:8080/v1/orders -H 'Authorization: lab-demo-token-not-a-secret'
    if ($LASTEXITCODE -ne 0) { throw 'Malformed-credential request failed to reach the local server.' }
    Assert-Response $bad 401 'Malformed credential'

    $good = & curl.exe -sS -i --max-time 3 http://127.0.0.1:8080/v1/orders -H 'Authorization: Bearer lab-demo-token-not-a-secret'
    if ($LASTEXITCODE -ne 0) { throw 'Corrected-credential request failed to reach the local server.' }
    Assert-Response $good 200 'Corrected credential'
    if (($good -join "`n") -notmatch '"orders"') { throw 'Successful response did not contain orders.' }

    $missing = & curl.exe -sS -i --max-time 3 http://127.0.0.1:8080/v1/orders
    if ($LASTEXITCODE -ne 0) { throw 'Missing-credential control failed to reach the local server.' }
    Assert-Response $missing 401 'Missing credential control'
    Write-Host 'Windows PowerShell and curl.exe: health 200; malformed credential 401; corrected credential 200; missing credential 401; request IDs present.'
}
finally {
    if ($server) {
        $server.Refresh()
        if (-not $server.HasExited) { Stop-Process -Id $server.Id -ErrorAction SilentlyContinue }
    }
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
