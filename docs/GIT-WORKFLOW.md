# Git 开发工作流规范 (Git Flow)

> 适用项目：全部  
> 生效日期：2026-07-02（2026-09-03 修订）  
> 本文档为通用 Git 工作流骨架与操作速查。
>
> **权威裁决（2026-09-03）**：Forge 项目现行唯一权威为 [DEV-RULES.md](./DEV-RULES.md)（单人开发模式，含 §1.3 用户验证门禁、§1.4 合并前 CI 健康门禁）。本文档与 DEV-RULES.md 冲突时，一律以 DEV-RULES.md 为准。本文档中面向多人协作的条款（PR-only、Code Review 人数、任务编号必填等）为团队扩展场景的通用模板，Forge 单人流程按下方标注的「单人适配」执行。

---

## 1. 分支模型 (Git Flow)

项目采用业界成熟的 **Git Flow** 分支模型，分支结构如下：

```
main
  └── dev
        ├── feature/xxx
        ├── fix/xxx
        └── release/x.y.z
  └── hotfix/xxx
```

### 1.1 分支类型与职责

| 分支类型 | 用途 | 来源 | 合并目标 | 生命周期 |
|----------|------|------|----------|----------|
| `main` | 生产环境代码，随时可发布 | — | — | 永久 |
| `dev` | 开发主分支，集成所有功能/修复 | — | — | 永久 |
| `feature/xxx` | 新功能开发 | `dev` | `dev` | 功能完成后删除 |
| `fix/xxx` | 非紧急 Bug 修复 | `dev` | `dev` | 修复合并后删除 |
| `hotfix/xxx` | 紧急线上修复 | `main` | `main` + `dev` | 修复合并后删除 |
| `release/x.y.z` | 发布准备（测试、修 Bug、版本号更新） | `dev` | `main` + `dev` | 发布完成后删除 |

### 1.2 分支关系图

```
main ──────●──────────────●──────────────●────── (tag v1.0.0, v1.1.0, v1.1.1)
            ↑              ↑              ↑
dev  ───●───┼──●───●───●──┼──●───●───●──┼──●──
        ↑   │  ↑       ↑  │              │
feature │   │  │       │  │              │
 /xxx ──┘   │  │       │  │              │
            │  │       │  │              │
fix/xxx ────┘  │       │  │              │
               │       │  │              │
release        │       │  │              │
 /x.y.z ───────┘       │  │              │
                        │  │              │
hotfix/xxx ─────────────┘  └──────────────┘
```

---

## 2. 分支命名规范

### 2.1 命名格式

| 分支类型 | 命名格式 | 示例 |
|----------|----------|------|
| feature | `feature/<描述>-<任务编号>` | `feature/user-auth-JIRA-123` |
| fix | `fix/<描述>-<任务编号>` | `fix/login-timeout-JIRA-456` |
| hotfix | `hotfix/<版本号>-<描述>` | `hotfix/v1.1.1-fix-crash` |
| release | `release/<版本号>` | `release/v1.2.0` |

### 2.2 命名规则

- 全部小写，单词间用 `-` 连接
- 描述部分简洁明了，不超过 4 个单词
- 有任务跟踪系统（JIRA / GitHub Issues）时，可在分支名末尾附上编号（**单人适配**：Forge 暂无任务系统，编号可选，可省略）
- 禁止使用个人姓名、日期、无意义编号作为分支名

```bash
# ✅ 正确
feature/oauth2-integration-ISSUE-88
fix/order-duplicate-bug-1024
hotfix/v2.0.1-null-pointer

# ❌ 错误
feature/zhangsan              # 使用个人姓名
fix/20260702                  # 使用日期
feature/aaa                   # 无意义
hotfix/fix                    # 描述不清
```

---

## 3. 提交信息规范 (Conventional Commits)

所有提交信息必须遵循 **Conventional Commits** 规范。

### 3.1 提交格式

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### 3.2 Type 前缀

| 前缀 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(auth): add OAuth2 login support` |
| `fix` | Bug 修复 | `fix(order): resolve duplicate order creation` |
| `docs` | 文档变更 | `docs(readme): update API documentation` |
| `style` | 代码风格（不影响逻辑） | `style: format with black` |
| `refactor` | 重构（非新功能、非修复） | `refactor(db): extract query builder` |
| `perf` | 性能优化 | `perf(api): reduce response time with caching` |
| `test` | 测试相关 | `test(user): add unit tests for user service` |
| `chore` | 构建/工具/依赖 | `chore(deps): bump fastapi to 0.110.0` |
| `ci` | CI/CD 配置 | `ci: add GitHub Actions workflow` |
| `revert` | 回滚提交 | `revert: revert commit abc123` |

### 3.3 规则

- `subject` 使用英文，不超过 72 字符，首字母小写，不加句号
- `scope` 可选但推荐，表示影响模块（如 `auth`、`order`、`db`）
- 破坏性变更在 footer 加 `BREAKING CHANGE:` 说明，或 type 后加 `!`

```bash
# 正确示例
feat(auth): add refresh token rotation
fix(api): handle null pointer in order query
chore(deps): upgrade dependencies
refactor!: drop support for Python 3.8

