# Compose 重建策略 SOP

## 核心原则

**不要每次改代码都重建 Docker 镜像。** 项目使用 bind-mount volume，源码文件（`./frontend/app` → `/app/app`）在容器内实时同步，Nuxt HMR 自动热更新。

## 判断矩阵：什么情况下需要重建镜像？

### 前端 (frontend)

| 改动范围 | 是否需要 rebuild 镜像 | 操作 |
|---------|---------------------|------|
| `.vue` / `.ts` / `.js` 源码文件 | ❌ 不需要 | 等 HMR 自动刷新（2-5 秒） |
| locale JSON 文件 (`i18n/locales/*.json`) | ❌ 不需要 | HMR 自动加载；新增顶层 key 可能需要手动刷新浏览器 |
| `.env` / `runtimeConfig` 环境变量 | ❌ 不需要 | 改 `docker-compose.yml` 中 `environment` 后 `up -d` 即可 |
| `tailwind.config.ts` / CSS | ❌ 不需要 | HMR |
| `nuxt.config.ts` | ✅ 需要 | 配置文件在 `COPY . .` 范围内，不在 volume mount 中 |
| `package.json` / `pnpm-lock.yaml` | ✅ 需要 | 依赖变更 |
| `Dockerfile` | ✅ 需要 | 构建逻辑变更 |

### 后端 (backend)

| 改动范围 | 是否需要 rebuild 镜像 | 操作 |
|---------|---------------------|------|
| `.py` 源码文件 | ❌ 不需要 | uvicorn `--reload` 自动重启 |
| `pyproject.toml` / 依赖 | ✅ 需要 | 依赖变更 |
| `Dockerfile` | ✅ 需要 | 构建逻辑变更 |

### Admin (admin)

| 改动范围 | 是否需要 rebuild 镜像 | 操作 |
|---------|---------------------|------|
| `.vue` / `.ts` 源码 | ❌ 不需要 | Vite HMR |
| `package.json` / `pnpm-lock.yaml` | ✅ 需要 | 依赖变更 |
| `Dockerfile` / `nginx.conf` | ✅ 需要 | 构建逻辑变更 |

## Docker 重建加速规则

### 1. 禁止使用 `--no-cache`
`--no-cache` 会使依赖安装层（STEP 5）每次重跑，消耗 2-5 分钟。除非明确需要清缓存，否则只用 `build`。

### 2. npm/pnpm 永久使用国内镜像
**不要在 RUN 指令中每次设置 registry**，在 Dockerfile 中统一配置：

```dockerfile
# 在 FROM 之后、任何 install 之前
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@11.8.0 --activate
COPY .npmrc .npmrc
```

`.npmrc` 内容：
```
registry=https://registry.npmmirror.com
```

### 3. 仅前端文件变更的正确做法
```powershell
# 大多数情况：不需要任何操作，HMR 自动生效
# 如果需要手动触发 HMR 重载（罕见）：
podman exec forge-frontend touch /app/app/app.vue
```

### 4. nuxt.config.ts 变更的正确做法
```powershell
# 只重建 frontend，不重建整个 compose
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml build frontend
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml up -d --force-recreate frontend
```

### 5. 需要重建时的最快路径
```powershell
# 仅重建变更的服务，不用 down 整个 compose
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml build <service>
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml up -d --force-recreate <service>
```

## fnm 的使用

本机 Node.js 通过 fnm 管理，在宿主机执行 node/npm/pnpm 时：

```powershell
# 确保 fnm 环境已加载（通常已配置在 profile 中）
fnm use default
# 然后正常使用
node -v
pnpm --version
```

不要在容器外到处搜索 node 路径，直接用 `fnm use default && pnpm ...`

## compose 文件位置

统一使用：`D:\codeRepo\forge\docker\docker-compose.yml`
项目名：`docker`

所有 compose 命令统一格式：
```powershell
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml <子命令>
```

## 常见场景速查

| 场景 | 命令 |
|------|------|
| 改 .vue 源码 | 无操作，等 HMR |
| 改 locale 翻译 | 无操作，等 HMR；刷新浏览器 |
| 改 nuxt.config.ts | `build frontend` → `up -d --force-recreate frontend` |
| 改 Dockerfile | `build <service>` → `up -d --force-recreate <service>` |
| 改 docker-compose.yml | `up -d`（compose 自动检测变更） |
| 改 .py 后端代码 | 无操作，uvicorn --reload 自动重启 |
| 改 pyproject.toml | `build backend` → `up -d --force-recreate backend` |
| 改 package.json | `build <service>` → `up -d --force-recreate <service>` |
| 容器异常排查 | `podman logs forge-frontend` |
| 查看服务状态 | `podman ps --filter name=forge` |
