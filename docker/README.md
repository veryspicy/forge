# Docker Compose — 本地开发环境

> 详细部署步骤请参阅 [DEPLOYMENT-MOP.md](../docs/DEPLOYMENT-MOP.md)

## 使用说明

> **启动容器统一走 `up.ps1`**：它在 `podman-compose up -d` 之前强制执行启动前检查（`preflight.ps1`）。
> 禁止绕过直接 `podman-compose up -d`，否则机器状态/水位/悬空镜像不会被前置处理。

```powershell
cd D:\codeRepo\forge\docker

# 启动全部服务（自动执行启动前检查：machine 拉起 + 水位体检 + 停止容器/悬空镜像清理）
powershell -ExecutionPolicy Bypass -File .\up.ps1

# 启动指定服务（preflight 同样先生效）
powershell -ExecutionPolicy Bypass -File .\up.ps1 -Service backend,gateway

# 启动 + HTTP 冒烟自检（backend / ai-service / portal-web / gateway）
powershell -ExecutionPolicy Bypass -File .\up.ps1 -Smoke

# 单独做启动前检查（不启动容器，可随时跑）
powershell -ExecutionPolicy Bypass -File .\preflight.ps1
powershell -ExecutionPolicy Bypass -File .\preflight.ps1 -Strict      # 超阈值直接中止
powershell -ExecutionPolicy Bypass -File .\preflight.ps1 -SkipPrune   # 只体检不清理

# 重建单服务（内部同样先跑 preflight）
powershell -ExecutionPolicy Bypass -File .\rebuild-service.ps1 -Service backend

# 查看日志 / 停止
podman compose logs -f backend
podman compose down
```

## 启动前检查（preflight.ps1）

每次容器启动前必跑，替代任何定时任务。检查项与阈值：

| 项目 | 说明 | 默认阈值 | 超阈值行为 |
|------|------|---------|-----------|
| podman machine | 未运行则自动 `machine start` 并轮询 API 就绪 | — | 起不来则退出码 2，阻止启动 |
| machine vhdx | 宿主机上的实体文件大小（不会自动缩小） | > 100 GB | 告警，`-Strict` 下中止 |
| 宿主磁盘剩余 | vhdx 所在盘剩余空间 | < 20 GB | 告警，`-Strict` 下中止 |
| 悬空镜像数 | `podman images -f dangling=true` 计数 | > 100 | 告警，`-Strict` 下中止 |
| 已停止容器 | `container prune -f` 清理 | — | 直接清理 |
| 悬空镜像 | `image prune -f` 清理，硬超时 180s | — | 超时则留在后台并告警，**期间禁止并发 podman 命令** |

说明：

- 由 `--no-cache` 构建产生的悬空镜像层与活跃镜像共享，prune 回收不掉属预期，不做 `image prune -a`（会删其它 tag）。
- vhdx 只增不减，回收空闲块需停机 compact（5400rpm 机械盘上极慢，非必要不做）。日志落 `temp/preflight-<时间戳>.log`。

## 服务清单

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| postgres | forge-postgres | 5433 | PostgreSQL 16 + pgvector |
| redis | forge-redis | 6380 | Redis 7，密码 `redispass` |
| minio | forge-minio | 9002 (API) / 9003 (Console) | 对象存储 |
| rocketmq-namesrv | forge-namesrv | 9876 | NameServer |
| rocketmq-broker | forge-broker | 10911 / 10912 | Broker |
| backend | forge-backend | 8002 | FastAPI 后端 |
| ai-service | forge-ai | 8001 | AI 推理服务 |
| portal-web | forge-portal-web | 3000 | Nuxt 3 前端 |
| admin | forge-admin | — (经 gateway) | 管理端静态站 |
| gateway | forge-gateway | 8080 | Nginx 入口 |

## 环境变量

在项目根目录或 `docker/` 下创建 `.env` 文件：

```env
OPENAI_API_KEY=sk-your-key-here
```

容器内已预设以下默认值（`docker-compose.yml` 中 `x-common-vars`）：

```yaml
DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/forge
REDIS_URL: redis://redis:6379/0
MINIO_ENDPOINT: minio:9000
MINIO_ACCESS_KEY: minioadmin
MINIO_SECRET_KEY: minioadmin
ROCKETMQ_PROXY: http://rocketmq-proxy:8081
JWT_SECRET_KEY: dev-secret-key-change-in-production
```
