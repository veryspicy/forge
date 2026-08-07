---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_94b706ef6fdd11f1986d525400d9a7a1
    ReservedCode1: QHxHPs1/4Lj8iQNg/GR8brk7GpSy7/MQpxJGvbjTBm399ln2NTxn8I2oxnsXxxFneFbQ3WL4KUbcxaIpX3Ygz92LLo6E0Ds4QW+xvjmOor3ltVX/86hUebsWOiti/BC7L2f/UWKyUomuxqWEJy7xuOYXheCSNvETrp1twcV6zpxdarqRUClUm4Z1JAY=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_94b706ef6fdd11f1986d525400d9a7a1
    ReservedCode2: QHxHPs1/4Lj8iQNg/GR8brk7GpSy7/MQpxJGvbjTBm399ln2NTxn8I2oxnsXxxFneFbQ3WL4KUbcxaIpX3Ygz92LLo6E0Ds4QW+xvjmOor3ltVX/86hUebsWOiti/BC7L2f/UWKyUomuxqWEJy7xuOYXheCSNvETrp1twcV6zpxdarqRUClUm4Z1JAY=
---

# 认证鉴权安全加固清单

> **背景**：当前认证体系为开发阶段占位实现，生产上线前必须逐项修复。架构设计（共用 JWT + 路径隔离 + 角色依赖注入）本身无问题，风险集中在占位代码。
>
> **涉及文件**：
> - `backend/src/forge/main/dependencies.py`
> - `portal-web/app/middleware/auth.ts`
> - `portal-web/app/composables/useAuth.ts`

---

## P0 — 阻塞上线

### 1. JWT 真实验证

**当前**：`get_current_user_id` 硬编码返回 demo 用户 UUID，不校验 token。

```python
# dependencies.py L43-L45
async def get_current_user_id(authorization: str | None = Header(None)) -> UUID:
    return UUID("00000000-0000-0000-0000-000000000001")
```

**修复要求**：
- 解码 JWT，校验签名（HS256/RS256）
- 校验 `exp` 过期时间
- 从 payload 提取 `sub`(user_id)
- 无效/过期 token 返回 401

---

### 2. 角色从数据库查询

**当前**：`require_role` 为占位，跳过真实角色校验。

```python
# dependencies.py L78-L85
async def role_checker(user_id: str = Depends(get_current_user_id)):
    # TODO: 从数据库查询用户角色
    return user_id
```

**修复要求**：
- 从 `users` 表查询 `role` 字段
- 与 token 中 role 交叉验证（不一致则拒绝）
- 角色不在 `allowed_roles` 中返回 403
- 建议缓存角色查询结果（Redis，TTL 5 分钟）

---

## P1 — 建议上线前完成

### 3. 前端角色路由守卫

**当前**：`middleware/auth.ts` 仅检查 token 存在，不做角色判断。

```typescript
if (to.path.startsWith("/admin")) {
    // Role check will be tightened later
    return;
}
```

**修复要求**：
- 解码 token 读取 role 字段
- 非 `admin` / `operator` 角色访问 `/admin` 时跳转到 403 页面或首页
- `support` 角色仅放行 `/admin/orders`、`/admin/chat-requests`

---

### 4. Cookie 安全加固

**当前**：`forge_token` cookie 缺少关键安全标记。

```typescript
// useAuth.ts
const token = useCookie('forge_token', {
    maxAge: 60 * 60 * 24 * 7,
    sameSite: 'lax',
    // 缺少 httpOnly
    // 缺少 secure
})
```

**修复要求**：
- `httpOnly: true` — 禁止 JS 读取，防 XSS 窃取
- `secure: true` — 仅 HTTPS 传输（开发环境可条件判断）
- `sameSite: 'strict'` — 防 CSRF

---

## P2 — 可在第一期上线后迭代

### 5. Token 刷新机制

**当前**：单 token，7 天静默有效期，无轮换。

**修复要求**：
- 签发 `access_token`（短效，15 分钟）+ `refresh_token`（长效，7 天）
- 前端自动静默刷新，用户无感知
- refresh token 使用后轮换（rotation），防重放

### 6. 登录限流与暴力破解防护

- 登录接口加入 rate-limit（如 5 次/分钟/IP）
- 连续失败锁定账户（如 10 次失败锁定 30 分钟）

---

## 修复顺序建议

```
JWT 真实验证 → 角色查库 → Cookie 加固 → 前端角色守卫 → Token 刷新 → 限流
```

## 完成后清理

全部修复验证通过后，删除本文件。
*（内容由AI生成，仅供参考）*
