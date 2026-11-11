# preflight.ps1 - Forge container pre-start check & cleanup
#
# Purpose: run BEFORE every container start (machine start / compose up) so that
#   disk water level, dangling images and stopped containers are handled up-front
#   instead of relying on any scheduled task.
#
# Why (2026-11-10 incident): podman machine vhdx grew to 89.8GB on a 5400rpm HDD,
#   dangling images piled up to 800+ and `podman image prune -f` blocked > 600s,
#   which dead-locked later podman calls. Preflight therefore:
#     1. ensures the podman machine is running (auto start + ready polling)
#     2. reports water level (vhdx size, host free space, system df, dangling count)
#     3. prunes stopped containers + dangling images under a hard timeout
#        (timeout -> leave the prune running in background, warn, never run other
#         podman commands in the same window)
#     4. evaluates thresholds: warn by default, abort only with -Strict
#
# Usage (from docker/):
#   powershell -ExecutionPolicy Bypass -File .\preflight.ps1
#   powershell -ExecutionPolicy Bypass -File .\preflight.ps1 -SkipStart
#   powershell -ExecutionPolicy Bypass -File .\preflight.ps1 -Strict
#   powershell -ExecutionPolicy Bypass -File .\preflight.ps1 -SkipPrune
#
# Parameters:
#   -SkipStart       do not start the machine, only inspect (read-only mode)
#   -SkipPrune       report only, no cleanup
#   -Strict          abort (exit 1) when a threshold is exceeded
#   -PruneTimeoutSec hard timeout for prune (default 180)
#   -MinFreeGB       host free space warning threshold (default 20)
#   -MaxVhdxGB       machine vhdx size warning threshold (default 45; machine disk is 50GB)
#   -MaxDangling     dangling image count warning threshold (default 100)
#
# Exit codes: 0 ok / 1 threshold breached with -Strict / 2 machine not usable

param(
    [switch]$SkipStart,
    [switch]$SkipPrune,
    [switch]$Strict,
    [int]$PruneTimeoutSec = 180,
    [int]$MinFreeGB = 20,
    [int]$MaxVhdxGB = 45,
    [int]$MaxDangling = 100
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

$ComposeFile = '.\docker-compose.yml'
$ProjectName = 'docker'
$MachineName = 'podman-machine-default'
$repoRoot    = Split-Path -Parent (Get-Location).Path
$tempDir     = Join-Path $repoRoot 'temp'
if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir -Force | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logFile = Join-Path $tempDir "preflight-$stamp.log"

$warnings = New-Object System.Collections.Generic.List[string]

function Write-Log {
    param([string]$Text, [string]$Color = 'Gray')
    Write-Host $Text -ForegroundColor $Color
    Add-Content -Path $logFile -Value $Text -Encoding UTF8
}

# Native command wrapper: PS 5.1 + ErrorActionPreference=Stop turns native stderr
# into terminating errors. Lower it locally and rely on exit codes only.
function Invoke-Native {
    param([string]$Command, [string[]]$Arguments, [switch]$Quiet)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $out = & $Command @Arguments 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message }
        else { "$_" }
    }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if (-not $Quiet) { $out | ForEach-Object { Write-Log $_ } }
    return [pscustomobject]@{ Code = $code; Out = @($out) }
}

function Get-Count {
    param($Text)
    if (-not $Text) { return 0 }
    $items = @($Text)
    if ($items.Count -eq 1) { $items = @("$($items[0])" -split "`n") }
    return @($items | Where-Object { "$_".Trim() -ne '' }).Count
}

Write-Log ''
Write-Log "=== Forge preflight  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  (branch: $(git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null)) ===" 'Cyan'

# ---------- 1. podman machine ----------
Write-Log ''
Write-Log '[1/5] podman machine'

# Probe the API first: `podman info` succeeding is the only reliable readiness
# signal. `podman machine list` Running field varies across podman versions and
# once reported "stopped" for a running machine, which then failed with
# "already running".
$apiUp = $false
$prevErr = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
podman info --format '{{.Host.Arch}}' 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { $apiUp = $true }
$ErrorActionPreference = $prevErr

