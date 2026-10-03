# Forge 本地开发环境基线（INFRA-BASELINE）

> 适用范围：Windows 11 + WSL2 + podman machine 容器化开发环境。
> 本文档是环境事实基线 + 故障恢复 SOP。**环境问题必须先查本文档，禁止从头排查**。
> 最后更新：2026-09-09（固化原因：8080 端口转发问题重复发生且每次从头排查；2026-09-09 补充 wsl --update 后 machine 卡 Starting / 52293 转发异常 SOP，并统一发行版内 podman 至 6.1.1）

---

## 1. 环境拓扑（事实基线）

| 组件 | 值 |
|---|---|
| 操作系统 | Windows 11 (Build 26200) |
| WSL | 2.7.11，`.wslconfig` 配置 `networkingMode=mirrored`（镜像网络模式，全局生效），另设 `[wsl2] vmIdleTimeout=-1` 与 `[general] instanceIdleTimeout=-1`（2026-09-09 修复 VM 空闲约 60s 自动关闭导致的假掉线） |
| podman | 6.1.1（Windows 侧与发行版内均已统一，machine `podman-machine-default`，WSL 后端，rootless；发行版内原 6.0.2 于 2026-09-09 升级，来源 rhcontainerbot:f44-podman6 COPR） |
| podman machine 网络 | `UserModeNetworking=false`（NAT；曾为 true，因端口注册丢失切换，勿轻易切回，见 §6） |
| 容器网络 | `docker_forge`（compose 自动创建）——**所有容器必须挂此网络** |
| 容器清单 | forge-postgres / forge-redis / forge-minio / forge-namesrv / forge-broker / forge-backend / forge-ai / forge-portal-web / forge-admin / forge-gateway / forge-init-admin（一次性） |

## 2. 访问入口（强制）

| 入口 | 地址 | 说明 |
|---|---|---|
| 网关（唯一对外入口） | `http://127.0.0.1:8080` | nginx 网关 |
| admin 后台 | `http://127.0.0.1:8080/admin/` | **尾部斜杠必带**；admin 无对外端口，由网关代理到 admin:80 |
| portal-web | `http://127.0.0.1:8080/` | 根路径 |
| backend 直连 | `http://127.0.0.1:8002` | 宿主 8002 → 容器 8000 |
| 登录 | admin / admin123 | |

**铁律：一律用 `127.0.0.1`，禁止用 `localhost`。** 原因见 §3。

## 3. 为什么必须用 127.0.0.1 而不是 localhost

- `.wslconfig` 为镜像网络模式（mirrored），WSL 与 Windows 共享网络栈
- Windows 上 `localhost` 名称解析**优先返回 IPv6 `::1`**，而镜像网络模式下 **IPv6 回环（::1）不转发**到 WSL → 连接超时
- IPv4 回环 `127.0.0.1` 转发正常（2026-08-24 实测：WSL 内服务经 Windows `127.0.0.1:端口` 可达 200，`localhost:端口` 超时）
- 影响范围：所有脚本、browser-agent 派发地址、curl / Invoke-WebRequest 验证命令，一律写 `127.0.0.1`

## 4. 容器生命周期管理（强制）

**podman-compose 可用性**：曾因 Smart App Control（SAC）误拦截被禁用（SAC 拦 uv/venv 无微软信誉签名的 Python 可执行文件，含 podman-compose.exe）；**2026-08-24 用户关闭 SAC 后已恢复可用**（实测 `podman-compose --version` → 1.6.0，无拦截）。若 compose 命令再被拦截，先按 §6 坑位 5 检查 SAC/WDAC 状态，再退回 `podman start` 方案。

