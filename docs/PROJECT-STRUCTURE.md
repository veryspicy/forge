# Forge — 项目目录结构说明

> 所有文档、SOP 规范、设计决策必须放在 `docs/` 目录下，禁止散落在项目根目录。

---

## 1. 根目录

```
forge/
├── README.md                  # 项目入口说明
├── .github/workflows/         # GitHub Actions CI/CD
│   └── ci-cd.yml              # CI/CD 流程定义
├── admin/                     # 管理后台前端（Vue3 + Vite）
├── ai-service/                # AI 对话服务（Python/FastAPI）
├── backend/                   # 主后端服务（Python/FastAPI + DDD）
├── portal-web/                # 用户端前端（Nuxt3 + Vue3 + i18n）
├── gateway/                   # 网关（Nginx 反向代理）
├── docker/                    # Docker Compose 编排
│   ├── docker-compose.yml     # 本地开发编排文件
│   └── Containerfile.pgvector # pgvector 扩展镜像（备用）
├── docs/                      # 【所有文档的唯一存放位置】
├── k8s/                       # K3s 生产部署配置
└── uploads/                   # 上传文件存储（含 .gitkeep）
```

### 文档存放规则

| 文件类型 | 存放位置 | 示例 |
|---------|---------|------|
| 架构设计 | `docs/ARCHITECTURE.md` | 技术栈、分层、DDD 聚合 |
| API 规范 | `docs/API-REFERENCE.md` | 接口定义 |
| 需求文档 | `docs/REQUIREMENT-*.md` | 各模块需求 |
| 部署相关 | `docs/DEPLOYMENT*.md` | 部署手册、MOP |
| SOP/操作规范 | `docs/SOP-*.md` | Compose 重建策略 |
| 开发日志 | `docs/DEVELOPMENT-LOG.md` | 阶段完成记录 |
| 实现总结 | `docs/implementation-summary.md` | 功能实现汇总 |

---

## 2. portal-web/ — 用户端前端

```
portal-web/
├── Dockerfile                 # Docker 镜像构建（node:22-alpine + pnpm）
├── .npmrc                     # npm/pnpm 镜像源（registry.npmmirror.com）
├── package.json / pnpm-lock.yaml
├── nuxt.config.ts             # Nuxt 配置（SSR + i18n + TailwindCSS）
├── tsconfig.json
├── vitest.config.ts           # 单元测试配置（tests/）
├── app/                       # 【Nuxt 应用主目录 → bind-mount 到容器 /app/app】
│   ├── app.vue                # 根组件
│   ├── pages/                 # 页面组件（自动路由）
│   │   ├── index.vue          # 首页
│   │   ├── products.vue       # 产品列表
│   │   ├── products/[id].vue  # 产品详情
│   │   ├── cart.vue           # 购物车
│   │   ├── orders.vue         # 订单列表
│   │   ├── pets.vue           # 宠物管理
│   │   └── admin/             # 管理端页面（orders/pricing/products/...）
│   ├── components/            # 可复用组件
│   │   ├── AppHeader.vue      # 顶部导航栏（含多语言/货币切换）
│   │   ├── CartDrawer.vue     # 购物车侧边栏
│   │   ├── OrderStatusBadge.vue
│   │   ├── admin/             # 管理端组件（DataTable/StatCard/...）
│   │   ├── diy/               # DIY 装修组件（DiyBanner/DiyGoodsList/...）
│   │   └── products/          # 产品相关组件
│   │       ├── ProductCard.vue
│   │       └── FilterSidebar.vue
│   ├── composables/           # 组合式函数（API 调用、状态管理）
│   ├── i18n/                  # 国际化配置
│   │   └── locales/           # 【翻译文件：en/zh/ar/de/fr.json】
│   ├── layouts/               # 布局（default/admin）
│   ├── stores/                # Pinia 状态（auth/cart/order/pet/...）
│   ├── server/                # Nuxt API 路由（BFF 层）
│   └── utils/                 # 工具函数
├── i18n/                      # i18n 配置与 locales
├── server/                    # Nitro API 路由（server/api/v1/[...path].ts 代理）
├── tests/                     # Vitest 单元测试（components/stores/pages）
├── node_modules/              # 依赖（容器内安装，本地用于 IDE）
└── .nuxt/                     # Nuxt 构建缓存
```

### 前端 build-mount 与 HMR
- `docker-compose.yml` 中将 `../portal-web/app` bind-mount 到容器内 `/app/app`
- Nuxt dev server 开启 HMR（Hot Module Replacement）
- **改任何 `.vue/.ts` 源码或 `i18n/locales/*.json` 翻译文件：等 HMR 生效即可，无需重建镜像**

---

## 3. admin/ — 管理后台

```
admin/
├── Dockerfile                 # 多阶段构建（node:20-alpine → nginx:alpine）
├── .npmrc                     # npm 镜像源
├── package.json
├── nginx.conf                 # Nginx SPA fallback + /api 反向代理
├── src/                       # Vue3 + Vite 源码
├── public/
└── dist/                      # 构建产物（npm run build）
```

