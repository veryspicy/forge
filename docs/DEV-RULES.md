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

> **本项目为单人开发，无多人协作。** 以下规则基于此前提制定。

### 1.1 前置约束：分支必须归集到 dev

**铁律**：每次开始新的 fix 或 feature 开发前，必须先将所有本地分支合并归集到 dev，再从 dev 创建新分支。

**执行步骤**：

1. **检查遗留分支**：`git branch --no-merged dev`
2. **逐一合并或删除**：
   - 有独有提交的分支 → `git merge <branch>` 合入 dev
   - 提交已是 dev 某 commit 的 cherry-pick 等价版 → `git branch -D <branch>` 直接删除
3. **确认归零**：`git branch --no-merged dev` 必须无输出
4. **从 dev 创建新分支**：`git checkout -b fix/<xxx>` 或 `git checkout -b feature/<xxx>`

**cherry-pick 等价判定**：用 `git log --grep="<关键词>" dev` 在 dev 历史中搜索相同功能的 commit，若 commit message 和改动内容一致（仅 SHA 不同），则该分支可安全删除。

**违反后果**：游离分支越积越多，cherry-pick 等价提交难以追溯，最终不知道哪些代码是真正未合入的。

### 1.2 分支命名与合并

遵守 [GIT-WORKFLOW.md](./GIT-WORKFLOW.md) 中定义的 Git Flow 工作流：

