# rebuild-admin.ps1 — Forge Admin 一键重建镜像 + 重建容器 + 网关生效
#
# 背景：podman-compose 外部 provider 在本机经常静默失败（无输出且不生效），
#       若只依赖 compose 重建会导致「镜像已更新但容器未重建」的假成功。
#       本脚本以 compose 为首选路径，通过容器 StartedAt 校验是否真正重建，
#       未生效时自动降级到已验证的手动 podman run 路径。
#
# 用法（在 docker/ 目录下执行）：
#   powershell -ExecutionPolicy Bypass -File .\rebuild-admin.ps1          # 完整重建
#   powershell -ExecutionPolicy Bypass -File .\rebuild-admin.ps1 -SkipBuild  # 仅重建容器（镜像已构建）
#
# 完成后访问 http://127.0.0.1:8080/admin/ （勿用 localhost，IPv6 会超时）并 Ctrl+Shift+R 硬刷新。

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

$ComposeFile = '.\docker-compose.yml'
$ProjectName = 'docker'
$Image       = 'localhost/forge-admin:latest'
$Container   = 'forge-admin'
$Network     = 'docker_forge'          # podman-compose 项目名 docker + 网络 forge
$DnsServer   = '223.5.5.5'             # 构建期 DNS，绕过 registry.npmjs.org EAI_AGAIN

# ---------- 1. 构建镜像 ----------
if (-not $SkipBuild) {
    Write-Host '[1/3] podman build --no-cache --dns=223.5.5.5 ...'
    podman build --no-cache --dns $DnsServer -t $Image -f '..\admin\Dockerfile' '..\admin'
    if ($LASTEXITCODE -ne 0) { throw '镜像构建失败，终止。' }
    Write-Host "构建完成: $Image"
} else {
    Write-Host '[1/3] 跳过构建（-SkipBuild）'
}

# ---------- 2. 重建容器 ----------
Write-Host '[2/3] 重建容器 ...'
$before = (podman inspect $Container --format '{{.State.StartedAt}}' 2>$null)

# 首选 compose 路径（DEV-RULES 3.3 统一命令）
podman-compose --project-name $ProjectName -f $ComposeFile up -d --force-recreate admin 2>&1 | Out-Host
Start-Sleep -Seconds 6

$after = (podman inspect $Container --format '{{.State.StartedAt}}' 2>$null)
if ($before -eq $after) {
    Write-Warning 'podman-compose 未生效（外部 provider 静默失败），降级手动重建（已验证路径）。'
    podman rm -f $Container | Out-Null
    podman run -d --name $Container `
        --network $Network `
        --network-alias admin `
        --restart unless-stopped `
        $Image | Out-Null
}

if (-not (podman ps --filter "name=$Container" --format '{{.Names}}')) { throw '容器未运行，终止。' }
Write-Host "容器已运行，StartedAt = $(podman inspect $Container --format '{{.State.StartedAt}}')"

# ---------- 3. 网关生效 ----------
Write-Host '[3/3] 网关 nginx reload（resolver 动态解析，重建换 IP 无需重启）'
podman exec forge-gateway nginx -s reload 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { throw '网关 reload 失败，终止。' }

# ---------- 自检 ----------
Write-Host ''
Write-Host '自检:'
& (Join-Path $PSScriptRoot 'check-admin.ps1')
if ($LASTEXITCODE -ne 0) { throw '自检未通过，请检查上述失败项。' }

Write-Host ''
Write-Host '完成。浏览器访问 http://127.0.0.1:8080/admin/ 并 Ctrl+Shift+R 硬刷新。'
