# up.ps1 - single entry point for starting the Forge stack
#
# Always runs preflight.ps1 first (machine auto-start + water level + dangling
# cleanup), then `podman-compose up -d`, then prints a status table.
# Never call `podman-compose up -d` by hand: the pre-start check is the contract.
#
# Usage (from docker/):
#   powershell -ExecutionPolicy Bypass -File .\up.ps1
#   powershell -ExecutionPolicy Bypass -File .\up.ps1 -Service backend,gateway
#   powershell -ExecutionPolicy Bypass -File .\up.ps1 -Smoke
#   powershell -ExecutionPolicy Bypass -File .\up.ps1 -NoPreflight      # emergency skip
#
# Parameters:
#   -Service        subset of services; default = whole stack
#   -Smoke          HTTP smoke check after start
#   -NoPreflight    skip preflight (emergency only)
#   -Strict         pass through to preflight (abort on threshold breach)
#
# Exit codes: 0 ok / 1 preflight aborted / 2 compose failed

param(
    [string[]]$Service = @(),
    [switch]$Smoke,
    [switch]$NoPreflight,
    [switch]$Strict
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

$ComposeFile = '.\docker-compose.yml'
$ProjectName = 'docker'

function Write-Step {
    param([string]$Text, [string]$Color = 'Cyan')
    Write-Host ''
    Write-Host $Text -ForegroundColor $Color
}

# ---------- 1. preflight ----------
if (-not $NoPreflight) {
    Write-Step '[0/3] preflight (machine + water level + cleanup)'
    $pfArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PWD 'preflight.ps1'))
    if ($Strict) { $pfArgs += '-Strict' }
    & powershell @pfArgs
    $pfCode = $LASTEXITCODE
    if ($pfCode -eq 1) {
        Write-Host 'preflight aborted (-Strict threshold breach), container start cancelled.' -ForegroundColor Red
        exit 1
    }
    if ($pfCode -eq 2) {
        Write-Host 'preflight could not bring the podman machine up, container start cancelled.' -ForegroundColor Red
        exit 1
    }
} else {
    Write-Step '[0/3] preflight skipped (-NoPreflight)' 'Yellow'
}

# ---------- 2. compose up ----------
Write-Step '[1/3] podman-compose up -d'
$composeArgs = @('--project-name', $ProjectName, '-f', $ComposeFile, 'up', '-d')
if ($Service.Count -gt 0) { $composeArgs += $Service }

$prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
& podman-compose @composeArgs 2>&1 | ForEach-Object {
    if ($_ -is [System.Management.Automation.ErrorRecord]) { Write-Host $_.Exception.Message -ForegroundColor DarkYellow }
    else { Write-Host $_ }
}
$code = $LASTEXITCODE
$ErrorActionPreference = $prev
if ($code -ne 0) {
    Write-Host "podman-compose up failed (exit $code)" -ForegroundColor Red
    exit 2
}

# ---------- 3. status ----------
Write-Step '[2/3] container status'
Start-Sleep -Seconds 5
$prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
podman ps -a --format '{{.Names}}|{{.Status}}|{{.Ports}}' 2>&1 | ForEach-Object {
    if ($_ -is [System.Management.Automation.ErrorRecord]) { Write-Host $_.Exception.Message -ForegroundColor DarkYellow }
    else { Write-Host "  $_" }
}
$ErrorActionPreference = $prev

Write-Step '[3/3] access list'
Write-Host '  admin      http://127.0.0.1:8080/    (Ctrl+Shift+R hard refresh; localhost/IPv6 may time out)'
Write-Host '  backend    http://127.0.0.1:8002/health  + /docs'
Write-Host '  ai-service http://127.0.0.1:8001/health'
Write-Host '  portal-web http://127.0.0.1:3000/'
Write-Host '  gateway    http://127.0.0.1:8080/'

# ---------- optional smoke ----------
if ($Smoke) {
    Write-Step 'smoke check'
    $targets = @(
        @{ Name = 'backend';    Url = 'http://127.0.0.1:8002/health' },
        @{ Name = 'ai-service'; Url = 'http://127.0.0.1:8001/health' },
        @{ Name = 'portal-web'; Url = 'http://127.0.0.1:3000/' },
        @{ Name = 'gateway';    Url = 'http://127.0.0.1:8080/' }
    )
    $fail = 0
    foreach ($t in $targets) {
        $status = 0
        for ($i = 0; $i -lt 12; $i++) {
            try {
                $r = Invoke-WebRequest -Uri $t.Url -UseBasicParsing -TimeoutSec 8
                $status = $r.StatusCode
                if ($status -eq 200) { break }
            } catch { $status = 0 }
            Start-Sleep -Seconds 5
        }
        if ($status -eq 200) { Write-Host ("  [OK]   {0,-11} {1}" -f $t.Name, $t.Url) -ForegroundColor Green }
        else { Write-Host ("  [FAIL] {0,-11} {1} -> {2}" -f $t.Name, $t.Url, $status) -ForegroundColor Red; $fail++ }
    }
    if ($fail -gt 0) {
        Write-Host "smoke check: $fail endpoint(s) failed" -ForegroundColor Red
        exit 3
    }
}

Write-Host ''
Write-Host 'done.' -ForegroundColor Green
exit 0