```powershell
# 启动全部容器（顺序无关，等待健康即可）
podman start forge-postgres forge-redis forge-minio forge-namesrv forge-broker forge-backend forge-ai forge-portal-web forge-admin forge-gateway

# 单容器管理
podman start / stop / restart <容器名>

# 容器内执行命令（迁移、调试）
podman exec <容器名> <命令>

# admin 重建完整 SOP（镜像变更后替换运行容器；无 HMR，必须 --no-cache）
# 注意：podman-compose 被拦截，无法用 compose up --force-recreate，只能手工替换。
# 替换前必须核对既有容器参数（网络/别名/restart），禁止凭记忆省略参数。
cd D:\codeRepo\forge\docker
podman build --no-cache -t localhost/forge-admin:latest ../admin
podman rm -f forge-admin
podman run -d --name forge-admin --network docker_forge --network-alias admin --restart unless-stopped localhost/forge-admin:latest
# 若网关 502 且指向旧 IP：nginx resolver 缓存了被删容器的 IP，需 podman restart forge-gateway 刷新
# 验证：Invoke-WebRequest http://127.0.0.1:8080/admin/ → 期望 200
```

**禁止事项**：
- 禁止不带完整网络参数的 `podman run` 重建既有容器（会连错网络 / 丢配置）。必须严格按上述 SOP 带全 `--network docker_forge --network-alias <服务名> --restart unless-stopped`；网络名以 `podman network ls` 实测为准（compose 逻辑名 `forge` ≠ 实际网络名 `docker_forge`）
- 环境操作前必须先查本文档 §1/§4（DEV-RULES §16 强制）；本次踩坑根因即未先查基线、凭 compose 逻辑网络名误挂 `forge`
- 若确需重建 gateway：必须挂 `docker_forge` 网络（勿用 `--network forge`），重建后立即验证 `podman exec forge-gateway curl http://backend:8000/health`

## 5. 环境故障恢复 SOP（按序执行，勿跳步）

**触发条件**：Windows 侧访问 `127.0.0.1:8080` 超时 / 502 / 无监听，或 podman machine 异常。

```powershell
# 1. 诊断
netstat -ano | findstr ":8080"          # Windows 侧是否有监听
podman ps                               # machine 是否可连、容器状态
podman machine ssh "ss -tln | grep 8080"  # WSL 内 rootlessport 是否监听

# 2. machine 异常时：完整重启（勿裸 wsl --shutdown，会丢 systemd 导致 podman.socket 未起）
podman machine stop
podman machine start

# 3. stop 失败（如 user-mode networking 清理报错）时强制恢复
wsl --terminate podman-net-usermode
wsl --terminate podman-machine-default
podman machine stop
podman machine start

# 4. 拉起容器（machine 重启后容器不会自动恢复）
podman start forge-postgres forge-redis forge-minio forge-namesrv forge-broker forge-backend forge-ai forge-portal-web forge-admin forge-gateway

# 5. 等待 backend healthy（约 1-2 分钟）
podman ps --filter "name=forge-backend"

# 6. 验证链路（注意用 127.0.0.1）
Invoke-WebRequest http://127.0.0.1:8080/            # 期望 200
podman exec forge-gateway curl http://backend:8000/health   # 期望 200

# 7. 若 gateway 502：检查网络归属
podman inspect forge-gateway --format '{{json .NetworkSettings.Networks}}'
# 应含 docker_forge；若在 forge 网络，执行：
podman network connect docker_forge forge-gateway
```

## 6. 已知坑位（避免重踩）