- **feature/** 分支：新功能
- **fix/** 分支：Bug 修复
- **hotfix/** 分支：紧急修复
- 合并路径：feature/fix → dev → main
- 提交信息遵循 Conventional Commits 规范
- 禁止创建备份文件（如 `*_backup.py`、`*_old.py`）

### 1.3 合并 dev 验证门禁（强制）

**铁律**：用户明确验证通过之前，禁止将 fix/feature 分支合并到 dev，更禁止 push origin dev。用户说"部署 dev / 部署到 dev / 我要验证"等指令时，语义是**先部署最新代码供用户验证**，不是授权合并提交。

**执行步骤**：

1. 功能分支开发完成后，先本地部署（重建镜像 + 重建容器）供用户验证
2. 用户明确回复"验证通过 / 可以合并 / 提交 dev"等确认语后，才允许 `git merge <branch>` 到 dev 并 push origin dev
3. 用户未验证或验证未通过 → 分支保持本地（可 push 远程功能分支，但**不得**合入 dev），继续修复直至用户确认
4. 部署验证与合并提交是两件事，禁止混为一谈：先部署 → 用户验证 → 再合并

**反例（2026-08-15）**：用户说"现在部署 dev 我要验证"，Marvis 直接执行 `git merge fix/c-end-brand-i18n-rework` 并 `git push origin dev`，将未经验证的代码合入 dev，违反用户真实意图（先部署供验证）。

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
podman exec forge-portal-web rm -rf /app/.nuxt /app/node_modules/.cache
podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml restart portal-web
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

### 3.2 Admin（`admin/` 目录）

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

## 8. 变更行为准则

> **核心原则**：工作区是神圣的。任何一次修改都必须知道它从哪里来、要到哪里去、失败后能否回得去。

### 8.1 禁止残留：失败的尝试必须立即清除

**铁律**：修改了某个文件试图解决问题，但验证后发现无效 → **立刻还原该文件**，一秒都不能留。

理由：残留的半成品代码会在后续排查中伪装成"正常代码"，让你误以为它是原始设计的一部分。从此你排查的不是原始问题，而是你自己制造的第二个问题。

违反后果：你会花几小时追查一个由自己上次的失败尝试造成的新故障，且完全意识不到。

### 8.2 禁止污染：任何时候都要知道工作区里多了什么

**铁律**：在开始排查任何异常之前，**先执行 `git diff` 和 `git status`**。确认当前工作区里有哪些未提交的变更。

理由：如果工作区不干净，你无法判断异常是原始代码的问题还是未提交变更的问题。带着脏工作区排查问题是浪费时间。

违反后果：A 功能出问题 → 排查过程中改了 B → B 也出问题 → 以为是同一个根因 → 越查越深越偏。

### 8.3 禁止盲动：先证明问题存在，再试图修复

**铁律**：在动手改代码之前，必须先用可重复的验证手段（脚本、API 调用、自动化测试）**精确复现并定位问题**。修改只能在定位完成之后进行。

理由：没有精确复现就动手，你改的是空气。改完无法判断是"修好了"还是"恰好没触发"。

违反后果：在错误的地方改了错误的代码，不仅没修好原始问题，还破坏了原本正常的功能。

### 8.4 禁止跳跃：一次只动一个变量

**铁律**：每次只修改一个文件中的一处逻辑，修改后立即验证。验证通过才能进行下一处修改。绝不允许"先改 A，再改 B，最后一起测"。

理由：同时改多处后测试通过，你无法区分是哪一处修改起了作用。同时改多处后测试失败，你无法区分是哪一处修改导致了失败。无论结果如何，信息量为零。

违反后果：问题看似解决了但不知道为什么解决，或者引入了新问题但不知道哪一步引入的。

---

## 9. 会话启动上下文恢复（强制）

**触发时机**：每次 Marvis 开始处理本项目的任务前（新会话或用户重新提到项目），必须先执行本节校验，严禁依赖对话历史摘要代替实际 git 状态检查。

**失败案例（2026-08-01 #2）**：Marvis 在 `fix/c-end-image-proxy` 工作区有 v2.0 实现 + logo 修复 + 图片代理等多项未提交改动，但 `git stash` 后切到 `dev`（仅含 initial commit）创建新分支，完全丢失了所有改动。原因：

1. 依赖对话历史摘要判断代码位置，未实际检查 git 状态
2. 工作区长期堆积未提交改动，跨多轮会话
3. stash 后未记录内容，切分支后遗忘
4. 关键分支（fix/c-end-image-proxy）从未 push 到 remote

**校验清单（必须逐条执行，不可跳过）**：

1. **检查当前 Git 状态**：
   ```bash
   git status --short    # 工作区是否有未提交改动
   git stash list        # stash 栈是否非空
   git branch -v         # 所有本地分支及最新 commit
   git log --oneline -5  # 当前分支最近提交
   ```

2. **工作区不得有遗留改动**：
   - 若 `git status --short` 非空 → 必须先向用户报告有哪些未提交文件，由用户决定 commit / stash / 丢弃
   - 若 `git stash list` 非空 → 必须展示 stash 列表，询问用户是否恢复

3. **确认功能代码所在分支**：
   - 对比各分支 `git log --oneline <branch>` 和 `git diff <branch> --stat`，找出包含最新功能代码的分支
   - 禁止假设 `dev` 包含所有已实现功能；必须以实际 git 历史为准

4. **关键分支必须推送**：
   - 任何承载已验证功能的本地分支，会话结束前必须 `git push origin <branch>`
   - 若推送失败（无权限等），必须明确告知用户分支名和 commit hash

---

## 10. 重建后端到端验证（强制）

**触发时机**：完成容器重建/重启后，必须在用户查看结果前完成端到端验证。禁止仅凭"源码存在"或"静态资源在容器中"就宣布修复成功。

**失败案例（2026-08-01 #3）**：用户反馈"后台服务还是旧版"。Marvis 执行 `podman exec forge-admin ls /usr/share/nginx/html/assets/` 看到 `diy-D1LAQN6n.js` 等 chunk 存在，即宣布"已修复"。实际上：

1. 前端 `diyApi.ts` 调 `/api/admin/v1/diy/pages`（404），后端 v2.0 路由在 `/api/admin/v1/site/pages`
2. 数据库 `diy_pages` 表为空，系统页面（home / category / product_detail）从未种子
3. DIY 页面列表显示空表，用户看到的仍是旧版

**根因**：Marvis 在"静态资源存在"这一步就停止了验证链条，没有继续检查 API 路径 → 后端路由匹配 → 数据库数据 → 页面实际渲染。

**校验清单（必须逐条执行，不可跳过）**：

### 10.1 API 路径一致性检查

对比前端 API 调用路径与后端实际注册路由，确保二者一一对应：

```bash
# 前端 API 文件路径
grep -r "diyApi\|siteApi" admin/src/service/api/
# 后端路由注册
grep -r "include_router\|prefix" backend/src/forge/api/admin/v1/router.py
```

| 检查项 | 方法 |
|--------|------|
| 前端 `listPages` 等调用路径 | 读 `admin/src/service/api/diy.ts` |
| 后端实际路由注册 | 读 `backend/src/forge/api/admin/v1/router.py` |
| 路径是否匹配 | 逐条对比，任一不匹配即为阻断 |

### 10.2 数据链路完整性检查

```bash
# 检查数据库关键表是否有数据
podman exec forge-postgres psql -U postgres -d forge -c "SELECT count(*) FROM diy_pages;"
```

| 检查项 | 方法 |
|--------|------|
| 系统页面是否种子 | 查询 diy_pages 表 page_type IN ('home','category','product_detail') |
| API 是否可达 | `podman exec forge-backend curl -s http://localhost:8000/api/admin/v1/site/pages`（需带 auth header） |
| 列表数据是否返回 | 验证返回 JSON 中 system 数组不为空 |

### 10.3 需求匹配度检查

在宣称"功能正常"之前，必须回顾用户原始需求描述，逐条核对：

| 需求点 | 当前实现 | 是否满足 |
|--------|----------|----------|
| 逐条列出用户需求 | 逐条列出实际实现 | 标注满足/部分/未满足 |

**任一需求点未满足 → 必须如实报告缺口，禁止宣布"正常"。**

---

*最后更新：2026-08-08*
