---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_419836126ef011f184585254007bceed
    ReservedCode1: /OfFOZ0FtXMtDlExeQHLacmMdT7eG1BQaGCn/Swq/B2wYbAVB+RC0Vux07eyVadRQlY6RxlHYFO9IBJ0kR85bqwoNFLUwvFEniTC7ccqNTcHZ4V1iXPqUMMNPme7g0NjRzVqu/cLk5YRuyebZNcRd6wM3JWwxBgQLQxMLFMzjWYVIafnaCiPOQF/9Ec=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_419836126ef011f184585254007bceed
    ReservedCode2: /OfFOZ0FtXMtDlExeQHLacmMdT7eG1BQaGCn/Swq/B2wYbAVB+RC0Vux07eyVadRQlY6RxlHYFO9IBJ0kR85bqwoNFLUwvFEniTC7ccqNTcHZ4V1iXPqUMMNPme7g0NjRzVqu/cLk5YRuyebZNcRd6wM3JWwxBgQLQxMLFMzjWYVIafnaCiPOQF/9Ec=
---

# Forge — 本地开发环境部署 MOP (Method of Procedure)

> **项目路径**: `D:\codeRepo\forge`  
> **容器运行时**: Podman / Docker  
> **目标**: 一键拉起全部中间件及后端/前端/AI 服务  
> **最后更新**: 2026-06-23

---

## 前置条件

| 项目 | 最低版本 | 验证命令 |
|------|---------|---------|
| Podman (推荐) 或 Docker | 4.x / 27+ | `podman version` 或 `docker version` |
| Podman Compose / Docker Compose | 2.x | `podman-compose version` 或 `docker compose version` |
| Python | 3.11+ | `python --version` |
| Node.js | 20+ | `node --version` |
| pnpm | 9+ | `pnpm --version` |

---

## Step 1: 基础设施中间件

### 1.1 启动全部中间件容器

```bash
cd D:\codeRepo\forge\docker

# 使用 Podman (推荐)
podman compose up -d postgres redis minio rocketmq-namesrv rocketmq-broker

# 或使用 Docker
docker compose up -d postgres redis minio rocketmq-namesrv rocketmq-broker
```

**预期结果**: 5 个容器启动并处于 healthy 状态。

| 容器名称 | 端口 | 说明 |
|----------|------|------|
| forge-postgres | 5432 | PostgreSQL 16 + pgvector 向量扩展 |
| forge-redis | 6379 | Redis 7，密码 `redispass` |
| forge-minio | 9000 (API) / 9001 (Console) | 对象存储 |
| forge-namesrv | 9876 | RocketMQ NameServer |
| forge-broker | 10911 | RocketMQ Broker |

### 1.2 验证中间件

```bash
# PostgreSQL
podman exec forge-postgres pg_isready -U postgres

# Redis
podman exec forge-redis redis-cli -a redispass ping
# 预期: PONG

# MinIO
# 浏览器打开 http://localhost:9001
# 用户名: minioadmin / 密码: minioadmin
```

### 1.3 数据库迁移

```bash
cd D:\codeRepo\forge\backend

# 安装 Python 依赖
pip install -e ".[dev]"

# 执行数据库迁移
alembic upgrade head
```

> 若 `alembic upgrade head` 报错，说明 migration 目录可能尚未初始化。此时直接依赖 SQLAlchemy `create_all` 自动建表即可。

---

## Step 2: 后端 API 服务

### 2.1 配置环境变量

编辑 `D:\codeRepo\forge\backend\.env`，确保以下变量正确：

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/forge
REDIS_URL=redis://:redispass@localhost:6379/0
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=true
REGION=na
OPENAI_API_KEY=sk-your-key-here
```

### 2.2 启动后端

```bash
cd D:\codeRepo\forge\backend

# 开发模式 (热重载)
python run.py
# 或
uvicorn forge.main.application:app --host 0.0.0.0 --port 8000 --reload
```

**预期结果**: FastAPI 应用在 `http://localhost:8000` 启动。

### 2.3 验证后端

```bash
# 健康检查
curl http://localhost:8000/health

# API 文档
# 浏览器打开 http://localhost:8000/docs
```

---

## Step 3: AI 推理服务 (可选)

```bash
cd D:\codeRepo\forge

# 方式一: Docker Compose
cd docker
podman compose up -d ai-service

# 方式二: 直接运行 (若无 ai-service 目录，后端内置 AI 模块)
cd backend
# AI 聊天 WebSocket 由后端 forge.api.websocket.chat 提供
# 无需单独启动
```

**预期结果**: AI 服务在 `http://localhost:8001` 启动（如使用独立服务）。

---

## Step 4: 前端 Nuxt 3 应用

### 4.1 安装依赖

```bash
cd D:\codeRepo\forge\frontend

# 安装依赖
pnpm install

# 若 pnpm install 报 ERR_PNPM_IGNORED_BUILDS，执行:
pnpm approve-builds
# 用空格选中所有包 → 回车 → 输入 y 确认
```

### 4.2 配置环境变量

编辑 `D:\codeRepo\forge\frontend\.env`（或 `nuxt.config.ts` 中的 runtimeConfig）：

```env
NUXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
NUXT_PUBLIC_AI_CHAT_BASE=http://localhost:8001
NUXT_PUBLIC_REGION=na
NUXT_PUBLIC_DEFAULT_CURRENCY=USD
```

### 4.3 启动前端

```bash
cd D:\codeRepo\forge\frontend

# 开发模式
pnpm dev
```

**预期结果**: Nuxt 3 SSR 应用在 `http://localhost:3000` 启动。

### 4.4 验证前端

```bash
# 浏览器打开
# http://localhost:3000        — 首页
# http://localhost:3000/products  — 商品列表
# http://localhost:3000/cart      — 购物车
# http://localhost:3000/checkout  — 结算
# http://localhost:3000/pets      — 宠物档案
# http://localhost:3000/orders    — 订单
# http://localhost:3000/chat      — AI 聊天
```

---

## Step 5: 一键部署 (完整环境)

```bash
cd D:\codeRepo\forge\docker

# 拉取并启动全部服务
podman compose up -d

# 查看日志
podman compose logs -f backend

# 停止所有服务
podman compose down

# 重建镜像并启动
podman compose up -d --build
```

---

## 故障排查

### PostgreSQL 连接失败

```bash
# 检查容器状态
podman ps -a --filter name=forge-postgres

# 检查日志
podman logs forge-postgres

# 重启容器
podman restart forge-postgres
```

### Redis 连接失败

```bash
# 检查 Redis 是否要求密码
podman exec forge-redis redis-cli -a redispass ping
```

### pnpm install 报 ERR_PNPM_IGNORED_BUILDS

```bash
pnpm approve-builds
# 空格选中所有包 → 回车 → y 确认
# 然后重新 pnpm install
```

### 前端页面空白或路由 404

```bash
# 检查 Nuxt dev server 是否正常运行
curl http://localhost:3000

# 查看终端日志中的错误信息
```

---

## 服务端口汇总

| 服务 | 端口 | 地址 |
|------|------|------|
| 前端 (Nuxt 3) | 3000 | http://localhost:3000 |
| 后端 (FastAPI) | 8000 | http://localhost:8000 |
| API 文档 (Swagger) | 8000 | http://localhost:8000/docs |
| AI 服务 | 8001 | http://localhost:8001 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| MinIO API | 9000 | http://localhost:9000 |
| MinIO Console | 9001 | http://localhost:9001 |
| RocketMQ NameServer | 9876 | localhost:9876 |
| RocketMQ Broker | 10911 | localhost:10911 |
*（内容由AI生成，仅供参考）*
