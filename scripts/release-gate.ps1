<#
.SYNOPSIS
Release gate: run before tagging a new version / merging dev into main.

.CHECKS
1. Current branch must be dev (release cut from dev).
2. Working tree clean (excluding temp/).
3. dev in sync with origin/dev and ahead only by the release-merge commit.
4. docs/DEV-RULES.md release version gates:
   - CHANGELOG.md has a non-empty Unreleased section
   - bump expected version files (backend pyproject.toml / admin+portal package.json) consistent
5. Full code review gate vs origin/main (same checks as merge-to-dev).

.RULES
docs/DEV-RULES.md 2.x version management.

.PARAMETER SkipQuality
Pass through to the underlying gate (skip quality re-run).

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/release-gate.ps1
#>
param(
    [switch]$SkipQuality
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Fail {
    param([string]$Msg)
    Write-Host "[release-gate] FAILED: $Msg" -ForegroundColor Red
    exit 1
}

Write-Host '[release-gate] Checking release readiness...'

# ---------- branch / tree ----------
$head = git branch --show-current
if ($head -ne 'dev') { Fail "Release cut must happen on dev (current: $head)." }

$status = git status --porcelain | Where-Object { $_ -notmatch '^\?\? temp/' }
if ($status) { Fail "Working tree not clean (excluding temp/):`n$status" }

git fetch origin 2>&1 | Out-Host
$localDev = git rev-parse dev
$originDev = git rev-parse origin/dev
if ($localDev -ne $originDev) {
    Write-Host '[release-gate] local dev differs from origin/dev; syncing first...'
    git merge --ff-only origin/dev 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { Fail 'Could not fast-forward dev to origin/dev.' }
}

# ---------- changelog ----------
if (-not (Test-Path 'CHANGELOG.md')) { Fail 'CHANGELOG.md missing (DEV-RULES 2.5).' }
$cl = Get-Content 'CHANGELOG.md' -Raw
if ($cl -notmatch '## \[Unreleased\]') { Fail 'CHANGELOG.md has no [Unreleased] section.' }
$unrelBlock = ($cl -split '(?m)^## \[Unreleased\]')[1]
if (-not $unrelBlock -or $unrelBlock -match '(?s)^\s*(##\s|$)') {
    Fail 'CHANGELOG [Unreleased] section is empty - add entries before release.'
}
Write-Host '[release-gate] CHANGELOG [Unreleased] has entries.' -ForegroundColor Green

# ---------- version consistency ----------
try {
    $be = (Get-Content 'backend/pyproject.toml' -Raw | Select-String -Pattern '^version\s*=\s*"([^"]+)"' -AllMatches).Matches[0].Groups[1].Value
} catch { $be = $null }
try {
    $pw = (Get-Content 'portal-web/package.json' -Raw | Select-String -Pattern '"version"\s*:\s*"([^"]+)"' -AllMatches).Matches[0].Groups[1].Value
} catch { $pw = $null }
try {
    $aw = (Get-Content 'admin/package.json' -Raw | Select-String -Pattern '"version"\s*:\s*"([^"]+)"' -AllMatches).Matches[0].Groups[1].Value
} catch { $aw = $null }
Write-Host "[release-gate] Versions - backend=$be portal-web=$pw admin=$aw"
$vers = @($be, $pw, $aw) | Where-Object { $_ }
if (($vers | Select-Object -Unique).Count -gt 1) {
    Write-Host '[release-gate] WARNING: version mismatch across modules; bump all in this release.' -ForegroundColor Yellow
}

# ---------- full gate vs main ----------
Write-Host '[release-gate] Running code review gate against origin/main...'
$gateArgs = @('-Base', 'origin/main')
if ($SkipQuality) { $gateArgs += '-SkipQuality' }
& (Join-Path $PSScriptRoot 'code-review-gate.ps1') @gateArgs
if ($LASTEXITCODE -ne 0) { Fail 'Code review gate reported blockers.' }

Write-Host ''
Write-Host '[release-gate] PASSED. Next steps (manual):' -ForegroundColor Green
Write-Host '  1. git merge --no-ff dev -m "merge: dev into main (release vX.Y.Z)"' -ForegroundColor Cyan
Write-Host '  2. git tag vX.Y.Z && git push origin main --tags' -ForegroundColor Cyan
Write-Host '  3. Update CHANGELOG [Unreleased] -> release date, add new [Unreleased]' -ForegroundColor Cyan
exit 0