---

## 4. backend/ — 主后端

```
backend/
├── Dockerfile                 # Python 3.12-slim（uvicorn --reload）
├── pyproject.toml / uv.lock   # 依赖声明（uv 管理）
├── alembic.ini                # 数据库迁移配置
├── run.py                     # FastAPI 本地启动入口
├── migrations/                # Alembic 迁移脚本（versions/）
├── src/forge/                 # 【后端源码 → bind-mount 到容器 /app/src】
│   ├── main/                  # 应用装配（application.py / config.py / dependencies.py）
│   ├── api/                   # API 路由（admin/v1、v1、minio_proxy）
│   ├── application/           # 应用层服务（services/）
│   ├── domain/                # DDD 领域层（实体、值对象、聚合）
│   └── infrastructure/        # 基础设施（persistence/models、repositories、services）
├── tests/                     # 单元与功能测试
└── .venv/                     # Python 虚拟环境（本地用）
```

### 后端热重载
- `docker-compose.yml` 将 `../backend/src` bind-mount 到 `/app/src`
- `CMD ["uvicorn", ..., "--reload"]` 自动监听文件变更重启服务
- **改任何 `.py` 源码：自动重启，无需重建镜像**

---

## 5. ai-service/ — AI 对话服务

```
ai-service/
├── Dockerfile                 # Python 3.12-slim
├── requirements.txt           # pip 依赖
└── src/                       # → bind-mount 到容器 /app/src
    └── main.py                # FastAPI + uvicorn --reload
```

---

## 6. docker/ — 容器编排

```
docker/
├── docker-compose.yml         # 唯一编排文件（project-name: docker）
└── Containerfile.pgvector     # pgvector 扩展构建（备用）
```

### Compose 使用规范
- 所有容器生命周期管理**必须**通过 compose，禁止单独 podman 命令
- 命令统一格式：`podman-compose --project-name docker -f <路径>/docker-compose.yml <子命令>`
- 重建策略参考：`docs/SOP-compose-rebuild.md`

---

## 7. k8s/ — 生产环境 K3s 配置

```
k8s/
├── database/                  # PostgreSQL 部署（postgres/ + init-scripts）
└── templates/                 # Helm 模板
    ├── admin/                 # 管理后台部署
    ├── ai-service/            # AI 服务部署
    ├── backend/               # 后端 Deployment + Service
    ├── portal-web/            # 用户端前端部署
    ├── ingress/               # Traefik Ingress
    ├── jobs/                  # 初始化 Jobs
    ├── minio/                 # 对象存储
    ├── monitoring/            # Prometheus + Grafana
    ├── network-policies/      # 网络策略
    ├── postgres/              # PostgreSQL
    ├── redis/                 # 缓存
    └── rocketmq/              # 消息队列
```

---

## 8. docs/ — 文档（所有 .md 文件的唯一存放位置）

| 文档 | 说明 |
|------|------|
| `ARCHITECTURE.md` | 总体架构（技术栈、分层、DDD 聚合） |
| `API-REFERENCE.md` | API 接口定义 |
| `AUTH-SECURITY-TODO.md` | 认证/安全待办 |
| `DDD-AGGREGATES.md` | DDD 聚合设计 |
| `DEPLOYMENT.md` | 部署手册（本地/生产） |
| `DEPLOYMENT-MOP.md` | 部署操作流程 |
| `DEV-RULES.md` | 开发规则手册（Marvis 强制执行） |
| `DEVELOPMENT-LOG.md` | 开发日志 |
| `FRONTEND-SURVEY.md` | 前端调研 |
| `GIT-WORKFLOW.md` | Git Flow 工作流 |
| `NETWORK-DESIGN.md` | 网络设计 |
| `ROLE-PERMISSION.md` | 角色权限设计 |
| `REQUIREMENT-*.md` | 各模块需求文档（ADMIN/AI-SERVICE/BACKEND/FRONTEND/USER-MGMT-RBAC） |
| `PLAN-*.md` / `IMPLEMENTATION-PLAN-*.md` | 功能规划与实施计划（RBAC/DIY） |
| `PROMPT-DIY-DEVELOPMENT.md` | DIY 装修功能开发提示词 |
| `SOP-*.md` | 操作规范（compose-rebuild / podman-testing） |
| `STAGE*-DONE.md` | 阶段完成记录 |
| `i18n-multilang-plan.md` | 多语言方案 |
| `implementation-summary.md` | 实现汇总 |

---

## 9. 常见误放纠正

| 误放位置 | 正确位置 | 示例 |
|---------|---------|------|
| 根目录 `SOP-*.md` | `docs/SOP-*.md` | 已纠正 |
| 根目录 `*.md`（除 README） | `docs/` | 所有文档类文件 |
| 临时脚本 | `temp/`（中间产物目录） | 不要放根目录 |
| 产物输出 | `output/`（结果产物目录） | 由 Agent 管理 |
