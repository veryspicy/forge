# rebuild-service.ps1 — Forge 通用单服务/全量一键重建脚本（backend / portal-web / ai-service / admin）
#
# 背景：podman-compose 外部 provider 在本机经常静默失败（无输出且不生效），
#       且 --force-recreate 会连带处理依赖图（如缺失的一次性容器 forge-init-admin），
#       导致「镜像已更新但容器未重建」的假成功或直接报错中断。
#       本脚本复用 rebuild-admin.ps1 已验证模式：以 compose 为首选路径，
#       通过容器 StartedAt 校验是否真正重建，未生效时自动降级
#       （rm 旧容器 → compose up 重建，admin 再兜底到手动 podman run）。
#       内置 SOP-compose-rebuild.md 判断矩阵：admin 强制 --no-cache，其余服务普通 build 加速；
#       失败即停，不静默继续。
#
# 用法（在 docker/ 目录下执行）：
#   powershell -ExecutionPolicy Bypass -File .\rebuild-service.ps1 -Service backend
#   powershell -ExecutionPolicy Bypass -File .\rebuild-service.ps1 -Service all
#   powershell -ExecutionPolicy Bypass -File .\rebuild-service.ps1 -Service admin -SkipBuild
#   powershell -ExecutionPolicy Bypass -File .\rebuild-service.ps1 -Service portal-web -NoCache -Smoke
#
# 参数：
#   -Service   backend | portal-web | ai-service | admin | all
#   -SkipBuild 跳过镜像构建，仅重建容器（镜像须已存在）
#   -NoCache   强制 --no-cache 构建（admin 默认即 --no-cache，无需显式传）
#   -Smoke     重建后跑 HTTP 冒烟自检
#
# 完成后按输出清单访问对应地址验证（Admin 需 Ctrl+Shift+R 硬刷新）。

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('backend', 'portal-web', 'ai-service', 'admin', 'all')]
    [string]$Service,
    [switch]$SkipBuild,
    [switch]$NoCache,
    [switch]$Smoke,
    [switch]$SkipPreflight
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

$ComposeFile = '.\docker-compose.yml'
$ProjectName = 'docker'
$DnsServer   = '223.5.5.5'   # 构建期 DNS，绕过 registry.npmjs.org EAI_AGAIN

# ---------- 0. 启动前检查（machine 状态 + 水位 + 清理） ----------
# 启动/重建容器前统一走 preflight.ps1，避免悬空镜像堆积与 machine 未就绪。
# 应急可加 -SkipPreflight 跳过。
if (-not $SkipPreflight) {
    Write-Host '[0/3] preflight（machine 状态 + 水位 + 清理）'
    $pfArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PWD 'preflight.ps1'))
    & powershell @pfArgs
    if ($LASTEXITCODE -eq 1 -or $LASTEXITCODE -eq 2) { throw 'preflight 未通过，终止重建。' }
} else {
    Write-Host '[0/3] 跳过 preflight（-SkipPreflight）'
}

# ---------- 服务定义表（唯一真相来源 = docker-compose.yml + Dockerfile） ----------
# Container: 容器名；Image: 镜像名；Dockerfile/Context: 构建源；NoCache: 是否默认 --no-cache
# Port: 对外端口（用于冒烟）；HealthPath: 冒烟健康路径；ReloadGateway: 重建后是否需网关 reload
$Services = @{
    'backend'     = @{
        Container     = 'forge-backend'
        Image         = 'forge-backend:latest'
        Dockerfile    = '..\backend\Dockerfile'
        Context       = '..\backend'
        NoCache       = $false
        Port          = 8002
        HealthPath    = '/health'
        ReloadGateway = $false
    }
    'portal-web'  = @{
        Container     = 'forge-portal-web'
        Image         = 'forge-portal-web:latest'
        Dockerfile    = '..\portal-web\Dockerfile'
        Context       = '..\portal-web'
        NoCache       = $false
        Port          = 3000
        HealthPath    = '/'
        ReloadGateway = $false
    }
    'ai-service'  = @{
        Container     = 'forge-ai'
        Image         = 'forge-ai:latest'
        Dockerfile    = '..\ai-service\Dockerfile'
        Context       = '..\ai-service'
        NoCache       = $false
        Port          = 8001
        HealthPath    = '/health'
        ReloadGateway = $false
    }
    'admin'       = @{
        Container     = 'forge-admin'
        Image         = 'localhost/forge-admin:latest'
        Dockerfile    = '..\admin\Dockerfile'
        Context       = '..\admin'
        NoCache       = $true          # SOP：Admin 无 HMR，源码改动必须 --no-cache 才生效
        Port          = 8080
        HealthPath    = '/'
        ReloadGateway = $true
    }
}