if ($apiUp) {
    Write-Log "      machine '$MachineName' already serving the podman API" 'Green'
} elseif ($SkipStart) {
    Write-Log "      machine '$MachineName' is not running (-SkipStart, read-only mode)" 'Yellow'
    Write-Log '      inspection skipped: podman API unreachable' 'Yellow'
    Write-Log "      log: $logFile"
    exit 2
} else {
    Write-Log "      machine '$MachineName' stopped -> starting ..." 'Yellow'
    $r = Invoke-Native 'podman' @('machine', 'start', $MachineName)
    if ($r.Code -ne 0) {
        $joined = ($r.Out -join ' ')
        if ($joined -match 'already running') {
            Write-Log '      machine was already running (race), continue' 'Yellow'
        } else {
            Write-Log '      machine start FAILED, see output above' 'Red'
            exit 2
        }
    }
}

# poll until the podman API answers (socket may take a few seconds after start)
$ready = $false
for ($i = 1; $i -le 40; $i++) {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    podman info --format '{{.Host.Arch}}' 2>$null | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    if ($ok) { $ready = $true; break }
    Start-Sleep -Seconds 3
}
if (-not $ready) {
    Write-Log '      podman API not ready after 120s -> abort' 'Red'
    exit 2
}
Write-Log '      machine running, podman API ready' 'Green'

# ---------- 2. water level report ----------
Write-Log ''
Write-Log '[2/5] water level'

# vhdx physical size (the file on the host disk; does not shrink on its own)
$vhdxPath = $null
$prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
$inspectPath = (podman machine inspect $MachineName --format '{{.Image.Path}}' 2>$null | Select-Object -First 1)
$ErrorActionPreference = $prev
# inspect may yield an unavailable placeholder (e.g. "<no value>"), so validate on disk
if ($inspectPath -and $inspectPath.Trim() -and (Test-Path $inspectPath.Trim())) {
    $vhdxPath = $inspectPath.Trim()
} else {
    # NOTE: podman 6 InspectInfo has no Image field, so discovery falls back to
    # known locations. Wrap in @() - a single hit from the pipeline is a scalar
    # and $cand[0] would then slice the first character.
    $cand = @(@(
        "F:\podman-machine\$MachineName\ext4.vhdx",
        "F:\podman-machine\$MachineName\podman-machine-$MachineName.vhdx",
        (Join-Path $env:LOCALAPPDATA "containers\podman\machine\wsl\$MachineName\ext4.vhdx"),
        (Join-Path $env:USERPROFILE ".local\share\containers\podman\machine\$MachineName\ext4.vhdx")
    ) | Where-Object { $_ -and (Test-Path $_) })
    if ($cand.Count -gt 0) { $vhdxPath = $cand[0] }
}

$vhdxGB = $null
if ($vhdxPath -and (Test-Path $vhdxPath)) {
    $vhdxGB = [math]::Round((Get-Item $vhdxPath).Length / 1GB, 2)
    $drive = (Get-Item $vhdxPath).PSDrive.Name
    $freeGB = [math]::Round((Get-PSDrive $drive).Free / 1GB, 2)
    Write-Log ("      vhdx : {0}  ({1} GB)  [drive {2}: free {3} GB]" -f $vhdxPath, $vhdxGB, $drive, $freeGB)
    if ($vhdxGB -gt $MaxVhdxGB) {
        $warnings.Add("vhdx ${vhdxGB}GB > ${MaxVhdxGB}GB (needs offline compaction; vhdx never shrinks by itself)") | Out-Null
    }
    if ($freeGB -lt $MinFreeGB) {
        $warnings.Add("${drive}: free ${freeGB}GB < ${MinFreeGB}GB") | Out-Null
    }
} else {
    Write-Log '      vhdx : not found (skipped)' 'Yellow'
}

# inside-machine usage
$prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
$df = podman system df --format '{{.Type}}|{{.Total}}|{{.Size}}|{{.Reclaimable}}' 2>$null
$ErrorActionPreference = $prev
if ($df) {
    foreach ($line in @($df)) { if ($line.Trim()) { Write-Log "      $($line.Trim())" } }
} else {
    Write-Log '      podman system df unavailable' 'Yellow'
}

$prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
$dangling = podman images -f dangling=true --format '{{.ID}}' 2>$null
$stopped = podman ps -a --filter status=exited --filter status=created --format '{{.ID}}' 2>$null
$ErrorActionPreference = $prev
$danglingCount = Get-Count $dangling
$stoppedCount = Get-Count $stopped
Write-Log "      dangling images: $danglingCount   stopped containers: $stoppedCount"
if ($danglingCount -gt $MaxDangling) {
    $warnings.Add("dangling images $danglingCount > $MaxDangling") | Out-Null
}

