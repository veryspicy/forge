# TRACK-ADMIN-LOGIN-FREEZE · admin 登录后主线程假死问题档案

> 用途：本文件是「admin 登录后页面假死（not-found ↔ root 重定向环）」问题的**唯一留痕档案**。
> 每一次分析、每一个假设（含被推翻的）、每一次代码改动与验证，都必须以追加方式记入本文件，**禁止只改代码不留痕**。
> 新增记录请使用文末「§9 追加模板」，按其编号顺序递增。

| 项 | 内容 |
|---|---|
| 档案编号 | FZ-001 |
| 问题现象 | admin 登录后主线程 100% 停转，浏览器弹「此页面没有响应」，网关侧表现为零请求 |
| 当前状态 | 已修复（d15c7de），回归 PASS，用户硬刷新实测未复现；**保留观察**（复现即重启本档案） |
| 根因 | `authStore.resetStore()` 的 `$reset` 不复位 `isInitAuthRoute`，失效 token 场景下静态鉴权路由被错误置为「已注册」，dashboard 实际未注册，not-found 与 root 互相兜底形成无限重定向环 |
| 修复分支 | `fix/admin-freeze-watchdog`（基于 dev `a4bd1a8`） |
| 关联分支 | `fix/rebuild-discipline-gateway-logs`（A 方案）、`fix/admin-chunk-load-reload`（C 方案，未并入） |
| 关键提交 | `d15c7de` / `85f4367` / `fed1c38` / `bbe2300` / `03f32c8` |
| 最后更新 | 2026-10-03（用户实测未复现，转入观察） |

---

## 1. 现象与量化证据

| 时间 | 证据 | 说明 |
|---|---|---|
| 09-28 20:44:44 | 网关日志：719s 零请求 | 期间含 30s 周期自检窗口，同样无请求 → 排除「慢」而非「停」 |
| 09-28 20:58:11 | 网关日志：434s 零请求 | 同一指纹第二次出现，确认为可重复现象 |
| — | 网关日志 | `login` / `me` 均返回 200 **之后**再无任何请求 |
| — | stall-watchdog 心跳 | sessionStorage `forge:stall-hb` 中 phase 序列呈周期性导航环（非长时冻结无打点），指向路由守卫重定向自旋 |

**指纹判定要点**：`login/me 200` + 之后零请求 + 主线程停转 = 前端登录后处理链问题，不是网络/连接层问题。

---

## 2. 根因链（已闭环）

```
失效 token 场景登录
  └─ initUserInfo 返回 401
      └─ authStore.resetStore()
          └─ $reset 只清 token / userInfo，**不复位 isInitAuthRoute**（残留 true）
              └─ initStaticAuthRoute() 以空 roles 执行，仍把路由标记置为 true
                  └─ dashboard 实际未注册成功
                      └─ 访问 root → redirect 到 dashboard（不存在）→ 落到 not-found
                          └─ not-found 兜底回 root
                              └─ 回到 root redirect …… 无限重定向环 → 主线程 100% 停转
```

关键失效点：`isInitAuthRoute` 是「auth 路由是否已初始化」的 latch，`$reset` 未覆盖它，导致 401 后的重初始化流程被错误跳过。

---

## 3. 分析与改动时间线

> 类型标记：`[分析]` 仅排查未改码 · `[改动]` 有代码/规则/脚本落库 · `[验证]` 验证动作 · `[误判]` 事后被推翻的结论

