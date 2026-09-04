# Forge 架构重构方案一：统一网关（Admin + C 端同域）

> 状态：设计文档（待实现）
> 关联分支：`feature/nginx-gateway`
> 实现方：由其他 Agent 按本文档落地

---

## 0. 部署形态总览（本方案核心）

网关路由规则在**两种部署形态**下保持一致，实现载体不同：

| 部署形态 | 网关实现 | 载体 |
|----------|----------|------|
| **docker-compose（中间件）** | 独立 nginx 容器 `gateway`（`gateway/nginx.conf`，卷挂载热更新） | §4.1 / §4.2 |
| **Kubernetes（k8s）** | **Ingress** 实现同等路由，**不部署独立 nginx 容器** | §4.8 |

原则：
- **compose 环境**：`gateway` 是独立中间件容器，唯一对外入口 8080，Admin/C 端/API 全部同源。
- **k8s 环境**：由 Ingress Controller（Traefik / nginx-ingress）承担网关职责，`admin`、`portal-web` 等仅暴露 ClusterIP Service；无需额外 nginx 中间件，避免重复代理层。
- 两种形态的路由语义完全一致：`/admin/` → admin（strip 前缀）、`/` → portal-web、`/api` `/images` `/uploads` `/minio` → backend、`/ai` → ai-service。

---

## 1. 背景与目标

当前 Forge 容器部署架构中，Admin（Vite 构建产物 + nginx）与 C 端 portal-web（Nuxt SSR）**分属不同端口/域**：

- Admin: `http://<host>:8080`（nginx 容器，静态托管 + `/api`、`/images` 代理）
- C 端: `http://<host>:3000`（Nuxt 直出，独立域）

DIY 装修编辑器需要把 C 端页面嵌入 Admin 的 iframe 做实时预览。跨域（8080 vs 3000）导致 cookie、postMessage targetOrigin、SPA 导航等处理复杂且脆弱。

**方案一（本方案）**：引入统一 Nginx 反向代理网关作为唯一对外入口，实现**同域零跨域**：

- **C 端 portal-web 挂根路径 `/`**（商城即站点首页）
- **Admin 挂子路径 `/admin/`**
- 所有 API / 静态资源 / 上传文件走同源 `/api`、`/uploads` 等路径

开发模式（Vite 8383 本地代理）将同步对齐此形态。

---

## 2. 现状梳理

### 2.1 容器部署（docker/docker-compose.yml）

| 服务 | 对外端口 | 说明 |
|------|----------|------|
| admin | 8080 → 80 | nginx 托管 `dist`，仅代理 `/api`、`/images` → backend |
| portal-web | 3000 → 3000 | `pnpm dev --host 0.0.0.0`（Nuxt dev + 热重载，SSR） |
| backend | 8002 → 8000 | FastAPI，`--reload` 热重载 |
| ai-service | 8001 → 8001 | AI 服务 |

### 2.2 开发模式（本地 Vite 8383）

`admin/vite.config.ts` 已按同域形态代理（本方案要复刻到网关）：
- `/portal-preview` → `localhost:3000`（**strip 前缀**）
- `/zh`、`/en`、`/ar` → `localhost:3000`
- `/_nuxt`、`/_ipx`、`/favicon.ico` → `localhost:3000`
- `/api/v1`、`/api/admin` → `127.0.0.1:8000`
- `/uploads`、`/minio` → `127.0.0.1:8000`

### 2.3 关键既有事实

- Admin 路由支持 base：`admin/src/router/index.ts` 用 `createWebHistory(VITE_BASE_URL)`，Vite build `base: VITE_BASE_URL`（`vite.config.ts`）——**已具备子路径部署能力**，只需构建时注入 `VITE_BASE_URL=/admin/`。
- Admin 生产构建 `VITE_SERVICE_BASE_URL=` 为空 → API 走**同源绝对路径** `/api/...`（不受 `/admin/` 子路径影响），由 nginx 代理。
- C 端 `runtimeConfig.public.apiBase = '/api/v1'`（相对路径），浏览器端请求与 C 端页面同域（根路径）。
- DIY iframe 预览 URL：`/portal-preview/zh?preview=true`（`diy/index.vue` buildPreviewUrl 构造，**本方案将去掉 `/portal-preview` 前缀**）。
- `portal-web/app/plugins/diy-preview.client.ts` 已存在：iframe 内 SPA 导航自动补 `preview=true`。
- `admin/src/views/diy-editor/modules/PreviewCanvas.vue` 已有链接重写守卫（把 `/zh/...` 改写为 `/portal-preview/zh/...`，**本方案将移除**）。
- `portal-web/app/middleware/auth.ts` 有改动（识别 `preview=true` 跳过登录跳转，工作区中未提交）。