BREAKING CHANGE: minimum Python version is now 3.9

# 错误示例
update code           # 缺少 type 前缀
Feat: Add Login       # 首字母大写、描述不清晰
fix bug               # 描述太模糊
```

---

## 4. 合并策略

### 4.1 核心原则

**通用场景（多人团队）：禁止直接 push 到 `main` 和 `dev` 分支，所有变更必须通过 Pull Request / Merge Request 合并。**

**单人适配（Forge 现行，依据 DEV-RULES.md §1.3/§1.4）**：单人开发默认走本地 `--no-ff` 合 dev 后 push origin dev；但合并前必须满足两道门禁：

1. §1.3 用户验证门禁——用户明确"验证通过"前禁止合并 dev
2. §1.4 CI 健康门禁——功能分支先 push + 创建 PR 触发 CI，CI 健康（success）后才允许本地 merge 进 dev

> 本地合并是单人流程的执行方式，PR 仍保留：用于触发 CI 验证与变更留痕。

### 4.2 合并流程

**单人适配流程（Forge）**：

| 步骤 | 操作 |
|------|------|
| 1 | 从 dev 切出工作分支 |
| 2 | 在工作分支上开发和提交 |
| 3 | 本地部署验证（重建镜像 + 容器），用户明确"验证通过" |
| 4 | 推送到远程并创建指向 dev 的 PR，触发 CI |
| 5 | CI 健康（success）后本地 `git merge --no-ff <branch>` 到 dev |
| 6 | push origin dev，关注最终 CI run 健康 |

**通用场景（多人团队）**：

| 步骤 | 操作 | 责任人 |
|------|------|--------|
| 1 | 从目标分支切出工作分支 | 开发者 |
| 2 | 在工作分支上开发和提交 | 开发者 |
| 3 | 推送到远程，创建 PR/MR | 开发者 |
| 4 | 触发 CI 自动检查（lint / test / build） | CI 系统 |
| 5 | 至少 1 位团队成员 Code Review | Reviewer |
| 6 | Review 通过后合并到目标分支 | Reviewer / 开发者 |
| 7 | 删除远程工作分支 | 开发者 |

### 4.3 Code Review 要求

**单人适配**：无独立 Reviewer，PR 自查代替 Review（核对变更范围、无调试残留、质量门槛通过）；多人扩展时启用以下通用要求。

**通用场景**：

- 所有 PR/MR 必须至少 **1 人 Approve** 后方可合并
- `main` 分支的 PR/MR 需要 **2 人 Approve**
- Review 关注点：逻辑正确性、安全性、性能、可读性、测试覆盖
- Review 意见必须在合并前全部解决（resolve）

### 4.4 分支保护规则

**Forge 目标态（GitHub 侧设置未完全启用前，由 DEV-RULES.md §1.3/§1.4 门禁兜底）**：

| 分支 | 禁止直接 Push | 要求 PR | 要求 Review | 要求 CI 通过 |
|------|:---:|:---:|:---:|:---:|
| `main` | ✅ | ✅ | 2 人（多人） | ✅ |
| `dev` | ✅（多人） | ✅ | 1 人（多人） | ✅ |
| `feature/*` | — | — | — | 推荐 |
| `fix/*` | — | — | — | 推荐 |
| `hotfix/*` | — | ✅ | 1 人 | ✅ |
| `release/*` | — | ✅ | 1 人 | ✅ |

---

## 5. 发版流程

### 5.1 常规发版

```
1. 从 dev 切出 release/x.y.z
   git checkout -b release/x.y.z dev

2. 在 release 分支上：
   - 更新版本号（package.json / pyproject.toml / __init__.py 等）
   - 更新 CHANGELOG.md
   - 仅修复测试中发现的 Bug，不添加新功能

3. 测试通过后，合并到 main
   git checkout main
   git merge --no-ff release/x.y.z

4. 在 main 上打 Tag
   git tag -a vx.y.z -m "Release vx.y.z"
   git push origin vx.y.z

5. 合并回 dev（确保 dev 包含 release 分支的修复）
   git checkout dev
   git merge --no-ff release/x.y.z

6. 删除 release 分支
   git branch -d release/x.y.z
```

### 5.2 紧急修复发版 (Hotfix)

```
1. 从 main 切出 hotfix 分支
   git checkout -b hotfix/vx.y.(z+1)-<描述> main

2. 修复 Bug，提交

3. 合并到 main
   git checkout main
   git merge --no-ff hotfix/vx.y.(z+1)-<描述>

4. 打 Tag
   git tag -a vx.y.(z+1) -m "Hotfix vx.y.(z+1)"
   git push origin vx.y.(z+1)

5. 合并到 dev
   git checkout dev
   git merge --no-ff hotfix/vx.y.(z+1)-<描述>

6. 删除 hotfix 分支
```

### 5.3 版本号规则 (Semantic Versioning)

格式：`MAJOR.MINOR.PATCH`

| 变更类型 | 版本号 | 示例 |
|----------|--------|------|
| 不兼容的 API 变更 | MAJOR +1，MINOR 和 PATCH 归零 | `v1.2.3` → `v2.0.0` |
| 向下兼容的新功能 | MINOR +1，PATCH 归零 | `v1.2.3` → `v1.3.0` |
| 向下兼容的 Bug 修复 | PATCH +1 | `v1.2.3` → `v1.2.4` |

---

## 6. 禁止行为

### 6.1 分支操作

| 禁止行为 | 说明 |
|----------|------|
| ❌ 直接 push 到 `main` | 必须通过 PR/MR 合并（单人适配：main 仍走 PR 或显式发版流程，禁止随手 push） |
| ❌ 绕过 CI 门禁合入 `dev` | 单人适配：本地合并 + push 前必须先 PR 触发 CI 且健康（DEV-RULES §1.4）；CI 红禁止合并 |
| ❌ 未经验证合入 `dev` | 用户明确"验证通过"前禁止合并 dev（DEV-RULES §1.3） |
| ❌ 强制推送 (`--force`) 到共享分支 | 会覆盖他人提交，禁止对 `main`/`dev`/`release`/`hotfix` 使用 |
| ❌ 使用 `git push --force-with-lease` 到共享分支 | 同上 |
| ❌ 长期不合并的功能分支 | 分支存活不超过 2 周，避免合并冲突累积 |
| ❌ 合并未通过 CI 的 PR | CI 失败必须先修复 |

### 6.2 文件操作

| 禁止行为 | 说明 |
|----------|------|
| ❌ 创建备份文件 | 禁止提交 `*_backup.py`、`*_old.py`、`*_20260629.py`、`*_v2.py` 等备份/旧版文件 |
| ❌ 提交大文件 | 单个文件不超过 10MB，超过使用 Git LFS |
| ❌ 提交敏感信息 | 禁止提交密码、API Key、私钥、`.env` 文件等 |
| ❌ 提交依赖包 | 使用包管理器锁定文件（`requirements.txt` / `pyproject.toml`） |
| ❌ 提交 IDE 配置文件 | 使用 `.gitignore` 排除 `.vscode/`、`.idea/` 等 |

### 6.3 提交操作

| 禁止行为 | 说明 |
|----------|------|
| ❌ 超大提交 | 单次提交变更不超过 500 行，保持原子性 |
| ❌ 无意义提交信息 | 禁止 `WIP`、`fix`、`update`、`tmp` 等模糊描述 |
| ❌ `git commit --amend` 已推送的提交 | 会改写历史，仅允许在本地未推送的提交上使用 |
| ❌ 提交包含调试代码 | 提交前清理 `print()`、`console.log()`、临时注释等 |

---

## 7. 备份文件清理

**状态（2026-09-03 复核）**：`temp\inspect_routes_20260630_212129_567.py` 已清理，当前无遗留备份文件。

> 若发现符合 `*_202*.py`、`*_backup*`、`*_old*` 等模式的备份文件，请列入清理计划确认后删除；禁止提交 `*_backup.py`、`*_old.py`、`*_20260629.py`、`*_v2.py` 等备份/旧版文件（§6.2）。

---

## 8. 快速参考

### 8.1 新功能开发

```bash
git checkout dev
git pull origin dev
git checkout -b feature/<描述>
# ... 开发、提交、本地部署验证（用户确认）...
git push origin feature/<描述>
# 创建 PR → dev（触发 CI）；CI 健康后本地 merge 进 dev 并 push
```

### 8.2 Bug 修复

```bash
git checkout dev
git pull origin dev
git checkout -b fix/<描述>
# ... 修复、提交、本地部署验证（用户确认）...
git push origin fix/<描述>
# 创建 PR → dev（触发 CI）；CI 健康后本地 merge 进 dev 并 push
```

### 8.3 紧急修复

```bash
git checkout main
git pull origin main
git checkout -b hotfix/v<版本>-<描述>
# ... 修复、提交 ...
git push origin hotfix/v<版本>-<描述>
# 创建 PR → main（同时需手动合并到 dev）
```

---

> **最终解释权**：本规范由项目负责人维护，任何异议以本文档为准。违反规范的行为将在 Code Review 阶段被拦截。
