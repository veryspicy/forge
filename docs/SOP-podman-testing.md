---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_f5cd389d8dd611f196d8525400f8a581
    ReservedCode1: NIh/gXn7EPI8+6aepYgl/tGz0NDEEoKv/m4lGUDT+38My1C/3tfhhv2shsOLO2/ZdIvbMhWYWGfHc2BJFoR+8nMoIa0QI2s91RajSCTJiPWXZ9QEHPCXqe+6o6s6/mEHzBQLPbVE4nGDRGGF+rlW/5ESWnr1bbwfFgzLAz67nFKoW5vh+CiM2xMvTok=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_f5cd389d8dd611f196d8525400f8a581
    ReservedCode2: NIh/gXn7EPI8+6aepYgl/tGz0NDEEoKv/m4lGUDT+38My1C/3tfhhv2shsOLO2/ZdIvbMhWYWGfHc2BJFoR+8nMoIa0QI2s91RajSCTJiPWXZ9QEHPCXqe+6o6s6/mEHzBQLPbVE4nGDRGGF+rlW/5ESWnr1bbwfFgzLAz67nFKoW5vh+CiM2xMvTok=
---

# Podman 测试环境部署、发布与功能测试 SOP

> **项目路径**: `D:\codeRepo\forge`
> **容器运行时**: Podman (WSL2 后端)
> **Shell**: PowerShell 5.1
> **编排方式**: `podman-compose`，统一由 `docker-compose.yml` 管理全部服务
> **最后更新**: 2026-08-02

---

## 1. 环境总览

### 1.1 服务拓扑

所有服务由 `D:\codeRepo\forge\docker\docker-compose.yml` 统一编排，project name 固定为 `docker`。

```
┌─────────────────────────────────────────────────────────┐
│                  Podman Machine (WSL2)                   │
│                                                         │
│  Network: forge (bridge)                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ postgres │ │  redis   │ │  minio   │ │ rocketmq │   │
│  │   :5432  │ │  :6379   │ │:9000/9001│ │:9876/10911│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ backend  │ │ai-service│ │ frontend │ │  admin   │   │
│  │  :8000   │ │  :8001   │ │  :3000   │ │ 8080:80  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 1.2 端口与服务清单

| 服务 | 容器名 | 端口映射 | 部署方式 |
|------|--------|---------|---------|
| PostgreSQL 16 | `forge-postgres` | 5432:5432 | Compose |
| Redis 7 | `forge-redis` | 6379:6379 | Compose |
| MinIO | `forge-minio` | 9000:9000, 9001:9001 | Compose |
| RocketMQ NameServer | `forge-namesrv` | 9876:9876 | Compose |
| RocketMQ Broker | `forge-broker` | 10911:10911, 10912:10912 | Compose |
| Backend (FastAPI) | `forge-backend` | 8000:8000 | Compose |
| AI Service | `forge-ai` | 8001:8001 | Compose |
| Frontend (Nuxt 3) | `forge-portal-web` | 3000:3000 | Compose |
| Admin (Soybean Admin) | `forge-admin` | 8080:80 | Compose |
| Init Admin (一次性) | `forge-init-admin` | — | Compose（run to completion） |

### 1.3 网络

| 网络名 | 来源 | 说明 |
|--------|------|------|
| `forge` | `docker-compose.yml` 显式定义 (`networks.forge.driver: bridge`) | 所有服务声明的目标网络，容器间 DNS 解析通过此网络进行 |
| `docker_forge` | podman-compose 根据 project name `docker` 自动创建的默认网络 | **服务明确指定 `networks: forge` 后不应落入此网络**。若某容器仅出现在 `docker_forge` 中，说明网络配置漂移，须修复 |

### 1.4 关键凭据

| 组件 | 用户名 | 密码 / 密钥 |
|------|--------|-------------|
| PostgreSQL | `postgres` | `postgres` |
| Redis | — | `redispass` |
| MinIO | `minioadmin` | `minioadmin` |
| JWT | — | `dev-secret-key-change-in-production` |
| Admin 登录 | `admin@forge.dev` | `admin123`（种子脚本创建） |

---

## 2. 前置条件

### 2.1 Podman Machine

```powershell
# 确认 machine 存在且运行
podman machine list
# 预期: "Currently running" 或 "Running"

# 若未启动
podman machine start

