<#
.SYNOPSIS
Forge code review gate. Runs blocking checks before merge-to-dev / release.

.RULES
docs/DEV-RULES.md:
  - 1.2/1.3/1.4 branch naming & merge gates
  - 8.1/8.2 workspace hygiene (no backup files, no temp pollution)
  - 13.1 quality gates (ruff/mypy per hook params; pnpm lint/typecheck)
  - 15.2 Conventional Commits

.PARAMETER Base
Base branch to compare against (default: dev).

.PARAMETER SkipQuality
Skip module quality re-run (ruff/mypy/lint/typecheck). Mechanical checks still run.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/code-review-gate.ps1 -Base dev
#>
param(
    [string]$Base = 'dev',
    [switch]$SkipQuality
)

$ErrorActionPreference = 'Continue'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$reportLines = New-Object System.Collections.Generic.List[string]
$blockers = New-Object System.Collections.Generic.List[string]

function Write-Report {
    param([string]$Level, [string]$Msg)
    $script:reportLines.Add("[$Level] $Msg") | Out-Null
    if ($Level -eq 'BLOCKER') { $script:blockers.Add($Msg) | Out-Null }
}

function Test-Command {
    param([string]$Cmd)
    return [bool](Get-Command $Cmd -ErrorAction SilentlyContinue)
}

$head = git branch --show-current
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$reportPath = Join-Path $repoRoot "temp\code-review-report-$timestamp.md"
$hasCommits = $false

Write-Report 'INFO' "Scope: branch '$head' vs base '$Base'"
Write-Report 'INFO' "Generated: $timestamp"

# ---------- 1. Workspace & branch ----------
$status = git status --porcelain | Where-Object { $_ -notmatch '^\?\? temp/' }
if ($status) {
    Write-Report 'WARN' 'Working tree is not clean (excluding temp/): resolve before merge (DEV-RULES 8.2).'
} else {
    Write-Report 'PASS' 'Working tree clean (excluding temp/).'
}

if ($head -and $head -notmatch '^(feature|fix|hotfix)/') {
    Write-Report 'BLOCKER' "Branch '$head' does not follow feature/|fix/|hotfix/ naming (DEV-RULES 1.2)."
} else {
    Write-Report 'PASS' "Branch naming OK: $head"
}

# ---------- 2. Commit convention ----------
$commits = git log "$Base..HEAD" --format=%s 2>$null
if ($commits) {
    $hasCommits = $true
    $bad = @($commits | Where-Object { $_ -notmatch '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+' })
    if ($bad.Count -gt 0) {
        foreach ($c in $bad) { Write-Report 'BLOCKER' "Commit violates Conventional Commits (DEV-RULES 15.2): $c" }
    } else {
        Write-Report 'PASS' "All $($commits.Count) commit(s) follow Conventional Commits."
    }
} else {
    Write-Report 'WARN' "No commits in range $Base..HEAD."
}

# ---------- 3. Changed files & mechanical checks ----------
$changed = @(git diff --name-only "$Base...HEAD" 2>$null)
if ($changed.Count -eq 0) {
    $changed = @(git diff --name-only 2>$null)
}

if ($changed.Count -eq 0) {
    Write-Report 'BLOCKER' 'No changed files detected. Nothing to review.'
}

# backup-style files added
$backupFiles = @($changed | Where-Object { $_ -match '(^|/)([^/]*)(_backup|_old|\.bak|\.orig)(\.|$)|~$' })
if ($backupFiles.Count -gt 0) {
    foreach ($f in $backupFiles) { Write-Report 'BLOCKER' "Backup/leftover file in change set (DEV-RULES 1.2/12): $f" }
} else {
    Write-Report 'PASS' 'No backup/leftover files in change set.'
}

# temp pollution
$tempFiles = @($changed | Where-Object { $_ -match '^temp/' })
if ($tempFiles.Count -gt 0) {
    foreach ($f in $tempFiles) { Write-Report 'BLOCKER' "temp/ file in change set (DEV-RULES 12): $f" }
} else {
    Write-Report 'PASS' 'No temp/ pollution in change set.'
}

# secrets scan over diff hunks (heuristic; gitleaks is authoritative in CI)
$diffText = git diff "$Base...HEAD" 2>$null
if ($diffText) {
    $secretHits = @($diffText | Select-String -Pattern '(?i)(password|passwd|secret|api[_-]?key|token|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY)\s*[:=]\s*[^\s"''*]{8,}' |
        Where-Object {
            $_.Line -notmatch 'example|placeholder|your_|xxx|test' -and
            $_.Line -notmatch '=\s*[$@]' -and
            $_.Line -notmatch '=\s*[A-Za-z]+-[A-Za-z]+\s*$' -and
            $_.Line -notmatch '=\s*[A-Za-z_]+\(\)?\s*$' -and
            $_.Line -notmatch ':\s*[$@]' -and
            $_.Line -notmatch '[:=]\s*[A-Za-z_$][\w$]*(\.[\w$]+)+' -and
            $_.Line -notmatch '\["''(password|token|secret|key)"''\]'
        } | Select-Object -First 5)
    if ($secretHits.Count -gt 0) {
        foreach ($h in $secretHits) { Write-Report 'BLOCKER' "Possible secret in diff (DEV-RULES 13.4): $($h.Line.Trim())" }
    } else {
        Write-Report 'PASS' 'No obvious secrets in diff.'
    }
}