| # | 日期 | 类型 | 内容 | 结论 / 后续 |
|---|---|---|---|---|
| 1 | 09-28 | [分析] | 收到用户上报 admin 登录后假死，先取网关日志量化冻结窗口 | 得 719s / 434s 两个零请求窗口，确认为主线程停转类问题 |
| 2 | 09-28 | [误判] | 首轮归因为「本机冷启动导致浏览器卡顿」 | ❌ 用户当场纠正并撤回；教训：不得以本机环境状态解释用户现场现象 |
| 3 | 09-28 | [分析] | 插桩 `login-freeze-2/3/4`，跑约 10 轮 CPU profile 尝试自动化复现 | 全部 `NOT_REPRODUCED`；确认真实环境下自动化复现成本极高，转向取证 + 静态路径审查 |
| 4 | 09-30 | [误判] | 静态核查源码后得出「路由守卫自旋已排除」 | ❌ **错误结论**：只看了代码逻辑，未验证 `isInitAuthRoute` 这个 latch 的实际残留状态，导致根因被推迟发现；已记入避坑记忆 |
| 5 | 10-01 | [改动] | **A 方案**：重建纪律 + 网关日志落盘。分支 `fix/rebuild-discipline-gateway-logs` | 保证后续任何复现都有网关侧原始证据可查 |
| 6 | 10-01 18:24 | [改动] | `03f32c8` feat(admin)：新增主线程冻结观测 watchdog 与关键链路打点（`stall-watchdog.ts`） | 后续可从 sessionStorage 心跳还原守卫导航时间序列 |
| 7 | 10-01 18:33 | [改动] | `bbe2300` chore(scripts)：新增 admin 页面冻结静默窗口检测脚本（`analyze-admin-stalls.ps1`） | 支持从日志反查静默窗口 |
| 8 | 10-01 18:34 | [改动] | `fed1c38` docs(dev-rules)：新增 §20「Admin 页面冻结观测与静默窗口检测」 | 把观测手段固化为规则 |
| 9 | 10-01 19:26 | [改动] | `85f4367` fix(scripts)：修正冻结检测脚本格式化参数列表的解析问题 | 检测脚本可用性修复 |
| 10 | 10-02 | [分析] | 用 CDP + 原生 setter 写入 token 完成登录落盘 → 篡改 JWT 为失效值 → reload → 再次登录 | **成功复现冻结**，锁定「失效 token → 重登」这一真实触发路径 |
| 11 | 10-02 | [分析] | 复现态下读取 `isInitAuthRoute=true` 但 `hasDashboard=false` | 根因链闭环，确认 latch 残留 |
| 12 | 10-02 23:01 | [改动] | `d15c7de` fix(admin)：修 `admin/src/router/guard/route.ts`（入口残留态校正 + exist 分支环兜底）、`admin/src/store/modules/route/index.ts`（`resetStore` 显式 `setIsInitAuthRoute(false)`，暴露 `getIsAuthRouteRegistered`） | 三点同时收敛：消除残留、断环、提供可观测读取口 |
| 13 | 10-02 | [验证] | typecheck / lint 通过；重建镜像；跑 `temp/verify-admin-freeze-fix.py` 回归 | 篡改 token 后 reload 得 `isInitAuthRoute=true` / `hasDashboard=false`；再登录 1.0s 落 `/dashboard`，探活 0ms → **PASS** |
| 14 | 10-02 | [验证] | 构建产物核对：`auth-CRy8e0uX.js` 含修复标记 | 确认镜像确实装载了新代码，非「源码存在即宣布成功」 |
| 15 | 10-02 | [分析] | 重建中 `rebuild-admin.ps1` 在网关 reload 步骤因 podman stderr 输出被误判为失败而中断 | 实际 reload 已生效；用 `check-admin.ps1` 手动补跑全通过。已记入避坑记忆 |
| 16 | 10-03 | [验证] | 用户硬刷新 admin 实测 | **未复现**，问题关闭，转观察态 |

---

## 4. 已被排除/推翻的假设（禁止重复走弯路）