1. **user-mode networking 端口注册丢失**：`UserModeNetworking=true` 时，Windows 侧 8080 转发依赖 `podman-net-usermode\entries` 文件注册；WSL 重启 / wslservice 重启后该注册可能丢失（entries 文件为空），Windows 侧 gvproxy 无 8080 监听。**已切换为 `UserModeNetworking=false` 规避；若再切回 true，必须验证 `127.0.0.1:8080` 可用**。
2. **容器网络错位**：`docker_forge` 与 `forge` 是两个不同网络（前者 compose 创建、后者可能是手动创建残留）。gateway 连错网络会 502。所有容器统一挂 `docker_forge`。
3. **machine 重启后容器不自动恢复**：必须手动 `podman start` 全部容器（restart=unless-stopped 在 machine 层面不生效）。
4. **init-admin 阻塞 compose（已解决）**：根因是 `backend/seed_admin.py` 第 35 行 import 已删除的 `casbin_enforcer` 模块，导致 `forge-init-admin` 容器必然 Exited(1)，compose up 每次尝试重建该一次性容器而卡住。2026-08-24 方案A落地：已从 docker-compose.yml 移除 init-admin 服务定义（compose 不再包含该服务），并修复 seed_admin.py（移除 casbin 引用，RBAC 数据由 migration + API 落地，admin 可正常登录）。seed_admin.py 保留为手动初始化脚本（容器内 `python /app/seed_admin.py`），不再参与 compose 生命周期。
5. **podman-compose 曾被 SAC 误拦截（已解决）**：Smart App Control 曾误拦 podman-compose.exe 及 uv/venv Python 可执行文件（python.exe、alembic.exe、uvicorn.exe、.pyd 等，均无微软信誉签名）；2026-08-24 用户手动关闭 SAC 后恢复可用。SAC 关闭不可逆（重新开启需重置 Windows）。若再遇 App Control 拦截，先查 SAC 状态（Windows 安全中心 → 应用和浏览器控制）与 CodeIntegrity 事件日志（3076/3077）。
6. **admin 静态资源缓存**：admin 重建后浏览器需 Ctrl+Shift+R 硬刷新（nginx 强缓存），见 DEV-RULES §3.2。
7. **wsl --update 后 machine 卡 Starting / 52293 转发异常**：`wsl --update`（或 WSL 内核/组件升级）后，machine json 可能残留 `Starting=true`，Windows 侧到发行版 sshd 52293 连接被拒，客户端报 Cannot connect。镜像网络模式下内核更新后 wslservice 未完整复位所致。完整修复见 §7。
8. **WSL VM 空闲自动关闭（假掉线）**：WSL 默认 `vmIdleTimeout=60000ms`，VM 空闲约 60s 被自动关闭，表现为"掉线"；已通过 `.wslconfig` 设置 `[wsl2] vmIdleTimeout=-1` 与 `[general] instanceIdleTimeout=-1` 根治。若再出现类似掉线，先查 `.wslconfig` 是否仍含该配置（WSL 更新可能重置）。

---

## 7. WSL 更新后 Podman Machine 卡 Starting / 52293 转发异常修复 SOP

适用场景：`wsl --update`（或 WSL 内核/组件升级）后，`podman machine start` 卡在 `Currently starting`，客户端报 `Cannot connect`，Windows 侧到发行版 sshd 端口 52293 连接被拒；或 machine json 中 `Starting` 残留为 `true`。本 SOP 基于 2026-09-09 Forge 开发机实际修复过程整理。

关键文件与对象：
- machine json：`C:\Users\tank\.config\containers\podman\machine\wsl\podman-machine-default.json`
- machine / 发行版名：`podman-machine-default`（WSL 后端）
- 转发端口：52293（json 中 `SSH.Port`）

### 第一步：诊断与状态确认（先判定根因再动手）

```powershell
# 1. 确认 machine 状态：卡 Starting 时此处会持续显示 Starting / 客户端 Cannot connect
podman machine list

# 2. 确认发行版实际状态（区分"VM 已停"与"VM 在跑但转发坏"）
wsl -l -v

# 3. 检查 machine json 是否残留 Starting=true（卡死标记）
Get-Content 'C:\Users\tank\.config\containers\podman\machine\wsl\podman-machine-default.json'

# 4. 判定 52293 端口转发是否异常（TcpTestSucceeded 应为 True；wsl --update 后坏链时通常为 False）
Test-NetConnection -ComputerName 127.0.0.1 -Port 52293
```

关键判定点：
- json 中 `"Starting": true` 且 `wsl -l -v` 显示发行版 Running → 典型的"wslservice 未完整复位导致转发通道异常 + 客户端状态卡死"组合，按第二步处理。
- `wsl -l -v` 显示 Stopped → 直接走 `podman machine start` 正常生命周期即可，见第四步。
- 若发行版仍在运行，可用直启方式核对 systemd 是否真实健康（绕过 podman 客户端状态，避免误判）：

```powershell
# /proc/1/comm 应返回 systemd（证明 /etc/wsl.conf [boot] systemd=true 已生效）
wsl -d podman-machine-default -- sh -lc 'cat /proc/1/comm'
# 同法核对 sshd 是否监听 52293
wsl -d podman-machine-default -- sh -lc 'ss -tln | grep 52293'
```