# DNS 检查（见 7.1 节）
podman machine ssh -- cat /etc/resolv.conf
# 必须指向公共 DNS（223.5.5.5 / 8.8.8.8），不得为 192.168.127.1
```

### 2.2 统一命令前缀

本文档所有 compose 命令使用此前缀：

```powershell
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml
```

---

## 3. 测试环境搭建 SOP

### 3.1 从零启动（全量）

```powershell
# Step 1: 确保 Machine 运行 + DNS 正常
podman machine start
podman machine ssh -- cat /etc/resolv.conf

# Step 2: 构建所有镜像并启动全部服务
cd D:\codeRepo\forge\docker
podman-compose --project-name docker -f docker-compose.yml up -d --build

# Step 3: 等待 backend healthy
podman wait --condition=healthy forge-backend

# Step 4: 验证冒烟测试（见第 6 节）
```

### 3.2 分阶段启动（排障推荐）

按依赖顺序逐层启动，便于定位问题：

```powershell
cd D:\codeRepo\forge\docker
PC="podman-compose --project-name docker -f docker-compose.yml"

# 层 1: 基础设施
$PC up -d postgres redis minio rocketmq-namesrv rocketmq-broker

# 确认基础设施 healthy 后再继续
podman ps --filter name=forge --format "table {{.Names}}\t{{.Status}}"

# 层 2: 后端
$PC up -d backend ai-service
podman wait --condition=healthy forge-backend

# 层 3: migration + seed（backend healthy 后）
podman exec forge-backend alembic upgrade head

# 层 4: 前端 + Admin
$PC up -d portal-web admin

