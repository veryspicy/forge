# check-admin.ps1 — Forge Admin 全链路健康检查（网关 → index.html → 全部静态资源）
#
# 用途：admin 容器重建后验证页面是否真正可用，杜绝「index.html 200 但 JS/CSS 404」的假通过。
# 用法：powershell -ExecutionPolicy Bypass -File .\check-admin.ps1 [-BaseUrl http://127.0.0.1:8080]
#
# 退出码：0=全部通过；1=存在失败项（可接入 CI / 部署脚本）。

param(
    [string]$BaseUrl = 'http://127.0.0.1:8080'
)

$fail = 0

# 1. index.html
try {
    $html = (Invoke-WebRequest -Uri "$BaseUrl/admin/" -UseBasicParsing -TimeoutSec 10).Content
    Write-Host "[OK] /admin/ ($($html.Length) B)"
} catch {
    Write-Host "[FAIL] /admin/ : $($_.Exception.Message)"
    exit 1
}

# 2. 从 index.html 提取全部 js/css 资源（含 modulepreload href 与 stylesheet href）
$paths = @()
$paths += [regex]::Matches($html, 'src="([^"]+)"')    | ForEach-Object { $_.Groups[1].Value }
$paths += [regex]::Matches($html, 'href="([^"]+)"')   | ForEach-Object { $_.Groups[1].Value }
$paths = $paths | Where-Object { $_ -match '\.(js|css)$' } | Select-Object -Unique

if ($paths.Count -eq 0) { Write-Host '[WARN] 未从 index.html 提取到任何 js/css 资源，请检查页面。'; exit 1 }

foreach ($p in $paths) {
    $url = if ($p -like 'http*') { $p } else { "$BaseUrl$p" }
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
        if ($r.StatusCode -eq 200) {
            $len = if ($r.RawContentLength -gt 0) { $r.RawContentLength } else { $r.Content.Length }
            Write-Host "[OK] $p ($len B)"
        } else {
            Write-Host "[FAIL $($r.StatusCode)] $p"
            $fail++
        }
    } catch {
        $code = try { $_.Exception.Response.StatusCode.value__ } catch { 'ERR' }
        Write-Host "[FAIL $code] $p : $($_.Exception.Message)"
        $fail++
    }
}

Write-Host '----'
if ($fail -eq 0) {
    Write-Host "结果: 全部通过（共 $($paths.Count) 个资源）"
    exit 0
} else {
    Write-Host "结果: $fail 个资源失败"
    exit 1
}