### 2.4 现存问题（本次一并修复）

1. **portal-web 容器内 routeRules 代理目标不可达**：`nuxt.config.ts` 中 `/api/images/**`、`/uploads/**`、`/minio/**` 的 proxy 目标写死 `http://127.0.0.1:8000`——容器内 `127.0.0.1` 指向 portal-web 自身，无法到达 backend 容器。网关方案下应改为环境变量注入的 backend 地址。
2. **C 端无同域网关**：容器模式下 iframe 预览是跨域（8080↔3000），postMessage、cookie、资源加载均受影响。
3. **双入口不一致**：Admin 与 C 端各自独立端口，浏览器无法用同一域名同时访问两套系统。
4. **DIY 预览依赖 `/portal-preview` 前缀 + 语言路由多条代理**：C 端挂根路径后，这些规则与链接重写守卫全部可以删除，架构大幅简化。

---

## 3. 目标架构

```
                    ┌──────────────────────────────────────────────┐
                    │          Gateway (nginx:alpine)              │
  浏览器             │          唯一对外入口 :8080                  │
   ────────────────► │                                              │
  http://host:8080   ├── /           → portal-web:3000  (C 端根路径)│
                    │      ├─ /zh /en /ar ...        (语言路由)    │
                    │      ├─ /_nuxt /_ipx /favicon  (Nuxt 资源)   │
                    ├── /admin/     → admin:80        (Admin, strip)│
                    ├── /api        → backend:8000    (含 /api/v1) │
                    ├── /images /uploads /minio → backend:8000     │
                    └──────────────────────────────────────────────┘
                              │                  │           │
                     ┌────────┴───────┐  ┌───────┴─────┐  ┌───┴────┐
                     ▼                ▼  ▼             ▼  ▼        ▼
                 portal-web:3000   admin:80        backend:8000  ai-service
                 (Nuxt SSR)       (nginx+dist)     (FastAPI)     (不变)
```

- **唯一对外端口：8080**（由 Gateway 接管；Admin 容器不再对外映射 8080）。
- **首页即 C 端商城**：`http://host:8080/` 直接打开 C 端。
- **后台入口**：`http://host:8080/admin/` 打开 Admin。
- Admin / C 端 / API / 静态资源全部同源 `http://host:8080/*`，零跨域。
- Gateway 配置通过卷挂载，**改配置无需 rebuild 镜像**。

---

## 4. 具体改动

### 4.1 新增 `gateway/nginx.conf`（新文件）

项目根新增目录 `gateway/`，核心配置如下：