# ---------- 3. cleanup ----------
Write-Log ''
if ($SkipPrune) {
    Write-Log '[3/5] cleanup skipped (-SkipPrune)' 'Yellow'
} else {
    Write-Log '[3/5] cleanup'

    if ($stoppedCount -gt 0) {
        $r = Invoke-Native 'podman' @('container', 'prune', '-f') -Quiet
        Write-Log "      container prune -> exit $($r.Code): $(($r.Out | Select-Object -Last 1))"
    } else {
        Write-Log '      container prune -> nothing to do'
    }

    if ($danglingCount -gt 0) {
        # Hard timeout: a large dangling backlog once blocked >600s and held the
        # podman API lock, so no other podman command may run in this window.
        # The exit code is echoed by cmd into the log: PowerShell 5.1 does not
        # populate Process.ExitCode for detached Start-Process children here.
        $pruneLog = Join-Path $tempDir "preflight-prune-$stamp.log"
        $inner = 'podman image prune -f > "' + $pruneLog + '" 2>&1 & echo FORGE_PRUNE_EXIT:%ERRORLEVEL%>>"' + $pruneLog + '"'
        $proc = Start-Process -FilePath 'cmd' -ArgumentList "/c $inner" -NoNewWindow -PassThru
        $finished = $proc.WaitForExit($PruneTimeoutSec * 1000)
        if (-not $finished) {
            Write-Log "      image prune still running after ${PruneTimeoutSec}s (pid $($proc.Id))" 'Yellow'
            Write-Log "        -> left in background; do NOT issue other podman commands until it ends" 'Yellow'
            Write-Log "        -> prune log: $pruneLog" 'Yellow'
            $warnings.Add("image prune exceeded ${PruneTimeoutSec}s, still running in background") | Out-Null
        } else {
            $pruneExit = 'unknown'
            $lastLine = ''
            if (Test-Path $pruneLog) {
                $lines = @(Get-Content $pruneLog -Encoding UTF8)
                $marker = $lines | Where-Object { $_ -match 'FORGE_PRUNE_EXIT:(\d+)' } | Select-Object -Last 1
                if ($marker -and $marker -match 'FORGE_PRUNE_EXIT:(\d+)') { $pruneExit = $matches[1] }
                $lastLine = ($lines | Where-Object { $_ -notmatch 'FORGE_PRUNE_EXIT' } | Select-Object -Last 1)
            }
            Write-Log "      image prune -> exit ${pruneExit}: $lastLine"

            # re-check after prune (only safe once the prune process has finished)
            $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
            $dangling2 = podman images -f dangling=true --format '{{.ID}}' 2>$null
            $ErrorActionPreference = $prev
            $danglingLeft = Get-Count $dangling2
            Write-Log "      dangling images after prune: $danglingLeft"
            if ($danglingLeft -gt 0) {
                Write-Log '      note: leftovers are shared layers of --no-cache builds, not reclaimable' 'DarkGray'
            }
        }
    } else {
        Write-Log '      image prune -> nothing to do'
    }
}

# ---------- 4. thresholds ----------
Write-Log ''
Write-Log '[4/5] verdict'
if ($warnings.Count -eq 0) {
    Write-Log '      OK, no threshold breached' 'Green'
    $verdict = 0
} else {
    foreach ($w in $warnings) { Write-Log "      WARN  $w" 'Yellow' }
    if ($Strict) {
        Write-Log '      -Strict: aborting before container start' 'Red'
        $verdict = 1
    } else {
        Write-Log '      continue (use -Strict to abort instead)' 'Yellow'
        $verdict = 0
    }
}

# ---------- 5. summary ----------
Write-Log ''
Write-Log '[5/5] summary'
$prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
$ps = podman ps --format '{{.Names}}|{{.Status}}' 2>$null
$ErrorActionPreference = $prev
$runningCount = Get-Count $ps
Write-Log "      running containers: $runningCount"
if ($ps) { foreach ($line in @($ps)) { if ($line.Trim()) { Write-Log "        $($line.Trim())" } } }
Write-Log "      log: $logFile"
Write-Log ''

exit $verdict
