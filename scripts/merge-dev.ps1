<#
.SYNOPSIS
Automated merge of a feature/fix branch into dev with code review gate + CI health check.

.WORKFLOW
1. Run scripts/code-review-gate.ps1 -Base dev  (blockers => abort, nothing changed)
2. Fast-forward dev to origin/dev, then merge branch with --no-ff
3. Push dev to origin
4. Poll GitHub Actions for the dev push; fail loudly if the run is not green

.RULES
docs/DEV-RULES.md 1.3 (user verification gate is manual; this script only checks the
mechanical/CI gates), 1.4 (CI health required before merge is considered done).

.PARAMETER Branch
Branch to merge into dev. Default: current branch.

.PARAMETER SkipPush
Do not push after merge (local merge only).

.PARAMETER CiTimeoutSec
Seconds to poll CI before giving up (default 900).

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/merge-dev.ps1
#>
param(
    [string]$Branch = (git branch --show-current),
    [switch]$SkipPush,
    [int]$CiTimeoutSec = 900
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Fail {
    param([string]$Msg)
    Write-Host "[merge-dev] FAILED: $Msg" -ForegroundColor Red
    exit 1
}

function Get-GitHubToken {
    # Read PAT from git credential manager (same channel git uses)
    $inputLines = "protocol=https`nhost=github.com`n"
    $out = $inputLines | git credential fill 2>$null
    $pw = ($out | Where-Object { $_ -like 'password=*' }) -replace '^password=', ''
    if (-not $pw) { return $null }
    return $pw.Trim()
}

if (-not $Branch) { Fail 'Cannot determine branch.' }
if ($Branch -eq 'dev') { Fail "Refusing to merge 'dev' into itself. Run from the feature branch." }

Write-Host "[merge-dev] Target: $Branch -> dev"

# ---------- gate ----------
Write-Host '[merge-dev] Running code review gate...'
& (Join-Path $PSScriptRoot 'code-review-gate.ps1') -Base dev
if ($LASTEXITCODE -ne 0) {
    Fail 'Code review gate reported blockers. Merge aborted (nothing changed).'
}
Write-Host '[merge-dev] Gate passed.' -ForegroundColor Green

# ---------- sync & merge ----------
git fetch origin 2>&1 | Out-Host
$localDev = git rev-parse dev
$originDev = git rev-parse origin/dev
if ($localDev -ne $originDev) {
    Write-Host "[merge-dev] Fast-forwarding local dev to origin/dev ($($originDev.Substring(0,7)))..."
    git checkout dev | Out-Host
    git merge --ff-only origin/dev 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { Fail 'Could not fast-forward dev to origin/dev.' }
}
git checkout dev | Out-Host
git merge --no-ff $Branch -m "Merge $Branch into dev" 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host '[merge-dev] Merge conflicts detected. Resolve manually, do NOT run merge-dev again.' -ForegroundColor Yellow
    Fail 'Merge conflict. See git status.'
}

$mergeSha = git rev-parse HEAD
Write-Host "[merge-dev] Merged at $($mergeSha.Substring(0,7))"

if ($SkipPush) {
    Write-Host '[merge-dev] -SkipPush: not pushing.' -ForegroundColor Yellow
    exit 0
}

# ---------- push ----------
Write-Host '[merge-dev] Pushing dev to origin...'
git push origin dev 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Fail 'Push to origin/dev failed.' }

# ---------- CI health check ----------
$token = Get-GitHubToken
if (-not $token) {
    Write-Host '[merge-dev] No GitHub token available via git credential; CI check skipped. Verify run status in Actions UI.' -ForegroundColor Yellow
    exit 0
}

$headers = @{ Authorization = "Bearer $token"; 'User-Agent' = 'forge-merge-dev' }
Write-Host "[merge-dev] Polling GitHub Actions (timeout ${CiTimeoutSec}s)..."
$deadline = (Get-Date).AddSeconds($CiTimeoutSec)
$lastStatus = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 15
    try {
        $runs = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/veryspicy/forge/actions/runs?event=push&branch=dev&per_page=5"
        $run = $runs.workflow_runs | Where-Object { $_.head_sha -eq $mergeSha } | Select-Object -First 1
        if ($run) {
            $lastStatus = $run.status
            if ($run.status -eq 'completed') {
                if ($run.conclusion -eq 'success') {
                    Write-Host "[merge-dev] CI green for $($mergeSha.Substring(0,7)) ($($run.conclusion))." -ForegroundColor Green
                    Write-Host '[merge-dev] NOTE: per DEV-RULES 1.3, keep the branch PR open until you verify the change manually.' -ForegroundColor Yellow
                    exit 0
                } else {
                    Fail "CI run $($run.html_url) conclusion=$($run.conclusion). Merge not verified - do not delete branch."
                }
            }
        }
    } catch {
        Write-Host "[merge-dev] CI poll warning: $_" -ForegroundColor Yellow
    }
    Write-Host "[merge-dev] ... CI still $(if ($null -eq $lastStatus) { 'pending' } else { $lastStatus }) ($(($deadline - (Get-Date)).TotalSeconds.ToString('0'))s left)"
}
Fail "CI did not finish within ${CiTimeoutSec}s. Verify run status in Actions UI before proceeding."
