# Docker Compose — 本地开发环境

> 详细部署步骤请参阅 [DEPLOYMENT-MOP.md](../docs/DEPLOYMENT-MOP.md)

## 使用说明

```bash
# 启动全部服务
cd D:\codeRepo\forge\docker
podman compose up -d
# 或: docker compose up -d

# 查看日志
podman compose logs -f backend

# 停止所有服务
podman compose down

# 重建并启动
podman compose up -d --build
```

## 服务清单

| 服务 | 端口 | 说明 |
|------|------|------|
| postgres | 5432 | PostgreSQL 16 + pgvector |
| redis | 6379 | Redis 7，密码 `redispass` |
| minio | 9000 (API) / 9001 (Console) | 对象存储 |
| rocketmq-namesrv | 9876 | NameServer |
| rocketmq-broker | 10911 | Broker |
| backend | 8000 | FastAPI 后端 |
| ai-service | 8001 | AI 推理服务 |
| frontend | 3000 | Nuxt 3 前端 |

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
