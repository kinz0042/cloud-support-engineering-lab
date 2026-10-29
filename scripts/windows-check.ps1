# Read-only prerequisite checks; no installation or changes to Docker configuration.
$ErrorActionPreference = 'Continue'
Write-Host 'RelayDesk prerequisite check'
Write-Host "PowerShell: $($PSVersionTable.PSVersion)"
foreach ($name in @('git', 'python', 'docker')) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { Write-Host "${name}: available ($($cmd.Source))" }
    else { Write-Host "${name}: not found in PATH" }
}
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker version --format 'Client: {{.Client.Version}}; Server: {{.Server.Version}}'
    if ($LASTEXITCODE -ne 0) { Write-Host 'Docker engine is not reachable. Start Docker Desktop and retry.' }
    docker compose version
}
Write-Host 'This check does not verify virtualization support, compatibility or available memory.'