# ---------- 4. Quality gates (skip if disabled) ----------
if (-not $SkipQuality) {
    $pyFiles = @($changed | Where-Object { $_ -match '^backend/.*\.py$' })
    if ($pyFiles.Count -gt 0) {
        Write-Report 'INFO' "backend gate: $($pyFiles.Count) python file(s) changed."
        $preCommitPy = Join-Path $env:USERPROFILE '.local\precommit-env\Scripts\python.exe'
        if (Test-Path $preCommitPy) {
            Write-Report 'INFO' 'Running pre-commit hooks (ruff + mypy, hook-equivalent params) on changed files...'
            Push-Location (Join-Path $repoRoot 'backend')
            try {
                $relPyFiles = @($pyFiles | ForEach-Object { $_ -replace '^backend/', '' })
                $out = & $preCommitPy -m pre_commit run -c .pre-commit-config.yaml --files $relPyFiles 2>&1 | Out-String
            } finally {
                Pop-Location
            }
            if ($LASTEXITCODE -ne 0) {
                Write-Report 'BLOCKER' 'backend quality gate failed (ruff/mypy). See pre-commit output below.'
                $reportLines.Add('--- pre-commit tail ---') | Out-Null
                ($out -split "`r?`n" | Select-Object -Last 25) | ForEach-Object { $reportLines.Add($_) | Out-Null }
            } else {
                Write-Report 'PASS' 'backend quality gate passed (ruff + mypy).'
            }
        } else {
            Write-Report 'WARN' 'pre-commit env not found; skipped backend gate (install per DEV-RULES 13.2).'
        }
    }

    $frontendChanged = @($changed | Where-Object { $_ -match '^portal-web/' -or $_ -match '^admin/' })
    if ($frontendChanged.Count -gt 0) {
        # inject fnm node path (DEV-RULES 13.2)
        $fnmDir = Get-ChildItem "$env:LOCALAPPDATA\fnm_multishells" -Directory -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($fnmDir) { $env:PATH = "$($fnmDir.FullName);" + $env:PATH }

        if (Test-Command 'pnpm') {
            $modules = @()
            if (($changed | Where-Object { $_ -match '^portal-web/' }).Count -gt 0) { $modules += 'portal-web' }
            if (($changed | Where-Object { $_ -match '^admin/' }).Count -gt 0) { $modules += 'admin' }
            foreach ($mod in $modules) {
                Push-Location $mod
                Write-Report 'INFO' "$mod gate: pnpm lint + typecheck..."
                $lintOut = pnpm lint 2>&1 | Out-String
                if ($LASTEXITCODE -ne 0) {
                    Write-Report 'BLOCKER' "$mod pnpm lint failed."
                    ($lintOut -split "`r?`n" | Select-Object -Last 20) | ForEach-Object { $reportLines.Add($_) | Out-Null }
                }
                $tcOut = pnpm typecheck 2>&1 | Out-String
                if ($LASTEXITCODE -ne 0) {
                    Write-Report 'BLOCKER' "$mod pnpm typecheck failed."
                    ($tcOut -split "`r?`n" | Select-Object -Last 20) | ForEach-Object { $reportLines.Add($_) | Out-Null }
                }
                if ($LASTEXITCODE -eq 0 -and -not $blockers) { Write-Report 'PASS' "$mod quality gate passed." }
                Pop-Location
            }
        } else {
            Write-Report 'WARN' 'pnpm not found on PATH (fnm injection failed); skipped frontend gates.'
        }
    } else {
        Write-Report 'PASS' 'No backend/frontend source change; quality gates not required for this scope.'
    }
} else {
    Write-Report 'INFO' 'Quality gates skipped (-SkipQuality).'
}

# ---------- 5. Report ----------
if (-not (Test-Path (Join-Path $repoRoot 'temp'))) { New-Item -ItemType Directory -Path (Join-Path $repoRoot 'temp') | Out-Null }
$reportLines | Set-Content -Path $reportPath -Encoding UTF8

Write-Report 'INFO' "Report written to: $reportPath"

$blockerCount = $blockers.Count
Write-Host ''
Write-Host "================ Code Review Gate Result ================" -ForegroundColor Cyan
Write-Host "Branch: $head | Base: $Base | Blockers: $blockerCount" -ForegroundColor Cyan
foreach ($b in $blockers) { Write-Host "[BLOCKER] $b" -ForegroundColor Red }
Write-Host "Report: $reportPath" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

if ($blockerCount -gt 0) {
    Write-Host "GATE FAILED: $blockerCount blocker(s). Fix before merging." -ForegroundColor Red
    exit 1
} else {
    Write-Host 'GATE PASSED: ready for merge / release.' -ForegroundColor Green
    exit 0
}
