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

**Admin 视图文件变更后的额外步骤**：

> 若删除了 `admin/src/views/` 下的目录（如 `views/site/`），必须同步清理 `admin/src/router/elegant/` 中的三个自动生成文件：
> - `elegant/routes.ts` — 移除对应路由定义
> - `elegant/imports.ts` — 移除对应组件导入
> - `elegant/transform.ts` — 移除 `routeMap` 中的映射条目
>
> 否则 elegant-router 会按残留空目录生成旧路由，导致用户看到旧菜单项。

Admin 重建完整命令（在 `D:\codeRepo\forge\docker` 目录执行）：

```bash
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml build --no-cache admin
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml up -d --force-recreate admin
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

## 7. 规则自增长机制

> **核心理念**：将每次踩坑经验沉淀为可复用的规则，让 DEV-RULES.md 持续进化为项目开发专家手册。

### 7.1 触发条件

当出现以下任一情况时，Marvis 必须主动评估是否需要写入新规则：

- 遇到问题经排查后成功解决，且排查过程涉及非显而易见的项目特定知识
- 用户明确指出"把这个记下来"、"下次别犯这个错"、"加一条规则"
- 重复犯过同类错误，说明旧规则未覆盖
- 发现现有规则存在错误或过时，需修正

### 7.2 写入标准

新增规则必须满足：

1. **可复用**：该经验在未来类似场景中有参考价值
2. **项目特定**：与 Forge 项目的技术栈、架构、部署方式直接相关（通用编程知识不写入）
3. **可执行**：规则描述具体、有明确的判断条件和操作步骤，而非模糊建议
4. **不冗余**：与已有规则不重复；若已有规则覆盖不全则更新已有规则而非新增

### 7.3 执行流程

1. **问题解决后**：先总结根因和解决方案
2. **评估可规则化**：对照 7.2 写入标准判断是否应写入
3. **定位归属章节**：找到最相关的现有章节，或在末尾新增章节
4. **写入并声明**：使用 `edit_file` 写入，完成后在回复中用 `yyb-product` 声明更新
5. **格式要求**：每条规则包含触发条件（何时适用）、执行步骤（怎么做）、反例（常见的错误做法）

### 7.4 本次会话示例（留作模板）

参考本规则本身的写入过程：
- **根因**：Admin 构建后用户反馈"没有变化"，排查发现是 nginx 30 天强缓存 + 浏览器缓存导致
- **规则化**：该经验已写入第 3.2 节（Admin 重建后需硬刷新），属于更新已有规则而非新增

---

*最后更新：2026-08-02*
*（内容由AI生成，仅供参考）*