```nginx
# gateway/nginx.conf — Forge 统一反向代理网关
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    # ===== C 端 portal-web（根路径，商城首页）=====
    # 覆盖 /、/zh /en /ar 语言路由、/_nuxt /_ipx /favicon.ico 等所有 Nuxt 资源
    location / {
        proxy_pass http://portal-web:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Nuxt dev HMR websocket
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # ===== Admin 后台（/admin/ 子路径，strip 前缀）=====
    # /admin/xxx → admin:80/xxx（admin 容器内以 / 为根，SPA fallback 不受影响）
    location /admin/ {
        proxy_pass http://admin:80/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ===== 后端 API（Admin 与 C 端共用，同源绝对路径）=====
    # /api/admin/v1/* 与 /api/v1/* 均由 backend 提供
    location ^~ /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ===== 后端静态/上传资源 =====
    location ^~ /images {
        proxy_pass http://backend:8000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location ^~ /uploads {
        proxy_pass http://backend:8000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location ^~ /minio {
        proxy_pass http://backend:8000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> 注意：
> - `location /admin/ { proxy_pass http://admin:80/; }` —— 尾部 `/` 会 strip `/admin/` 前缀，admin 容器收到的路径与现在独立部署时完全一致（`/`、`/assets/...`、`/login` 等），**admin/nginx.conf 无需改动**。
> - `/api`、`/images`、`/uploads`、`/minio` 由网关直接代理到 backend，浏览器端请求不再经过 Nuxt 转发，解决 §2.4-1 的容器内 127.0.0.1 不可达问题（路由规则见 4.4 仍建议一并修正，双保险）。
> - C 端语言路由（/zh、/en、/ar、/de、/fr）无需单独匹配——已被 `location /` 命中并代理到 portal-web。

### 4.2 `docker/docker-compose.yml` 修改

新增 `gateway` 服务，调整 `admin`、`portal-web` 端口映射：

```yaml
  # ===== 统一反向代理网关（唯一对外入口）=====
  gateway:
    image: nginx:alpine
    container_name: forge-gateway
    restart: unless-stopped
    networks:
      - forge
    ports:
      - "8080:80"
    volumes:
      - ../gateway/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      admin:
        condition: service_started
      portal-web:
        condition: service_started
      backend:
        condition: service_healthy

  # ===== 后台管理前端 (Admin) — 不再对外映射端口 =====
  admin:
    build:
      context: ../admin
      dockerfile: Dockerfile
    container_name: forge-admin
    restart: unless-stopped
    networks:
      - forge
    # ports:                          # 移除 8080:80，仅网关可达
    #   - "8080:80"
    depends_on:
      backend:
        condition: service_healthy

  # ===== 门户前端 (C 端) — 保留 3000 便于直连调试，可选移除 =====
  portal-web:
    image: forge-portal-web:latest
    container_name: forge-portal-web
    restart: unless-stopped
    networks:
      - forge
    ports:
      - "3000:3000"        # 建议保留：本地直连调试 C 端；若需严格单一入口可移除
    environment:
      NUXT_PUBLIC_API_BASE: /api/v1
      NUXT_PUBLIC_AI_CHAT_BASE: http://ai-service:8001   # 修正：容器网络内直连 AI 服务
      NUXT_PUBLIC_REGION: na
      NUXT_PUBLIC_DEFAULT_CURRENCY: USD
      API_PROXY_TARGET: http://backend:8000
      NUXT_BACKEND_URL: http://backend:8000               # 新增：供 routeRules 使用（见 4.4）
    volumes:
      - ../portal-web/app:/app/app
    depends_on:
      backend:
        condition: service_healthy
```

要点：
- **gateway 独占 8080**，是唯一对外入口。
- **admin 移除对外端口**（可选保留 `8081:80` 作为调试直连，若保留需在注释中说明）。
- **portal-web 保留 3000** 以便直连调试；严格生产可移除。
- `NUXT_PUBLIC_AI_CHAT_BASE` 改为容器网络内 `http://ai-service:8001`（浏览器端请求 C 端聊天功能时由网关同域转发，见 4.5 可选代理；若 AI 聊天独立使用场景多，可增加网关 `/ai` 代理，本次不强制）。

### 4.3 Admin 构建配置修改（子路径部署）

新增/修改 `admin/.env.prod`：

```ini
# app base url（构建后 Admin 挂载于 /admin/ 子路径）
VITE_BASE_URL=/admin/

# backend service base url, prod environment (empty = same origin, API proxied by nginx)
VITE_SERVICE_BASE_URL=
```

效果：
- Vite build 产物资源引用前缀变为 `/admin/`（`<link href="/admin/assets/...">`）。
- Vue Router base 变为 `/admin/`（`createWebHistory('/admin/')`），Admin 内部路由 URL 为 `/admin/login`、`/admin/dashboard` 等。
- 网关 `location /admin/` strip 前缀后，admin 容器内路径仍为 `/assets/...`、`/login` 等，**admin/nginx.conf 无需改动**。
- API 请求走同源绝对路径 `/api/...`，不受 base 影响。

> 本地开发同步：如希望在本地开发也以 `/admin/` 访问，在 `admin/.env.development`、`admin/.env.test` 增加 `VITE_BASE_URL=/admin/`（开发 URL 变为 `http://localhost:8383/admin/`，Vite proxy 规则不受影响）；若暂不设置，本地仍以根路径访问，仅容器部署使用 `/admin/`。

### 4.4 `portal-web/nuxt.config.ts` 修改（修复容器内代理目标）

将 routeRules / devProxy 中写死的 `http://127.0.0.1:8000` 改为环境变量注入：

```ts
// 顶部读取环境变量
const backendUrl = process.env.NUXT_BACKEND_URL || 'http://127.0.0.1:8000';

// routeRules
routeRules: {
  "/api/images/**": { proxy: { to: `${backendUrl}/api/images/**` } },
  "/uploads/**":    { proxy: { to: `${backendUrl}/uploads/**` } },
  "/minio/**":      { proxy: { to: `${backendUrl}/minio/**` } },
},
devProxy: {
  "/uploads": { target: backendUrl, changeOrigin: true },
  "/minio":   { target: backendUrl, changeOrigin: true },
},
```

效果：
- 本地开发（无 `NUXT_BACKEND_URL`）→ 仍走 `127.0.0.1:8000`，行为不变。
- 容器部署（compose 注入 `NUXT_BACKEND_URL=http://backend:8000`）→ SSR 内部访问 backend 容器可达。

### 4.5 网关 `/ai` 代理（可选，AI 聊天同域化）

若希望 C 端 AI 聊天也同域，网关追加：

```nginx
    location /ai/ {
        proxy_pass http://ai-service:8001/;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
```

并将 `NUXT_PUBLIC_AI_CHAT_BASE` 改为 `/ai`（相对路径）。**若暂不需要，跳过此项**。

### 4.6 DIY 预览 URL 调整（移除 /portal-preview 前缀）

C 端挂根路径后，iframe 预览 URL 由 `/portal-preview/zh?preview=true` 简化为 `/zh?preview=true`：

**文件：`admin/src/views/diy/index.vue`**
- `buildPreviewUrl()`：去掉 `/portal-preview` 前缀拼接，base 直接为 `/zh?preview=true`（保持 `preview=true`）。

**文件：`admin/src/views/diy-editor/modules/PreviewCanvas.vue`**
- 移除 onIframeLoad 中把 `/zh/...` 改写为 `/portal-preview/zh/...` 的链接重写逻辑（C 端已在根路径，iframe 内 SPA 导航 `/zh/xxx` 天然同域且正确）。
- 保留（如适用）：`preview=true` 补全逻辑与 `__diyGuardInstalled` 防重复注入（可简化）。

**文件：`portal-web/app/plugins/diy-preview.client.ts`**
- 无需改动（`inIframe` 判断 + `beforeEach` 补 `preview=true` 依然生效）。

### 4.7 无需改动的部分

- **`admin/nginx.conf`**：保留原样（admin 容器内自服务，路径以 `/` 为根；网关 strip `/admin/` 后透传其 SPA fallback 与内部路由）。
- **C 端 runtimeConfig.apiBase**：`/api/v1` 相对路径，网关代理 `/api` → backend 已覆盖。
- **DIY 元素选择 / postMessage 桥接**（`docs/DIY-preview-bridge.md`）：同域目标从 `/portal-preview` 域改为根路径域后，postMessage 与 iframe 交互逻辑不变，仅 iframe src 前缀变化。

### 4.8 k8s 部署形态（使用 Ingress，不部署独立 nginx 容器）

> k8s 环境由 Ingress Controller 承担网关职责。仓库已含 Helm chart（`k8s/`），本小节将其从"旧路由直连"升级为与 compose 网关**同语义**的路由，并补齐 k8s 缺失的 admin 部署模板。

#### 4.8.1 现状与差异

当前 `k8s/templates/ingress/ingress.yaml`（Traefik IngressRoute + 标准 Ingress 双模板）与 `k8s/values.yaml` 仍是旧路由：

| 路径 | 当前 | 目标 |
|------|------|------|
| `/` | portal-web:3000 | portal-web:3000（不变） |
| `/admin/` | **无（404）** | admin:80（**strip `/admin/`**，新增） |
| `/api` | backend:8000 | backend:8000（不变） |
| `/ai` | ai-service:8001 | ai-service:8001（不变） |
| `/images` `/uploads` `/minio` | 未单独路由（走 `/` 误入 portal-web） | backend:8000（新增） |

**k8s 侧缺失项**：`k8s/templates/` 下没有 `admin/` 的 Deployment 与 Service（compose 有 admin 容器，k8s 必须补齐），否则 `/admin/` 无后端可转。

#### 4.8.2 新增 `k8s/templates/admin/deployment.yaml`

与 `portal-web` 模板同构，镜像使用 admin 构建产物（nginx + dist，内部监听 80），`VITE_BASE_URL=/admin/` 已在构建时注入镜像（同 §4.3，k8s 无需额外环境变量）：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "forge.fullname" . }}-admin
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "forge.labels" . | nindent 4 }}
    app.kubernetes.io/component: admin
spec:
  replicas: {{ index .Values "admin" "replicas" }}
  selector:
    matchLabels:
      {{- include "forge.selectorLabels" . | nindent 6 }}
      app.kubernetes.io/component: admin
  template:
    metadata:
      labels:
        {{- include "forge.labels" . | nindent 8 }}
        app.kubernetes.io/component: admin
    spec:
      containers:
        - name: admin
          image: {{ index .Values "admin" "image" "repository" }}:{{ index .Values "admin" "image" "tag" }}
          imagePullPolicy: {{ .Values.global.imagePullPolicy }}
          ports:
            - name: http
              containerPort: 80
              protocol: TCP
          readinessProbe:
            httpGet:
              path: /healthz
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 20
          resources:
            {{- toYaml index .Values "admin" "resources" | nindent 12 }}
```

> 若 admin 容器 `nginx.conf` 无 `/healthz` 探活端点，需在 `admin/nginx.conf` 增加 `location = /healthz { return 200; }`（compose 形态不影响）。

#### 4.8.3 新增 `k8s/templates/admin/svc.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "forge.fullname" . }}-admin
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "forge.labels" . | nindent 4 }}
    app.kubernetes.io/component: admin
spec:
  type: ClusterIP
  selector:
    {{- include "forge.selectorLabels" . | nindent 4 }}
    app.kubernetes.io/component: admin
  ports:
    - name: http
      port: {{ index .Values "admin" "service" "port" }}
      targetPort: 80
      protocol: TCP
```

#### 4.8.4 更新 `k8s/templates/ingress/ingress.yaml`

**（a）Traefik 分支（K3s 内置 Traefik v3）**——用 IngressRoute + `stripPrefix` Middleware 实现 `/admin/` 前缀剥离；`/api`、`/images`、`/uploads`、`/minio` 直达 backend；根路径 `/` 兜底 portal-web：

```yaml
{{- if eq .Values.ingress.className "traefik" }}
---
# 前缀剥离 Middleware（/admin/xxx → admin 收到 /xxx）
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: {{ include "forge.fullname" . }}-strip-admin
  namespace: {{ .Values.global.namespace }}
spec:
  stripPrefix:
    prefixes:
      - /admin
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: {{ include "forge.fullname" . }}
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "forge.labels" . | nindent 4 }}
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`{{ .Values.ingress.hosts[0].host }}`) && PathPrefix(`/admin`)
      kind: Rule
      middlewares:
        - name: {{ include "forge.fullname" . }}-strip-admin
      services:
        - name: {{ include "forge.fullname" . }}-admin
          port: 80
    - match: Host(`{{ .Values.ingress.hosts[0].host }}`) && (PathPrefix(`/api`) || PathPrefix(`/images`) || PathPrefix(`/uploads`) || PathPrefix(`/minio`))
      kind: Rule
      services:
        - name: {{ include "forge.fullname" . }}-backend
          port: 8000
    - match: Host(`{{ .Values.ingress.hosts[0].host }}`) && PathPrefix(`/ai`)
      kind: Rule
      services:
        - name: {{ include "forge.fullname" . }}-ai-service
          port: 8001
    - match: Host(`{{ .Values.ingress.hosts[0].host }}`)
      kind: Rule
      services:
        - name: {{ include "forge.fullname" . }}-portal-web
          port: 3000
{{- else }}
```

> Traefik 路由按声明顺序匹配，`/admin` 规则必须排在兜底 `/` 之前；`PathPrefix` 默认前缀匹配，`/admin` 同时覆盖 `/admin/` 与 `/admin/xxx`。

**（b）标准 Ingress 分支（nginx-ingress 等）**——用 `rewrite-target` + 正则捕获组实现 `/admin/` 前缀剥离；`use-regex` 开启正则；`/api`、`/images`、`/uploads`、`/minio` 走独立 path 直通 backend（不 rewrite）：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "forge.fullname" . }}
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "forge.labels" . | nindent 4 }}
  annotations:
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/proxy-body-size: 50m
    {{- with .Values.ingress.annotations }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          # Admin：/admin/xxx → admin:80/xxx（rewrite-target 剥离前缀）
          - path: /admin(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: {{ include "forge.fullname" $ }}-admin
                port:
                  number: 80
          # 后端 API 与资源：直通，不 rewrite
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: {{ include "forge.fullname" $ }}-backend
                port:
                  number: 8000
          - path: /images
            pathType: Prefix
            backend:
              service:
                name: {{ include "forge.fullname" $ }}-backend
                port:
                  number: 8000
          - path: /uploads
            pathType: Prefix
            backend:
              service:
                name: {{ include "forge.fullname" $ }}-backend
                port:
                  number: 8000
          - path: /minio
            pathType: Prefix
            backend:
              service:
                name: {{ include "forge.fullname" $ }}-backend
                port:
                  number: 8000
          - path: /ai
            pathType: Prefix
            backend:
              service:
                name: {{ include "forge.fullname" $ }}-ai-service
                port:
                  number: 8001
          # C 端兜底：根路径 → portal-web
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "forge.fullname" $ }}-portal-web
                port:
                  number: 3000
    {{- end }}
  {{- if .Values.ingress.tls }}
  tls: ...
  {{- end }}
```

> 关键：`/admin(/|$)(.*)` + `rewrite-target: /$2` 将 `/admin/login` 改写为 `/login`，与 compose 网关 `proxy_pass http://admin:80/`（strip）语义一致。`/api`、`/images` 等 path 若走 rewrite-target 会被破坏，因此保持独立直通规则（默认不带 rewrite 的 path 也会被全局 rewrite-target 影响——nginx-ingress 中若需豁免，可将这些 path 单独拆成第二个 Ingress 资源（无 rewrite-target annotation），或改用 server-snippet；实现时以 nginx-ingress 版本行为为准，优先用"admin 单独一个 Ingress + 其余共享一个 Ingress"的拆分方案规避）。

#### 4.8.5 更新 `k8s/values.yaml`

新增 `admin` 配置段，并把 `ingress.hosts[0].paths` 补齐为与 compose 网关一致的路由集合：

```yaml
# Admin
admin:
  enabled: true
  replicas: 1
  image:
    repository: harbor.example.com/forge/admin
    tag: v0.1.0
  service:
    port: 80
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi

# Ingress（旧 3 条路径 → 6 条，与 compose 网关同语义）
ingress:
  enabled: true
  className: traefik        # traefik=IngressRoute(stripPrefix) / 其他=标准 Ingress(rewrite)
  hosts:
    - host: forge.local
      paths:
        - path: /admin
          pathType: Prefix
          service: admin
        - path: /api
          pathType: Prefix
          service: backend
        - path: /images
          pathType: Prefix
          service: backend
        - path: /uploads
          pathType: Prefix
          service: backend
        - path: /minio
          pathType: Prefix
          service: backend
        - path: /ai
          pathType: Prefix
          service: ai-service
        - path: /
          pathType: Prefix
          service: portal-web
  tls: []
```

> `values.yaml` 的 paths 驱动标准 Ingress 分支渲染；Traefik 分支按 §4.8.4(a) 固定路由顺序渲染，不受 paths 顺序影响。

#### 4.8.6 k8s 形态验证清单

- [ ] `kubectl -n forge get ingress,ingressroute,middleware` 资源就绪。
- [ ] `http://forge.local/admin/` 打开 Admin 登录页，刷新 `/admin/dashboard` 不 404（前缀剥离生效）。
- [ ] `http://forge.local/` 打开 C 端首页；`/zh` `/en` `/ar` 语言路由正常。
- [ ] `/api/v1/*`、`/api/admin/v1/*` 经 Ingress 到达 backend。
- [ ] `/uploads/*`、`/minio/*`、`/images/*` 图片资源正常（不再被 `/` 兜底吞掉）。
- [ ] `curl -H 'Host: forge.local' http://<ingress-ip>/admin/login` 返回 admin SPA（rewrite 后路径为 `/login`）。
- [ ] 与 compose 网关行为对拍：同一 URL 在两种形态下返回同源路径语义。

---

## 5. 请求路径对照（网关生效后）

| 场景 | URL（同域 8080） | 网关转发目标 |
|------|------------------|--------------|
| C 端首页/商城 | `/` | portal-web:3000 |
| C 端语言路由 | `/zh`、`/en`、`/ar`、`/de`、`/fr` | portal-web:3000 |
| C 端商品/详情 | `/zh/products` 等 | portal-web:3000 |
| Admin 登录/后台 | `/admin/login`、`/admin/dashboard` | admin:80（strip `/admin/`） |
| Admin 静态资源 | `/admin/assets/*` | admin:80（strip） |
| Admin API | `/api/admin/v1/auth/login` | backend:8000 |
| C 端 API | `/api/v1/products` | backend:8000 |
| DIY 预览 iframe | `/zh?preview=true` | portal-web:3000 |
| iframe 内 SPA 导航 | `/zh/products` | portal-web:3000 |
| Nuxt 资源 | `/_nuxt/*`、`/_ipx/*`、`/favicon.ico` | portal-web:3000 |
| 上传/静态图 | `/uploads/*`、`/minio/*`、`/images/*` | backend:8000 |

---

## 6. 实施步骤（供实现 Agent 执行）

1. **分支准备**（遵循 DEV-RULES.md）：
   - `git status` 确认工作区（当前有未提交改动：PreviewCanvas.vue、diy/index.vue、alembic.ini、auth.ts、package.json、portal-web/app/plugins/）。
   - 归集相关改动到 dev 后，从 dev 切 `feature/nginx-gateway`。
2. **新建 `gateway/nginx.conf`**（按 §4.1 全文）。
3. **修改 `docker/docker-compose.yml`**（按 §4.2）：
   - 新增 gateway 服务；
   - admin 移除对外端口；
   - portal-web 环境变量增补 `NUXT_BACKEND_URL`、修正 `NUXT_PUBLIC_AI_CHAT_BASE`。
4. **修改 `admin/.env.prod`**（按 §4.3）：新增 `VITE_BASE_URL=/admin/`（并 rebuild admin 镜像）。
5. **修改 `portal-web/nuxt.config.ts`**（按 §4.4）routeRules/devProxy 目标改环境变量。
6. **修改 DIY 预览 URL**（按 §4.6）：
   - `admin/src/views/diy/index.vue`：`buildPreviewUrl()` 去掉 `/portal-preview` 前缀；
   - `admin/src/views/diy-editor/modules/PreviewCanvas.vue`：移除链接重写守卫。
7. **重建与启动**：
   - gateway 为新镜像，`docker compose up -d gateway`（nginx 配置卷挂载，改配置后 `docker compose restart gateway` 即可）；
   - admin 需 rebuild：`docker compose build admin && docker compose up -d admin`；
   - portal-web 配置变更后需重启：`docker compose restart portal-web`（容器内 `pnpm dev` 会热载 nuxt.config 变更，必要时重建镜像）。
8. **端到端验证**（见 §7），全部通过后提交 PR 合并 dev。

> 说明：若本地开发也需对齐 `/admin/` 子路径，按 §4.3 在 `.env.development` / `.env.test` 增加 `VITE_BASE_URL=/admin/`；否则本地开发维持现状（根路径），仅容器部署使用子路径。

### 6.1 k8s 形态实施步骤

1. 新增 `k8s/templates/admin/deployment.yaml`、`k8s/templates/admin/svc.yaml`（§4.8.2 / §4.8.3）。
2. 更新 `k8s/templates/ingress/ingress.yaml`（§4.8.4）：Traefik 分支加 `/admin` 路由 + Middleware；标准 Ingress 分支改 rewrite 方案。
3. 更新 `k8s/values.yaml`（§4.8.5）：新增 `admin` 段、ingress paths 补齐。
4. 校验模板渲染：`helm template forge ./k8s` 确认 IngressRoute / Middleware / Ingress / admin Deployment 均生成。
5. 部署与验证（§4.8.6）：`helm upgrade --install forge ./k8s -n forge` 后逐项 curl 对拍。

---

## 7. 验证清单

### 7.1 网关与入口
- [ ] `http://<host>:8080/` 打开 **C 端商城首页**。
- [ ] `http://<host>:8080/admin/` 打开 **Admin 登录页**，登录成功（`/api/admin/v1/auth/login` 走网关）。
- [ ] `http://<host>:8080/admin/dashboard` 直达后台首页（路由 base 生效）。
- [ ] `http://<host>:3000/`（如保留映射）仍可直连 C 端。

### 7.2 Admin 子路径资源
- [ ] Admin 页面静态资源（`/admin/assets/*.js/css`）加载正常，无 404。
- [ ] Admin 刷新 `/admin/dashboard` 不 404（SPA fallback 经 strip 后正常）。
- [ ] Admin 内 API 请求（`/api/admin/v1/*`）成功。

### 7.3 DIY 预览闭环（核心验收）
- [ ] Admin 打开页面装修 → 预览 tab → iframe 加载 `/zh?preview=true` 正常显示 C 端首页。
- [ ] iframe 内点击链接（SPA 导航）→ 地址变为 `/zh/xxx`，页面正常，**不跳出到 admin 路由**（`/admin/` 前缀与 C 端 `/` 前缀天然隔离）。
- [ ] iframe 内刷新 → 仍带 `preview=true`（diy-preview.client.ts 生效），不跳登录页。
- [ ] 切换设备模式、切 tab → iframe 重建后预览仍正常。

### 7.4 同域 API 与资源
- [ ] C 端页面内 API（`/api/v1/*`）请求成功（经网关 → backend）。
- [ ] C 端图片 `/uploads/*`、`/minio/*`、`/api/images/*` 正常显示（网关直达 backend）。
- [ ] C 端 `/_nuxt/*`、`/_ipx/*` 资源加载正常。

### 7.5 C 端语言路由
- [ ] `http://<host>:8080/zh`、`/en`、`/ar` 直接打开 C 端页面正常（根路径 `location /` 命中）。

### 7.6 开发容器热重载
- [ ] portal-web 容器内 `app/` 代码改动 → Nuxt HMR 通过网关路径生效（WebSocket 升级代理正常）。
- [ ] admin 构建产物更新后（rebuild admin 镜像）→ 网关无需重启即生效。

### 7.7 回归
- [ ] 本地开发模式（Vite 8383 + Nuxt 3000 + backend 8000，不经网关）不受影响，DIY 预览仍正常（若本地未设置 `/admin/` base）。

---

## 8. 风险与注意事项

1. **nginx location 匹配顺序**：`/admin/`（前缀）先于 `location /`（最泛匹配）命中，nginx 前缀匹配按最长优先；`^~ /api`、`^~ /images` 等避免被 `location /` 吞掉。实现时保持 §4.1 的层级。
2. **`proxy_pass` 尾部斜杠语义**：`location /admin/ { proxy_pass http://admin:80/; }` —— 带尾部 `/` 才会 strip `/admin/` 前缀；若误写成不带斜杠，admin 容器会收到 `/admin/login` 而 SPA fallback 返回 index.html 后路由 base 异常。实现时必须核对。
3. **Admin `VITE_BASE_URL` 必须与网关 strip 前缀一致**：构建时 `VITE_BASE_URL=/admin/`，否则资源 404 或路由错乱。
4. **WebSocket 升级**：Nuxt dev HMR 依赖 `Upgrade`/`Connection` 头透传，`location /` 必须带（已包含）。
5. **容器网络可达性**：`admin`、`portal-web`、`backend`、`ai-service` 必须在同一个 `forge` 网络内（compose 默认即如此）；移除 admin 对外端口不影响网关访问（同网络 DNS 直连）。
6. **AI 聊天同域化（4.5）为可选项**：不实现时 C 端 AI 聊天仍走 `http://ai-service:8001` 直连（容器网络内可用，浏览器需可路由到该地址，视部署环境而定）；如需严格同域再补 `/ai` 代理。
7. **gateway 配置热更新**：卷挂载 `nginx.conf`，修改后 `docker compose restart gateway` 即可，无需 rebuild 镜像（注意 nginx `-t` 校验：`docker compose exec gateway nginx -t`）。
8. **本地开发与容器部署路径差异**：若本地未设 `VITE_BASE_URL=/admin/`，本地 admin 在根路径、容器在 `/admin/`，两套 URL 并存属预期；若需完全一致，按 §4.3 同步设置。

---

## 9. 文件变更清单

| # | 文件 | 操作 | 说明 |
|---|------|------|------|
| 1 | `gateway/nginx.conf` | **新建** | 统一网关路由配置（compose 形态，~60 行） |
| 2 | `docker/docker-compose.yml` | **修改** | 新增 gateway 服务；admin 移除对外端口；portal-web 增补环境变量 |
| 3 | `admin/.env.prod` | **修改** | 新增 `VITE_BASE_URL=/admin/` |
| 4 | `admin/src/views/diy/index.vue` | **修改** | `buildPreviewUrl()` 去掉 `/portal-preview` 前缀 |
| 5 | `admin/src/views/diy-editor/modules/PreviewCanvas.vue` | **修改** | 移除 `/zh` → `/portal-preview/zh` 链接重写守卫 |
| 6 | `portal-web/nuxt.config.ts` | **修改** | routeRules/devProxy 目标改 `NUXT_BACKEND_URL` 环境变量 |
| 7 | `k8s/templates/admin/deployment.yaml` | **新建** | admin Deployment（nginx+dist，内部 80），k8s 侧补齐 |
| 8 | `k8s/templates/admin/svc.yaml` | **新建** | admin ClusterIP Service |
| 9 | `k8s/templates/ingress/ingress.yaml` | **修改** | Traefik 分支新增 `/admin` 路由 + stripPrefix Middleware、`/images` `/uploads` `/minio` 直通 backend；标准 Ingress 分支改 rewrite-target 剥离 `/admin/`、补充资源路径 |
| 10 | `k8s/values.yaml` | **修改** | 新增 `admin` 配置段；ingress paths 补齐 6 类路径 |
| 11 | `admin/nginx.conf` | **修改**（可选） | 增加 `/healthz` 探活端点（k8s readiness/liveness 使用，compose 不影响） |

*最后更新：2026-08-12*