# ---------- 原生命令封装 ----------
# PS 5.1 + $ErrorActionPreference='Stop' 下，原生命令的 stderr 会经 2>&1 转 ErrorRecord
# 导致脚本被意外终止（实测 podman-compose 报 init-admin 缺失时中断，降级逻辑没机会跑）。
# 这里局部降为 Continue 再收集 stderr，判断完全依赖退出码。
function Invoke-Native {
    param([string]$Command, [string[]]$Arguments)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $Command @Arguments 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) { Write-Host $_.Exception.Message -ForegroundColor DarkYellow }
        else { Write-Host $_ }
    }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    return $code
}

function Get-StartedAt {
    param([string]$Name)
    $v = podman inspect $Name --format '{{.State.StartedAt}}' 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return $v
}

function Get-ContainerNetwork {
    param([string]$Name)
    $nets = podman inspect $Name --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $nets) { return 'docker_forge' }
    $first = ($nets.Trim() -split '\s+')[0]
    if (-not $first) { return 'docker_forge' }
    return $first
}

function Test-HttpStatus {
    param([string]$Url)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        return $r.StatusCode
    } catch {
        return 0
    }
}

function Invoke-Smoke {
    param([string]$Name, [int]$Port, [string]$HealthPath)
    $svcName = $Services[$Name].Container
    $running = podman ps --filter "name=$svcName" --format '{{.Names}}'
    if (-not $running) { Write-Host "  [FAIL] $svcName 未运行" -ForegroundColor Red; return $false }

    # 慢启动服务（portal-web 等）需要等待就绪：最多 60s，每 5s 探测一次
    $code = 0
    for ($i = 0; $i -lt 12; $i++) {
        $code = Test-HttpStatus "http://127.0.0.1:$Port$HealthPath"
        if ($code -eq 200) { break }
        Start-Sleep -Seconds 5
    }
    if ($code -eq 200) {
        Write-Host "  [OK]   http://127.0.0.1:$Port$HealthPath -> 200" -ForegroundColor Green
    } else {
        # ai-service 等端点可能不同，兜底探测根路径
        if ($HealthPath -ne '/') {
            $code2 = Test-HttpStatus "http://127.0.0.1:$Port/"
            if ($code2 -eq 200) {
                Write-Host "  [OK]   http://127.0.0.1:$Port$HealthPath 无此端点，根路径 -> $code2" -ForegroundColor Green
                return $true
            }
        }
        Write-Host "  [FAIL] http://127.0.0.1:$Port$HealthPath -> $code（60s 内未就绪）" -ForegroundColor Red
        return $false
    }
    return $true
}

# ---------- 目标服务列表 ----------
$targets = @()
if ($Service -eq 'all') { $targets = @('backend', 'ai-service', 'portal-web', 'admin') }
else { $targets = @($Service) }

Write-Host "==> 重建目标: $($targets -join ', ')"
Write-Host ""

# ---------- 1. 构建镜像 ----------
if (-not $SkipBuild) {
    foreach ($name in $targets) {
        $cfg = $Services[$name]
        $cacheFlag = if ($cfg.NoCache -or $NoCache) { '--no-cache' } else { '' }
        Write-Host "[1/3] 构建 $name 镜像 ($cacheFlag) ..."
        $code = Invoke-Native 'podman' @('build', $cacheFlag, '--dns', $DnsServer, '-t', $cfg.Image, '-f', $cfg.Dockerfile, $cfg.Context)
        if ($code -ne 0) { throw "构建 $name 失败，终止。" }
        Write-Host "      完成: $($cfg.Image)"
    }
} else {
    Write-Host '[1/3] 跳过构建（-SkipBuild）'
}

