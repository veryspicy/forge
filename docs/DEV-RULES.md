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

### 3.4 重建前置条件：分支代码完整性校验（强制）

**适用场景**：执行任何会触发容器重建或重启的操作之前（包括 `podman compose up -d`、`podman build`、`podman compose restart` 等），必须完成本节校验。

**背景**：`podman compose up -d` 会用磁盘当前分支的代码重建镜像。如果当前分支缺少某些功能的代码（例如 `fix/xxx` 分支从 `dev` 切出，而某功能代码仅在 `feature/xxx` 分支），重建后容器就会回退到缺失该功能的版本。这是**不可逆的功能回退**，必须杜绝。

**校验清单**（必须逐条执行，不可跳过）：

1. **确认当前分支**：`git branch --show-current`，确认当前所在分支名称。
2. **确认分支来源**：`git merge-base <当前分支> dev`，确认当前分支的基提交是否包含 dev 最新代码。如果当前分支是 `fix/` 或 `feature/` 类型，必须确认它已包含所有必要的前置功能代码。
3. **代码完整性检查**：
   - Admin 容器重建前：确认 `admin/build/` 或 `admin/src/` 目录含有所需的页面/功能源码
   - 对比 `dev` 分支与当前分支的关键文件差异：`git diff dev --stat <关键目录>`
4. **若当前分支缺少必要代码**：必须先 `git merge <包含所需代码的分支>`，解决冲突后再继续。严禁在缺失代码的分支上直接重建容器。

**失败案例（2026-08-01）**：`fix/c-end-image-proxy` 从 `dev`（仅含 initial commit）切出，DIY 页面装修代码全在 `feature/docs-diy-page-decoration`。在该 fix 分支上执行 `podman compose up -d` 重建 admin 容器，导致 Admin 回退到无 DIY 功能的版本。根因：未校验分支代码完整性。

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

## 7. 会话启动上下文恢复（强制）

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

*最后更新：2026-08-01*
*（内容由AI生成，仅供参考）*
