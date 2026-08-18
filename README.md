# Forge — 全球化宠物用品 AI 独立站

## 架构概览

- **前端**: Nuxt 3 + Vue 3 + TypeScript + TailwindCSS + Shadcn-vue
- **后端**: Python 3.12 + FastAPI + DDD 架构
- **AI**: LangChain + OpenAI API + pgvector (RAG)
- **基础设施**: OCI K3s 双区域 (美西 + 阿姆斯特丹)
- **CI/CD**: Jenkins → Harbor → ArgoCD
- **数据库**: PostgreSQL 16 + pgvector (K3s StatefulSet)

## 项目结构

```
forge/
├── admin/           # 管理后台前端（Vue3 + Vite + UnoCSS）
├── portal-web/      # 用户端前端（Nuxt 3 SSR + Vue 3）
├── backend/         # FastAPI DDD 后端
├── ai-service/      # AI 推理微服务
├── gateway/         # Nginx 网关
├── k8s/             # K3s 生产部署（templates/ Helm 模板）
├── docker/          # Docker Compose 本地开发
├── uploads/         # 上传文件存储
└── docs/            # 架构文档（所有文档唯一存放位置）
```

## 快速开始

### 环境要求

| 组件 | 版本要求 |
|------|----------|
| Node.js | v24+ |
| Python | 3.11+ |
| Podman / Docker | 最新稳定版 |

### 1. 启动基础设施容器

PostgreSQL、Redis、MinIO 等依赖服务通过容器启动（使用 Podman 或 Docker）：

```bash
cd docker
podman compose up -d postgres redis minio

# 或启动全部基础设施
podman compose up -d
```

### 2. 启动后端 (FastAPI)

```bash
cd backend
pip install -e .
python run.py
```

后端运行在 `http://localhost:8000`，API 文档见 [docs/API-REFERENCE.md](docs/API-REFERENCE.md)。

### 3. 启动前端 (Nuxt 3)

```bash
cd portal-web
pnpm install
pnpm dev
```

前端运行在 `http://localhost:3000`。

### 更多运行方式

- 完整 Docker/Podman 本地部署：参见 [docs/DEPLOYMENT-MOP.md](docs/DEPLOYMENT-MOP.md)
- 生产环境 K3s 部署：参见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## 技术栈

| 层级 | 技术 |
|------|------|
| CDN | Cloudflare |
| 负载均衡 | OCI Load Balancer |
| 计算 | OCI K3s (美西 + 阿姆斯特丹) |
| 前端 | Nuxt 3 + Vue 3 + TS |
| 后端 | FastAPI (Python 3.12) |
| AI | LangChain + OpenAI API |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存 | Redis 7 Cluster |
| 对象存储 | MinIO (S3 兼容) |
| CI/CD | Jenkins + ArgoCD + Harbor |
| 认证 | JWT + OIDC |
| 支付 | Stripe (支持 135+ 币种) |

## 部署架构

- 入口: OCI LB → Traefik (K3s 内置)
- 出口: K3s Pods → 跳板机 → Internet
- 数据同步: PostgreSQL 主从复制 (US-West → EU-West)
- 网络策略: 仅允许 LB 入站 + 跳板机出站

## 区域配置

| 区域 | 集群 | 服务 |
|------|------|------|
| 北美 | US-West K3s | 全功能 (主) |
| 欧洲 | EU-West K3s | 全功能 + VAT/Klarna |
| 中东 | 复用 EU-West | 阿拉伯语 RTL 支持 |

## 文档索引

| 文档 | 说明 |
|------|------|
| [API-REFERENCE.md](docs/API-REFERENCE.md) | API 接口参考文档 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构设计文档 |
| [DDD-AGGREGATES.md](docs/DDD-AGGREGATES.md) | DDD 聚合设计文档 |
| [DEPLOYMENT-MOP.md](docs/DEPLOYMENT-MOP.md) | 本地开发环境 MOP 部署指南 |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | 生产环境部署文档 |
| [implementation-summary.md](docs/implementation-summary.md) | 实现总结 |
| [NETWORK-DESIGN.md](docs/NETWORK-DESIGN.md) | 网络架构设计文档 |
| [REQUIREMENT-AI-SERVICE.md](docs/REQUIREMENT-AI-SERVICE.md) | AI 服务需求文档 |
| [REQUIREMENT-BACKEND.md](docs/REQUIREMENT-BACKEND.md) | 后端需求文档 |
| [REQUIREMENT-FRONTEND.md](docs/REQUIREMENT-FRONTEND.md) | 前端需求文档 |

## License

Private — All rights reserved