# 层 5: 初始化 Admin 用户（一次性）
$PC up -d init-admin
```

### 3.3 数据库操作必须在容器内执行

```
✅ podman exec forge-backend alembic upgrade head
✅ podman exec forge-backend alembic revision --autogenerate -m "..."
❌ cd D:\codeRepo\forge\backend && alembic upgrade head  （直连本地 DB，凭据和网络可能不一致）
```

---

## 4. 部署规则

### 4.1 重建触发条件矩阵

| 服务 | 变更内容 | 操作 | 命令 |
|------|---------|------|------|
| **Backend** | `.py` 源码 | 重启容器 | `$PC restart backend` |
| **Backend** | `pyproject.toml` / 依赖 | 重建镜像 + 重建容器 | `$PC build backend` → `$PC up -d --force-recreate backend` |
| **Backend** | Dockerfile | 重建镜像 + 重建容器 | 同上 |
| **Frontend** | `.vue` / `.ts` / `.js` / CSS | **无操作**（HMR 自动生效） | — |
| **Frontend** | `locales/*.json` | **无操作**（HMR 自动生效） | — |
| **Frontend** | `nuxt.config.ts` | 重建镜像 + 重建容器 | `$PC build portal-web` → `$PC up -d --force-recreate frontend` |
| **Frontend** | `package.json` / `pnpm-lock.yaml` | 重建镜像 + 重建容器 | 同上 |
| **Frontend** | `.nuxt` 缓存异常 500 | 清缓存并重启 | `podman exec forge-portal-web rm -rf /app/.nuxt /app/node_modules/.cache` → `$PC restart portal-web` |
| **Admin** | **任何源码**（`.vue` / `.ts` / `.css` / `.json`） | **重建镜像 --no-cache** + 重建容器 | `$PC build --no-cache admin` → `$PC up -d --force-recreate admin` |
| **Admin** | `package.json` / `pnpm-lock.yaml` | 重建镜像 --no-cache + 重建容器 | 同上 |
| **Admin** | `nginx.conf` | 重建镜像 --no-cache + 重建容器 | 同上 |
| **Admin** | `Dockerfile` | 重建镜像 --no-cache + 重建容器 | 同上 |
| **基础设施** | compose 配置 | `down` → `up -d` | `$PC down postgres; $PC up -d postgres` |

> **Admin 为何必须 `--no-cache`**: Vite 构建产物固化为静态文件打入镜像，Docker 层缓存可能命中旧 `COPY . .` 层导致源码改动未生效。Admin 无 HMR，必须确保每次源码改动后新镜像包含最新构建产物。

### 4.2 部署顺序

严格按依赖顺序执行，不可跳过：

```
1. Machine Start + DNS 检查
2. 基础设施（postgres / redis / minio / rocketmq）
3. Backend + AI Service（依赖基础设施 healthy）
4. Migration + Seed（依赖 backend healthy）
5. Frontend + Admin（依赖 backend healthy）
6. Init Admin（一次性，依赖 backend healthy）
```

### 4.3 禁止事项

| 禁止 | 原因 | 替代 |
|------|------|------|
| 使用 `podman run` 管理 compose 内服务 | 配置漂移，compose 无法追溯 | compose 命令 |
| 修改 compose 内 `container_name` | nginx.conf / 服务间 DNS 解析依赖容器名 | 保持不变 |
| 在容器内直接改配置文件不加卷挂载/不回写源码 | 容器重建后丢失 | 修改源码 → 重建镜像 |
| 跨服务并行启动（backend 未 healthy 时启动 frontend） | 前端启动后 API 调用失败 | 逐层等待依赖就绪 |
| 本地直连数据库执行 migration | 网络/凭据差异导致状态不一致 | 在 backend 容器内执行 |
| `podman compose up`（不带 `-d`） | PowerShell 下易挂起/截断 | 始终带 `-d` |

---

## 5. 功能测试规则

### 5.1 冒烟测试（每次部署后必做）

```powershell
# === 基础设施层 ===
podman exec forge-postgres pg_isready -U postgres      # 预期: accepting connections
podman exec forge-redis redis-cli -a redispass ping     # 预期: PONG

# === Backend ===
curl -s http://localhost:8000/health                    # 预期: {"status":"ok"}
curl -s -o nul -w "%{http_code}" http://localhost:8000/docs  # 预期: 200

# === Frontend ===
curl -s -o nul -w "%{http_code}" http://localhost:3000   # 预期: 200

# === Admin ===
curl -s -o nul -w "%{http_code}" http://localhost:8080   # 预期: 200
curl -s http://localhost:8080/api/v1/health              # API 代理: 预期 {"status":"ok"}
curl -s -o nul -w "%{http_code}" http://localhost:8080/dashboard  # SPA fallback: 预期 200
```

### 5.2 端到端验证（代码变更后）

| 变更模块 | 验证步骤 |
|---------|---------|
| 后端 API | ① `curl http://localhost:8000/docs` 确认新接口出现 ② 直接调用验证 ③ 通过 Admin 代理 (`localhost:8080/api/...`) 再次调用，确认路径一致 |
| 前端页面 | 浏览器访问对应页面，Network 面板确认无 404/500，数据加载正常 |
| Admin 后台 | ① 浏览器硬刷新（Ctrl+Shift+R）绕过 CDN 缓存 ② 页面正常加载 ③ API 调用路径与后端路由一致 |
| 数据库 Migration | ① `podman exec forge-backend alembic current` 确认版本 ② 查询新表/字段存在 ③ 种子数据可正常查询 |

### 5.3 网络连通性校验（预防漂移）

```powershell
# 所有 forge 容器应处于 forge 网络
podman inspect forge-backend --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
podman inspect forge-admin --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# 预期输出均包含: forge

# Admin → Backend 容器名 DNS 解析
podman exec forge-admin wget -qO- http://forge-backend:8000/health
# 预期: {"status":"ok"}

# 若某容器不在 forge 网络中，手动接入
podman network connect forge forge-backend
```

---

## 6. 发布规则

### 6.1 发布前检查清单

发布（合并到 main + 打 tag）前必须全部通过：

- [ ] 冒烟测试全部通过（第 5.1 节）
- [ ] 端到端验证通过（涉及模块见第 5.2 节）
- [ ] 网络连通性校验通过（第 5.3 节）
- [ ] git status 干净，当前分支代码已全部提交
- [ ] 分支已合并到 dev 并通过 CI（如有）
- [ ] `docker-compose.yml` 中无临时调试配置（如暴露的调试端口、非标准环境变量）
- [ ] 无硬编码的本地路径（如 `C:\codeRepo\...`）

### 6.2 版本号管理

遵循 [GIT-WORKFLOW.md](./GIT-WORKFLOW.md) 中的 Semantic Versioning：

| 变更类型 | 示例 |
|----------|------|
| 不兼容的 API 变更 | `v1.2.3` → `v2.0.0` |
| 向下兼容的新功能 | `v1.2.3` → `v1.3.0` |
| 向下兼容的 Bug 修复 | `v1.2.3` → `v1.2.4` |

### 6.3 镜像标签策略

本地测试环境不要求 tag，开发中统一使用 `latest`。发版时：

```powershell
# 为发版构建带版本 tag 的镜像
podman-compose --project-name docker -f docker-compose.yml build
podman tag forge-backend:latest forge-backend:v1.3.0
podman tag forge-admin:latest forge-admin:v1.3.0
podman tag forge-portal-web:latest forge-portal-web:v1.3.0
```

---

## 7. 故障排查

### 7.1 Podman Machine DNS 不可用

**症状**: `podman build` 中 `pip install` / `npm install` 报 DNS 解析错误

**根因**: Machine (WSL2) 内 `/etc/resolv.conf` 指向不可达的内网代理 `192.168.127.1`

**修复**:
```powershell
podman machine ssh -- sudo sh -c "echo nameserver 223.5.5.5 > /etc/resolv.conf"
podman machine stop
podman machine start
```

### 7.2 Redis 认证失败

**症状**: Backend 日志报 `NOAUTH Authentication required`

**根因**: compose 中 `REDIS_URL` 未带密码但 Redis 配置了 `requirepass redispass`

**修复**: 修改 `docker-compose.yml` 中 `REDIS_URL`：
```yaml
# 修正前
REDIS_URL: redis://redis:6379/0
# 修正后
REDIS_URL: redis://:redispass@redis:6379/0
```

### 7.3 Admin 502 — nginx 无法解析 backend

**症状**: Admin 首页正常，API 请求返回 502

**排查**:
```powershell
# 1. backend 是否在 forge 网络中
podman inspect forge-backend --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'

# 2. 若缺失 forge 网络，手动连接
podman network connect forge forge-backend

# 3. Admin 能否解析 backend 容器名
podman exec forge-admin wget -qO- http://forge-backend:8000/health

# 4. nginx upstream 是否正确
podman exec forge-admin cat /etc/nginx/conf.d/default.conf | findstr upstream
# 应为: forge-backend:8000
```

### 7.4 Frontend 500 — .nuxt 缓存异常

**症状**: Nuxt 首页返回 500，日志显示 `Cannot find module`

**修复**:
```powershell
podman exec forge-portal-web rm -rf /app/.nuxt /app/node_modules/.cache
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml restart portal-web
```

### 7.5 Compose 命令挂起/截断

**症状**: PowerShell 中 `podman compose up` 无响应或 Traceback

**修复**: 始终使用 `-d` 参数；对单服务操作使用 `podman-compose ... up -d <service>`

### 7.6 Admin 源码改动未生效

**症状**: 修改 Admin 源码后 `up -d --force-recreate` 仍然看到旧页面

**修复**: 必须使用 `--no-cache` 重建：
```powershell
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml build --no-cache admin
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml up -d --force-recreate admin
# 浏览器 Ctrl+Shift+R 硬刷新
```

---

## 8. 速查表

### 8.1 常用命令

```powershell
# 设置别名（建议加入 PowerShell profile）
$PC = "podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml"

# 全量启动
$PC up -d --build

# 全量停止
$PC down

# 查看所有 forge 容器状态
podman ps --filter name=forge --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 重建单个服务
$PC build --no-cache admin
$PC up -d --force-recreate admin

# 查看容器日志
podman logs --tail 50 forge-backend

# 进入容器 Shell
podman exec -it forge-backend sh

# 数据库迁移
podman exec forge-backend alembic upgrade head

# 网络连通性检查
podman exec forge-admin wget -qO- http://forge-backend:8000/health
```

### 8.2 服务端口

| 服务 | 地址 |
|------|------|
| Backend API | http://localhost:8000 |
| Backend Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| Admin | http://localhost:8080 |
| MinIO Console | http://localhost:9001 |
| AI Service | http://localhost:8001 |

### 8.3 文档索引

| 文档 | 说明 |
|------|------|
| `docs/SOP-podman-testing.md`（本文档） | 测试环境部署、测试、发布全流程 |
| `docs/DEV-RULES.md` | 开发规则（版本管理、缓存重启、重建策略） |
| `docs/SOP-compose-rebuild.md` | Compose 重建策略（HMR 说明、重建加速） |
| `docs/GIT-WORKFLOW.md` | Git Flow 分支模型、提交规范、发版流程 |
| `docs/DEPLOYMENT-MOP.md` | 首次环境搭建详细步骤（含非容器化方式） |
| `docker/docker-compose.yml` | 服务定义唯一真相来源 |

---

*最后更新：2026-08-02*
*（内容由AI生成，仅供参考）*
