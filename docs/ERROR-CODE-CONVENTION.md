# 错误码契约规范（Error Code Convention）

> 全局错误处理统一契约。所有后端接口（C 端 /api/v1、Admin /api/admin/v1）与前端错误展示必须遵循本文档。
> 定位：机器码传输 + 前端本地化映射（对齐 RFC 9457 Problem Details / Stripe error.code / Google AIP-193 ErrorInfo.reason 的行业主线）。

## 1. 核心原则

1. **后端只返回机器可读错误码**：响应体 `code` 为稳定英文大写枚举（如 `EMAIL_ALREADY_REGISTERED`），禁止返回中文/本地化文案。
2. **message 面向开发者**：英文可读、不本地化；**前端禁止直接展示 message 原文**（仅日志/调试使用）。
3. **UI 永不回显**：禁止在页面显示 HTTP 状态码、接口路径（`[POST] /api/...`）、后端原始 detail、i18n key（`auth.passwordMismatch`）等内部产物。
4. **前端语言包 `errors.<code>` 段是唯一用户文案映射表**，key 即后端错误码；新增错误码 = 后端枚举 + 各语言包 errors 段加一行。
5. **缺 key 兜底**：前端映射不到时显示通用文案（`errors.UNKNOWN_ERROR`），生产环境禁止回显 key。
6. **本地化由前端完成**：按当前 locale（zh/en/ar/de/fr）输出对应语言文案，与后端语言无关。

## 2. 响应体结构

所有错误响应统一结构（HTTP 状态码保持语义正确）：

```json
{
  "code": "EMAIL_ALREADY_REGISTERED",
  "message": "Email already registered",
  "status": 409,
  "errors": [
    { "field": "email", "code": "EMAIL_ALREADY_REGISTERED" }
  ]
}
```

| 字段 | 语义 | 是否展示给用户 |
|------|------|---------------|
| `code` | 稳定机器错误码，前端 i18n key 的来源 | 否（经语言包映射后展示） |
| `message` | 英文开发者可读描述 | 否 |
| `status` | HTTP 状态码（冗余便于排查） | 否 |
| `errors[]` | 字段级错误（校验类），可选 | 字段定位（前端定位输入框） |

兼容说明：旧接口响应体仅 `{"detail": "..."}` 将随接口改造逐步迁移到本结构；前端统一解析函数同时兼容读取 `data.code`（优先）与 `data.detail`（迁移期）。

## 3. 错误码规范

### 3.1 两层模型（对齐 Stripe）

- **type（大类）**：UI 通用分支使用（toast 位置、是否可重试），不参与文案
- **code（细码）**：精确文案 key

type 取值：

| type | 含义 | 典型 code |
|------|------|-----------|
| `AUTH_ERROR` | 认证/授权失败 | UNAUTHORIZED / INVALID_CREDENTIALS / ACCOUNT_DISABLED / TOKEN_EXPIRED / FORBIDDEN |
| `VALIDATION_ERROR` | 请求校验失败 | VALIDATION_ERROR / BAD_REQUEST / REQUIRED_FIELD |
| `RESOURCE_ERROR` | 资源不存在/被占用 | NOT_FOUND / USER_NOT_FOUND / EMAIL_ALREADY_REGISTERED |
| `CONFLICT_ERROR` | 状态冲突 | CONFLICT |
| `RATE_LIMIT_ERROR` | 限流 | RATE_LIMITED |
| `SERVER_ERROR` | 服务端异常 | SERVER_ERROR |

### 3.2 code 命名

- 全大写 SNAKE_CASE
- 语义自解释：`<DOMAIN>_<ACTION>_<REASON>`（如 `EMAIL_ALREADY_REGISTERED`、`ORDER_NOT_PAYABLE`）
- 一个 HTTP 状态码可对应多个 code；一个 code 全局唯一
- 认证类 code 不加 `AUTH_` 前缀（兼容存量）；新业务 code 建议带业务域前缀（`ORDER_`、`CATALOG_`、`PAYMENT_`）

### 3.3 唯一权威来源（后端）

`backend/src/forge/api/errors.py` 中的注册表是错误码唯一权威来源：
- code → type / http_status / 英文 message 三合一登记
- 新增错误码只允许在此登记后使用

## 4. 后端使用方式

```python
# 精确错误（推荐）
raise APIError(code=ErrorCode.EMAIL_ALREADY_REGISTERED)
# 或带自定义 message（英文）
raise APIError(code=ErrorCode.EMAIL_ALREADY_REGISTERED, message="User with this email already exists.")
# 字段级校验错误
raise APIError(code=ErrorCode.VALIDATION_ERROR, errors=[FieldError(field="email", code="EMAIL_ALREADY_REGISTERED")])
```

禁止事项：
- 禁止直接 `HTTPException(detail="中文文案")` 向 UI 输出业务文案（兜底 handler 会降级为通用码，业务语义丢失）
- 禁止在响应体中拼接 HTML、前端路由地址
- 禁止把异常栈/数据库错误原文写入响应体

## 5. 前端使用方式

### 5.1 portal-web（Nuxt C 端）

- 运行时语言包 `portal-web/i18n/locales/*.json` 的 `errors` 段 = 映射表
- 统一解析入口 `portal-web/app/composables/useApiError.ts`：FetchError → `{ key, type, fieldErrors }`
- 组件禁止自行拼接错误信息，统一调用解析入口后 `$t(key)`
- 网络/超时错误由解析入口判定为 `errors.NETWORK_ERROR`（本地 key，非后端码）

### 5.2 admin（Vue3 SPA）

- 语言包 `admin/src/locales/langs/{zh-cn,en-us}.ts` 的 `errors` 段 = 映射表
- 统一解析在 `admin/src/service/request/index.ts` onError 完成，业务组件无感知
- 403/409 等非 401 错误同样映射，禁止 toast `error.response.data.detail` 原文

### 5.3 兜底策略（两端一致）

```text
已知 code  → $t("errors." + code)
未知 code  → $t("errors.UNKNOWN_ERROR")   # 通用"操作失败，请稍后重试"
网络错误   → $t("errors.NETWORK_ERROR")
HTTP 4xx 无 body → 按 status 映射通用码（401→UNAUTHORIZED 等）
```

## 6. 新增错误码 SOP（后端 + 前端）

1. 后端 `errors.py` 注册表登记：`code` → type / http_status / message
2. `raise APIError(code=...)` 使用
3. 各语言包 `errors` 段加一行（en/zh/ar/de/fr 或 admin en-us/zh-cn）
4. 运行一致性校验脚本（见 §7），确认枚举与语言包无缺漏
5. 提交 PR 时引用 code（如 commit message 带错误码）

## 7. 一致性校验

`scripts/check-error-codes.py`（仓库根）自动比对：
- 后端注册表 code 集合
- portal-web 运行时语言包 errors 段 key
- admin 语言包 errors 段 key

任一缺失即报错退出（供 pre-commit/CI 接入）。运行：

```bash
python scripts/check-error-codes.py
```

## 8. 边界与 FAQ

- **网络不可达 / 超时**：非后端响应，前端本地 `NETWORK_ERROR`，不入后端注册表
- **5xx**：后端统一 `SERVER_ERROR`，前端提示"服务异常，请稍后重试"，不展示栈信息
- **429 限流**：`RATE_LIMITED`，前端提示稍后重试
- **字段级校验**：优先前端本地校验（即时反馈）；后端 422 由统一 handler 转 `VALIDATION_ERROR` + `errors[]`
- **存量中文 detail 接口**：未迁移前由统一 handler 兜底为通用码，**禁止 UI 展示原文**；迁移到注册表码后获得精确文案
