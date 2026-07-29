---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_9dd3814e839411f184135254006c9bbf
    ReservedCode1: 8Rd1/yF+3VhHdr52zpgHBzQl11fo1kTBUYUD4aoP+cFgxGex0ZGQpT+1bAeCrNhOzF/8k6tyuZZUZXQsydsUW1mCqnPDRoEdOUG/K2eJ3+kiKP1aPUtMhCRgi2jEFVwfoPcWx6Sp3aioWzcCM6vgNhDFwRGBI5LjM08zizm444jI4DQGTip7N94BONQ=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_9dd3814e839411f184135254006c9bbf
    ReservedCode2: 8Rd1/yF+3VhHdr52zpgHBzQl11fo1kTBUYUD4aoP+cFgxGex0ZGQpT+1bAeCrNhOzF/8k6tyuZZUZXQsydsUW1mCqnPDRoEdOUG/K2eJ3+kiKP1aPUtMhCRgi2jEFVwfoPcWx6Sp3aioWzcCM6vgNhDFwRGBI5LjM08zizm444jI4DQGTip7N94BONQ=
---

---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_de6542c3757b11f19641525400d9a7a1
    ReservedCode1: aRlwyaXIE05IvV85qkqs64aqtUZblvhSPZSYit2rpeHXPD2YBKeLOSnzFBJ2Gkeh+k8pEd9Z726GkXtb5JG/OHqBwzzijMkkZotfS4i07IkahRemJib/z1RE4kinWify+miyX96bSjiOZ7x9PPIbv61aa6A1h8ij4pEivT1+On6pY/PzPgsBWeNgPOM=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_de6542c3757b11f19641525400d9a7a1
    ReservedCode2: aRlwyaXIE05IvV85qkqs64aqtUZblvhSPZSYit2rpeHXPD2YBKeLOSnzFBJ2Gkeh+k8pEd9Z726GkXtb5JG/OHqBwzzijMkkZotfS4i07IkahRemJib/z1RE4kinWify+miyX96bSjiOZ7x9PPIbv61aa6A1h8ij4pEivT1+On6pY/PzPgsBWeNgPOM=
---

# 开发规则手册

> 适用于 Marvis AI 助手在本项目中的所有开发协助行为。

---

## 1. 版本管理

遵守 [GIT-WORKFLOW.md](./GIT-WORKFLOW.md) 中定义的 Git Flow 工作流：

- **feature/** 分支：新功能
- **fix/** 分支：Bug 修复
- **hotfix/** 分支：紧急修复
- 合并路径：feature/fix → dev → main
- 提交信息遵循 Conventional Commits 规范
- 禁止创建备份文件（如 `*_backup.py`、`*_old.py`）

---

## 2. 缓存清理与重启

**触发条件**：修改以下类型文件后，由 Marvis 判断是否需要清除缓存并重启：

| 文件类型 | 是否需要清缓存 |
|---|---|
| `server/` 目录下的 `.ts` 文件（Nitro 路由/中间件） | **是** |
| `nuxt.config.ts`、`package.json` | **是**（且需重建镜像） |
| `pages/`、`components/`、`composables/` 下的 `.vue` / `.ts` | 否（HMR 自动生效） |
| `stores/` 下的 `.ts` 文件 | 否（HMR 自动生效） |
| `locales/` 下的 `.json` 翻译文件 | 否（HMR 自动生效） |
| Dockerfile、`docker-compose.yml` | 参考第 3 节 |

**执行步骤**（由 Marvis 判断并自动执行）：

```bash
podman exec forge-frontend rm -rf /app/.nuxt /app/node_modules/.cache
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml restart frontend
```

对于后端 `.py` 源文件（非 Dockerfile），由于使用 bind mount，直接重启容器即可生效：

```bash
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml restart backend
```

---

## 3. 部署策略

遵守 [SOP-compose-rebuild.md](./SOP-compose-rebuild.md) 中的重建规则。

### 3.1 Frontend（Nuxt，forge/frontend）

| 变更内容 | 操作 |
|---|---|
| `.vue`、`.ts` 源码、`locales/*.json` | HMR / 重启容器即可，**无需重建镜像** |
| `Dockerfile`、`package.json`、`nuxt.config.ts` | 必须 `--build` 重建 |

### 3.2 Admin（Soybean Admin，`admin/` 目录）

Admin 源码位于项目内 `admin/` 目录，Vite 构建产物固化为静态文件，由 nginx 直接服务，**无 HMR**。

| 变更内容 | 操作 |
|---|---|
| **任何源码**（`.vue` / `.ts` / `.json` / `.css`） | 必须 `build --no-cache` 重建镜像 + `up -d --force-recreate` 重建容器 |

Admin 重建完整命令（在 `D:\codeRepo\forge\docker` 目录执行）：

```bash
podman-compose build --no-cache admin
podman-compose up -d --force-recreate admin
```

> **为什么需要 `--no-cache`**：Docker 层缓存可能命中旧的 `COPY . .` 层，导致源码改动未打入镜像。容器重建后用户还需 `Ctrl+Shift+R` 硬刷新浏览器绕过 CDN 缓存。

### 3.3 通用命令格式

统一命令格式（禁止单独使用 podman run/stop/restart）：

```bash
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml <子命令>
```

---

## 4. 知识检索优先级

遇到不确定的事项，按以下顺序查找：

1. **查阅 `docs/` 目录下的文档**
2. 文档未覆盖 → **询问用户**

禁止在无依据的情况下自行决策架构、配置或业务逻辑层面的问题。

---

## 5. 执行前计划

每次执行任务前，Marvis 必须：

- **先向用户说明执行计划**（改哪些文件、做什么操作、预期结果）
- 用户知情后即可开始执行，无需逐一等待审批

**文件修改约束**：

- 修改文件本身无需用户审批
- 必须确保修改不引入新 Bug
- 修改完成后必须进行**回归测试**验证

---

## 6. 新增文件与变更记录

- 新增文件、引入新内容无需用户审批
- 每次完成任务后，必须在回复中声明产出物（使用 `yyb-product` 卡片）
- 所有文档（`.md`）必须放在 `docs/` 目录下，根目录仅允许 `README.md`

---

*最后更新：2026-07-19*
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