# ---------- 2. 重建容器 ----------
foreach ($name in $targets) {
    $cfg = $Services[$name]
    $container = $cfg.Container
    Write-Host "[2/3] 重建 $name ($container) ..."

    $before = Get-StartedAt $container
    Write-Host "      重建前 StartedAt = $before"

    # 首选 compose 路径：--no-deps 避免连带重建依赖图（forge-init-admin 缺失会报错）
    $code = Invoke-Native 'podman-compose' @('--project-name', $ProjectName, '-f', $ComposeFile, 'up', '-d', '--force-recreate', '--no-deps', $name)
    Start-Sleep -Seconds 6

    $after = Get-StartedAt $container
    $recreated = ($code -eq 0 -and $before -ne $after)

    if (-not $recreated) {
        Write-Warning "      podman-compose 未生效（外部 provider 静默失败或报错），降级：rm 旧容器 + compose up 重建。"
        Invoke-Native 'podman' @('rm', '-f', $container) | Out-Null
        $code = Invoke-Native 'podman-compose' @('--project-name', $ProjectName, '-f', $ComposeFile, 'up', '-d', '--no-deps', $name)
        Start-Sleep -Seconds 6
        $after = Get-StartedAt $container

        # admin 最后兜底：手动 podman run（rebuild-admin.ps1 已验证路径，容器名/别名/网络必须与 compose 一致）
        if (-not $after -and $name -eq 'admin') {
            Write-Warning "      compose 仍不可用，admin 降级手动 podman run（已验证路径）。"
            $net = Get-ContainerNetwork $container
            Invoke-Native 'podman' @('run', '-d', '--name', $container, '--network', $net, '--network-alias', 'admin', '--restart', 'unless-stopped', $cfg.Image) | Out-Null
            Start-Sleep -Seconds 6
            $after = Get-StartedAt $container
        }
    }

    if (-not $after) { throw "$container 重建后仍未运行，终止。" }
    Write-Host "      重建后 StartedAt = $after"
}

# ---------- 3. 网关生效 ----------
$needReload = $targets | Where-Object { $Services[$_].ReloadGateway }
if ($needReload) {
    Write-Host '[3/3] 网关 nginx reload（resolver 动态解析，重建换 IP 无需重启）'
    $code = Invoke-Native 'podman' @('exec', 'forge-gateway', 'nginx', '-s', 'reload')
    if ($code -ne 0) { throw '网关 reload 失败，终止。' }
} else {
    Write-Host '[3/3] 本服务无需网关 reload，跳过。'
}

# ---------- 冒烟自检 ----------
if ($Smoke) {
    Write-Host ''
    Write-Host '冒烟自检:'
    $allOk = $true
    foreach ($name in $targets) {
        $cfg = $Services[$name]
        if (-not (Invoke-Smoke $name $cfg.Port $cfg.HealthPath)) { $allOk = $false }
    }
    if (-not $allOk) { throw '冒烟自检存在失败项，请检查。' }
}

# ---------- 验证清单 ----------
Write-Host ''
Write-Host '==> 重建完成，验证清单：'
foreach ($name in $targets) {
    $cfg = $Services[$name]
    $url = if ($name -eq 'admin') { 'http://127.0.0.1:8080/  （勿用 localhost，IPv6 会超时；Ctrl+Shift+R 硬刷新）' }
           elseif ($name -eq 'backend') { 'http://127.0.0.1:8002/health + /docs' }
           elseif ($name -eq 'portal-web') { 'http://127.0.0.1:3000/' }
           else { 'http://127.0.0.1:8001/health' }
    Write-Host "  - $name : $url"
}
Write-Host ''