| 假设 | 结论 | 排除依据 |
|---|---|---|
| 本机冷启动 / 机器性能导致浏览器卡顿 | ❌ 已推翻 | 用户当场纠正；网关日志显示零请求，与机器性能无关 |
| 网络 / 网关 / 连接层挂起 | ❌ 已排除 | `login` / `me` 均 200，之后零请求；网关侧无异常 |
| 路由守卫重定向自旋（09-30 曾判定「已排除」） | ✅ **实际就是根因** | 09-30 的排除结论本身是误判，arising 于未校验 latch 残留 |
| chunk 加载失败导致白屏卡死 | ⚠️ 未证实为主因 | C 方案作为兜底自愈保留，非本次根因 |
| 靠自动化 CPU profile 批量复现 | ❌ 不可行 | 约 10 轮全 `NOT_REPRODUCED`，环境错配；改为 CDP 定向构造失效 token 复现 |

---

## 5. 已落地改动清单

**代码**
- `admin/src/store/modules/route/index.ts` — `resetStore()` 显式 `setIsInitAuthRoute(false)`；暴露 `getIsAuthRouteRegistered()`
- `admin/src/router/guard/route.ts` — 守卫入口做残留态校正；exist 分支增加环兜底

**观测与脚本**
- `admin/src/**/stall-watchdog.ts` — 主线程冻结观测 + 关键链路打点（`03f32c8`）
- `temp/analyze-admin-stalls.ps1` — 冻结静默窗口检测（`bbe2300` / `85f4367`）
- `temp/verify-admin-freeze-fix.py` — 本问题定向回归脚本

**规则与文档**
- `docs/DEV-RULES.md` §20 — Admin 页面冻结观测与静默窗口检测（`fed1c38`）
- 本档案文件

**其他分支产出（未并入）**
- `fix/rebuild-discipline-gateway-logs` — A 方案：重建纪律 + 网关日志落盘
- `fix/admin-chunk-load-reload` — C 方案：前端 chunk 自愈（`stale-reload.ts`）

---

## 6. 复现与验证方法（下次直接照做）

**复现（CDP 定向构造）**
1. 通过 CDP 用原生 setter 在 localStorage 写入有效 token，完成登录落盘；
2. 篡改 JWT 为失效值；
3. `reload` 页面让 401 路径触发；
4. 再次执行登录 → 观察是否冻结。

**判定修复是否在位**
- 篡改 token 后 reload：应得 `isInitAuthRoute=true` / `hasDashboard=false`；
- 再次登录：应在约 1s 内落到 `/dashboard`，主线程探活 0ms；
- 构建产物名应含修复标记（本轮为 `auth-CRy8e0uX.js`）。

**运行时取证入口**
- 浏览器 Session Storage 键 `forge:stall-hb`：按 phase 时间序列判定「自旋」还是「冻结」；
- 网关落盘 access log：查 `login` / `me` 200 之后是否零请求。

---

## 7. 遗留与待办

- [ ] `fix/admin-chunk-load-reload`（C 方案）尚未并入，需确认是否保留 / 合并；
- [ ] `fix/rebuild-discipline-gateway-logs`（A 方案）尚未并入；
- [ ] 本问题在用户侧转入观察：**若再次复现，回到本档案追加记录，并先核对 §4 已排除假设，不要重复排查**；
- [ ] 本档案是否随 `d15c7de` 一同走 PR 合入 dev，待用户确认。

---

## 8. 环境与账号备忘

- 默认管理员：`admin@forge.dev` / `admin123`（见 `docs/SOP-podman-testing.md`）
- 静态鉴权模式：`VITE_AUTH_ROUTE_MODE=static`，`VITE_ROUTE_HOME=dashboard`
- 容器管理：`podman-compose --project-name docker -f D:\codeRepo\forge\docker\docker-compose.yml`
- Admin 无 HMR：源码变更必须 build --no-cache 重建镜像 + up -d --force-recreate

---

## 9. 追加模板（后续每次分析/改动请复制此块）

```
### [编号] YYYY-MM-DD HH:MM · [分析|改动|验证|误判]
- 触发：
- 观察/证据：
- 结论：
- 动作（文件 / 提交）：
- 推翻或修正了哪条既有结论：
```
