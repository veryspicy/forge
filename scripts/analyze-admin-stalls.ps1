<#
.SYNOPSIS
  Detect admin page-freeze (main-thread stall) windows from gateway/nginx access log gaps.

.DESCRIPTION
  Admin freeze fingerprint (2026-09-28): after login/me returned 200 the browser stopped sending
  any request, including the in-page 30s self-check (index.html fetch) - i.e. the renderer main
  thread stalled. A stalled tab produces a request silence window in the gateway access log.

  This script groups access log entries by client IP, sorts them by time, and reports every gap
  larger than -GapSeconds. Reported windows can be correlated with the in-page stall reports
  (browser console: window.__forgeStallDump(), or localStorage key forge:stall-reports).

.PARAMETER LogPath
  Gateway/nginx access log file (combined or main format).

.PARAMETER GapSeconds
  Minimum silence gap between two consecutive requests of the same client. Default 30
  (the admin self-check runs every 30s, so >=30s silence is already abnormal).

.PARAMETER ClientIp
  Optional: only analyze a single client IP.

.PARAMETER TopN
  Number of largest gaps printed in the report. Default 20.

.PARAMETER OutFile
  Optional report path. Default: <repo>/temp/admin-stall-gaps-<timestamp>.txt

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\analyze-admin-stalls.ps1 -LogPath D:\logs\gateway-access.log
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$LogPath,

  [int]$GapSeconds = 30,

  [string]$ClientIp = '',

  [int]$TopN = 20,

  [string]$OutFile = ''
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $LogPath)) {
  Write-Error "Log file not found: $LogPath"
  exit 1
}

$repoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $tempDir = Join-Path $repoRoot 'temp'
  if (-not (Test-Path -LiteralPath $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir | Out-Null
  }
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $OutFile = Join-Path $tempDir "admin-stall-gaps-$stamp.txt"
}

# nginx combined / main format:
# 1.2.3.4 - - [28/Sep/2026:20:44:01 +0800] "GET /api/v1/auth/login HTTP/1.1" 200 123 "-" "ua"
$pattern = '^(?<ip>\S+)\s+\S+\s+\S+\s+\[(?<ts>[^\]]+)\]\s+"(?<req>[^"]*)"\s+(?<status>\d{3})'
$invariant = [System.Globalization.CultureInfo]::InvariantCulture
$tsFormat = 'dd/MMM/yyyy:HH:mm:ss zzz'

$byClient = @{}
$totalLines = 0
$parsed = 0
$skipped = 0

$reader = [System.IO.File]::OpenText($LogPath)
try {
  while ($null -ne ($line = $reader.ReadLine())) {
    $totalLines++
    $match = [regex]::Match($line, $pattern)
    if (-not $match.Success) {
      $skipped++
      continue
    }

    $ip = $match.Groups['ip'].Value
    if ($ClientIp -ne '' -and $ip -ne $ClientIp) {
      continue
    }

    $tsText = $match.Groups['ts'].Value
    $ts = [datetime]::MinValue
    try {
      $ts = [datetime]::ParseExact($tsText, $tsFormat, $invariant)
    } catch {
      $skipped++
      continue
    }

    $entry = New-Object psobject -Property @{
      Time   = $ts
      Ip     = $ip
      Req    = $match.Groups['req'].Value
      Status = $match.Groups['status'].Value
    }

    if (-not $byClient.ContainsKey($ip)) {
      $byClient[$ip] = New-Object System.Collections.ArrayList
    }
    [void]$byClient[$ip].Add($entry)
    $parsed++
  }
} finally {
  $reader.Close()
}

$gaps = New-Object System.Collections.ArrayList
foreach ($ip in $byClient.Keys) {
  $entries = @($byClient[$ip] | Sort-Object -Property Time)
  if ($entries.Count -lt 2) {
    continue
  }

  for ($i = 1; $i -lt $entries.Count; $i++) {
    $gap = ($entries[$i].Time - $entries[$i - 1].Time).TotalSeconds
    if ($gap -lt $GapSeconds) {
      continue
    }

    # The freeze window is the silence between the last request before the gap and the first after.
    $lastReq = $entries[$i - 1]
    $nextReq = $entries[$i]
    $selfCheckHit = if ($lastReq.Req -match 'index\.html') { 'YES' } else { 'no' }

    [void]$gaps.Add((New-Object psobject -Property @{
      Ip                = $ip
      GapSeconds        = [math]::Round($gap, 1)
      From              = $lastReq.Time.ToString('yyyy-MM-dd HH:mm:ss')
      To                = $nextReq.Time.ToString('yyyy-MM-dd HH:mm:ss')
      LastRequest       = $lastReq.Req
      LastStatus        = $lastReq.Status
      NextRequest       = $nextReq.Req
      LastWasSelfCheck  = $selfCheckHit
    }))
  }
}

$sorted = @($gaps | Sort-Object -Property GapSeconds -Descending)
$lines = New-Object System.Collections.ArrayList

[void]$lines.Add("admin stall gap report")
[void]$lines.Add("log          : $LogPath")
[void]$lines.Add("client filter: $(if ($ClientIp -eq '') { '<all>' } else { $ClientIp })")
[void]$lines.Add("gap threshold: >= $GapSeconds s")
[void]$lines.Add("parsed lines : $parsed (skipped $skipped / total $totalLines)")
[void]$lines.Add("clients      : $($byClient.Count), gaps: $($sorted.Count)")
[void]$lines.Add('')

if ($sorted.Count -eq 0) {
  [void]$lines.Add('No gap found. Either the log has no freezes or the threshold is too high.')
} else {
  [void]$lines.Add("top $TopN gaps (silence windows of a client):")
  [void]$lines.Add('gap(s) | client | from -> to | last request (status) | self-check before gap')
  $limit = [math]::Min($TopN, $sorted.Count)
  for ($i = 0; $i -lt $limit; $i++) {
    $item = $sorted[$i]
    # NOTE: the comma list after -f must be wrapped in @(), otherwise it is parsed as
    # multiple arguments when it sits inside a method-call argument list (PS 5.1).
    $rowArgs = @(
      $item.GapSeconds, $item.Ip, $item.From, $item.To,
      $item.LastRequest, $item.LastStatus, $item.LastWasSelfCheck
    )
    [void]$lines.Add(("{0,8} | {1} | {2} -> {3} | {4} ({5}) | {6}" -f $rowArgs))
  }
  [void]$lines.Add('')
  [void]$lines.Add('How to read:')
  [void]$lines.Add('- Gap >= 30s with self-check=YES before the gap => the page stopped its 30s self-check,')
  [void]$lines.Add('  which is the main-thread stall fingerprint. Cross-check the same timestamp with the')
  [void]$lines.Add('  browser side report forge:stall-reports (kind=frozen-session / main-thread-blocked).')
  [void]$lines.Add('- Gap on /api/* only, while self-check keeps hitting index.html => request layer stall,')
  [void]$lines.Add('  not a main-thread freeze.')
}

$report = $lines -join [Environment]::NewLine
Set-Content -LiteralPath $OutFile -Value $report -Encoding UTF8
Write-Output $report
Write-Output ''
Write-Output "report written: $OutFile"
