---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_ba03261c9f9811f1a413525400287e28
    ReservedCode1: bIY42VwFHD0Zi/Ejipr+/dQBE7knqDcsMPzkltv2f7QeniSaQs3noCX/Fx08X7l914K/YrjrMrdpBW7lIOGtwmE/mIyYaMBM0ErTJ6oyLdg6xkYL2C6ipATZksKkvq3xNFDkJsTHrCTIxFV5GD7RmP70O70J5U618RyyLMBj/i1MJMrxGtbamPWTlbg=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_ba03261c9f9811f1a413525400287e28
    ReservedCode2: bIY42VwFHD0Zi/Ejipr+/dQBE7knqDcsMPzkltv2f7QeniSaQs3noCX/Fx08X7l914K/YrjrMrdpBW7lIOGtwmE/mIyYaMBM0ErTJ6oyLdg6xkYL2C6ipATZksKkvq3xNFDkJsTHrCTIxFV5GD7RmP70O70J5U618RyyLMBj/i1MJMrxGtbamPWTlbg=
---

# Forge 本地开发环境基线（INFRA-BASELINE）

> 适用范围：Windows 11 + WSL2 + podman machine 容器化开发环境。
> 本文档是环境事实基线 + 故障恢复 SOP。**环境问题必须先查本文档，禁止从头排查**。
> 最后更新：2026-08-24（固化原因：8080 端口转发问题重复发生且每次从头排查，浪费大量时间）

---

## 1. 环境拓扑（事实基线）

| 组件 | 值 |
|---|---|
| 操作系统 | Windows 11 (Build 26200) |
| WSL | 2.7.11，`.wslconfig` 配置 `networkingMode=mirrored`（镜像网络模式，全局生效） |
| podman | 6.0.2，machine `podman-machine-default`（WSL 后端，rootless） |
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
*（内容由AI生成，仅供参考）*
