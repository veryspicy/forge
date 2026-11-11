<#
.SYNOPSIS
Resolve the local proxy port from the v2rayN config file instead of hardcoding it.

.DESCRIPTION
v2rayN/xray rotates its inbound port when the previously configured port is
occupied, so any hardcoded port (10808 / 10809 / 10911 / 11133 ...) eventually
goes stale and every git/gh call fails with
"Failed to connect ... over proxy 127.0.0.1".

The authoritative source is the v2rayN GUI config:
    <v2rayN>\guiConfigs\guiNConfig.json  ->  .inbound[0].localPort
The generated runtime config shows the same value with protocol "mixed",
which means the port serves HTTP and SOCKS on the same listener, so
"http://127.0.0.1:<port>" and "socks5://127.0.0.1:<port>" both work.

.WORKFLOW
1. Locate guiNConfig.json: -GuiConfig path > running v2rayN process dir >
   common install dirs on C:/D:/E:.
2. Read .inbound[0].localPort and protocol.
3. Warn (not fail) when the port is not actually listening, so the caller can
   tell "config stale / core not started" apart from "wrong port".
4. With -Apply, write http.proxy/https.proxy into the git repo config so that
   scripts which shell out to git (merge-dev.ps1 etc.) inherit the right proxy.

.PARAMETER GuiConfig
Explicit path to guiNConfig.json. Skips auto-discovery.

.PARAMETER Apply
Write http.proxy / https.proxy into the target git repository config.

.PARAMETER RepoPath
Git repo to apply the proxy to. Default: current directory.

.PARAMETER Quiet
Only print the port number (machine friendly, for scripts).

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/get-proxy-port.ps1

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/get-proxy-port.ps1 -Apply -RepoPath D:\codeRepo\forge
#>
param(
    [string]$GuiConfig,
    [switch]$Apply,
    [string]$RepoPath = (Get-Location).Path,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

function Write-Info {
    param([string]$Msg)
    if (-not $Quiet) { Write-Host "[proxy] $Msg" }
}

function Find-GuiConfig {
    param([string]$Explicit)
    if ($Explicit) {
        if (Test-Path $Explicit) { return (Resolve-Path $Explicit).Path }
        throw "guiNConfig.json not found at '$Explicit'."
    }
    $candidates = @()
    $proc = Get-Process -Name 'v2rayN' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($proc -and $proc.Path) {
        $candidates += (Join-Path (Split-Path $proc.Path -Parent) 'guiConfigs\guiNConfig.json')
    }
    foreach ($drive in @('C:', 'D:', 'E:', 'F:')) {
        $candidates += "$drive\Program Files\v2rayN-windows-64\guiConfigs\guiNConfig.json"
        $candidates += "$drive\Program Files\v2rayN\guiConfigs\guiNConfig.json"
        $candidates += "$drive\v2rayN\guiConfigs\guiNConfig.json"
        $candidates += "$drive\Tools\v2rayN\guiConfigs\guiNConfig.json"
    }
    foreach ($c in $candidates) {
        if (Test-Path $c) { return (Resolve-Path $c).Path }
    }
    throw 'guiNConfig.json not found. Pass -GuiConfig <path to v2rayN\guiConfigs\guiNConfig.json>.'
}

$path = Find-GuiConfig -Explicit $GuiConfig
$cfg = Get-Content -Path $path -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $cfg.inbound -or $cfg.inbound.Count -eq 0) {
    throw "No inbound entries in '$path'. Start v2rayN once so the config gets written."
}

$inbound = $cfg.inbound[0]
$port = [int]$inbound.localPort
if ($port -le 0) { throw "Invalid localPort '$($inbound.localPort)' in '$path'." }

Write-Info "config : $path"
Write-Info "inbound: protocol=$($inbound.protocol) localPort=$port"

$listening = $false
try {
    $conn = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -eq $port } | Select-Object -First 1
    if ($conn) { $listening = $true }
} catch {
    Write-Info "listener check skipped: $_"
}
if (-not $listening) {
    Write-Warning "Port $port is in the config but nothing is listening on it. v2rayN core is probably not running (or it failed to bind because the port is occupied) - start v2rayN and re-run."
} else {
    Write-Info "listener: OK (something is listening on 127.0.0.1:$port)"
}

$url = "http://127.0.0.1:$port"
Write-Info "env    : `$env:HTTPS_PROXY='$url'; `$env:HTTP_PROXY='$url'; `$env:NO_PROXY='localhost,127.0.0.1,::1'"
Write-Info "git    : git -c http.proxy=$url -c https.proxy=$url <command>"

if ($Apply) {
    if (-not (Test-Path (Join-Path $RepoPath '.git'))) {
        throw "'$RepoPath' is not a git repository root (no .git)."
    }
    Push-Location $RepoPath
    try {
        git config http.proxy $url
        if ($LASTEXITCODE -ne 0) { throw 'git config http.proxy failed.' }
        git config https.proxy $url
        if ($LASTEXITCODE -ne 0) { throw 'git config https.proxy failed.' }
        Write-Info "applied: repo '$RepoPath' http.proxy/https.proxy = $url"
    } finally {
        Pop-Location
    }
}

if ($Quiet) { Write-Output $port }