### 第二步：Restart-Service wslservice（时机与前置条件）

时机：**仅当**满足第一步判定点（wsl --update 后、发行版 Running 但 52293 转发 refused、machine 卡 Starting）时执行。根因是 `.wslconfig` 启用 `networkingMode=mirrored` 时内核更新后 wslservice 未完整复位。

前置条件与影响提示：
- 需管理员权限的 PowerShell。
- **此操作会停止全部 WSL 发行版/会话**，执行前用 `wsl -l -v` 确认无其他发行版承载关键任务；本机故障场景下即为恢复手段。
- 服务复位后所有 WSL 实例会停止，属预期行为。

```powershell
# 管理员 PowerShell
Restart-Service wslservice
Start-Sleep -Seconds 5

# 确认发行版已被复位为 Stopped（此时不要直接 wsl -d 进入操作）
wsl -l -v

# 若个别实例仍残留运行，先全停冷启（可选兜底）
wsl --shutdown
```

### 第三步：machine json 状态回写（Starting=true → false 并刷新 LastUp）

时机：`podman machine start` 曾被中断/超时，或 json 中 `Starting` 仍为 `true` 导致 start 无法正常完成时，必须先清除残留标记再走正常生命周期。**先备份再修改。**

```powershell
$jsonPath = 'C:\Users\tank\.config\containers\podman\machine\wsl\podman-machine-default.json'

# 1. 备份
Copy-Item $jsonPath "$jsonPath.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# 2. 回写：Starting=true -> false，并将 LastUp 刷新为当前时刻
$j = Get-Content $jsonPath -Raw | ConvertFrom-Json
$j.Starting = $false
$j.LastUp   = (Get-Date).ToString('o')   # 输出形如 2026-09-09T21:30:00.0000000+08:00，与原格式同构

# 3. 保存：必须 UTF-8 无 BOM（Podman 解析带 BOM 的 json 会失败）
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($jsonPath, ($j | ConvertTo-Json -Depth 10), $utf8NoBom)

# 4. 复核写入结果
Get-Content $jsonPath
```

关键判定点：
- 文件必须保持 UTF-8 无 BOM（`New-Object System.Text.UTF8Encoding($false)` 写法不可省略）。
- `ConvertTo-Json -Depth` 需 ≥ 4（json 嵌套含 Resources/SSH/WSLHypervisor 层），用 10 更稳妥；切勿使用默认 Depth 2 造成字段截断。
- 修改范围**仅限** `Starting` 与 `LastUp` 两个字段，不触碰 `SSH.Port`、`ImagePath`、`WSLHypervisor` 等其余配置。

### 第四步：恢复正常生命周期并验证

```powershell
# 1. 经 podman machine 正常生命周期启动（勿用 wsl -d 直启替代）
podman machine start podman-machine-default

# 2. 等待并确认 machine Running、Starting 消失
podman machine list

# 3. 确认发行版与 systemd 真实健康
wsl -l -v
wsl -d podman-machine-default -- sh -lc 'cat /proc/1/comm'   # 期望 systemd

# 4. 52293 转发恢复
Test-NetConnection -ComputerName 127.0.0.1 -Port 52293        # TcpTestSucceeded: True

# 5. 容器与服务端到端验证（本机 9 容器，backend healthy，8080 200）
podman ps
Invoke-WebRequest -Uri 'http://127.0.0.1:8080/' -UseBasicParsing -TimeoutSec 15   # HTTP 200
```

### 预防性约定

- 日常统一使用 `podman machine start/stop` 管理生命周期；`wsl --terminate` 仅用于 stop 失败的强制停止兜底，且恢复仍须走 `podman machine start` 并等待 list 显示 Running，勿直接 `wsl -d` 进入操作。
- WSL 侧 `.wslconfig` 已配置 `[wsl2] vmIdleTimeout=-1` 与 `[general] instanceIdleTimeout=-1`，避免 VM 空闲约 60 秒被自动关闭造成新一轮"掉线"误判。
- 本机发行版内 podman 已与 Windows 侧统一为 6.1.1（rhcontainerbot COPR），后续升级保持两侧版本一致。
