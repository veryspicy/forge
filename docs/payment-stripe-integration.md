# Stripe 支付渠道接入说明（P0）

> 状态：渠道代码已合入 `feature/payment-stripe`（待验证后 PR 合 dev）
> 适用：backend（渠道适配器）+ portal-web（结账页 / 订单支付弹窗）
> 关联：多渠道支付抽象见 `payment_gateway.py`，PayPal 渠道见 `payment_channels.py`

## 1. 架构位置

```
backend/src/forge/application/services/
├── payment_gateway.py      # PaymentChannel 抽象基类 + PaymentRegistry + MockPaymentChannel
├── payment_channels.py     # PayPalChannel
└── payment_stripe.py       # StripeChannel（本次新增）
```

`StripeChannel` 实现 `PaymentChannel` 四能力：

| 能力 | 实现 | 说明 |
| --- | --- | --- |
| `create_session` | `POST /v1/checkout/sessions` | 托管收银台，返回 `redirect_url`（Stripe 侧 URL） |
| `capture` | `GET /v1/checkout/sessions/{id}` | 回跳后确认支付状态，`paid` 即成功 |
| `refund` | `POST /v1/refunds` | 按 `payment_intent` 退款，支持部分退款 |
| `handle_webhook` | 本地 HMAC-SHA256 验签 | `Stripe-Signature: t=..,v1=..`，5 分钟容差防重放 |

金额换算：Stripe 使用最小货币单位（分）。零小数币种（JPY/KRW 等）按 1:1 处理，其余 ×100，避免日元被放大 100 倍。

## 2. 环境变量

写入 `docker/.env`（不入库），由 `docker/docker-compose.yml` 注入 backend：

```dotenv
STRIPE_SECRET_KEY=            # sk_test_... / sk_live_...
STRIPE_WEBHOOK_SECRET=        # whsec_...（Stripe Dashboard -> Webhooks）
STRIPE_API_BASE=https://api.stripe.com
FORGE_PAYMENT_ENABLED_CHANNELS=stripe,paypal,mock
```

`backend/.env.example` 已同步字段名（值为空）。

## 3. 启用与隐藏规则

`GET /api/v1/orders/payment-channels` 返回站点启用的渠道及其可用性：

```json
{"channels":[
  {"channel":"stripe","flow":"redirect","supports_refund":true,"supported_currencies":["USD","EUR","GBP"],"available":false}
]}
```

- `available=false`：渠道已注册但**凭证缺失**（`configured` 属性为假），C 端不渲染该选项，避免用户选到必然失败的支付方式。
- 未列入 `FORGE_PAYMENT_ENABLED_CHANNELS` 的渠道不会出现在返回中。
- 前端（`checkout.vue`、`orders/[id].vue`）按该接口动态渲染支付方式，接口异常时回退到 mock 网关，保证结账流程不中断。

## 4. 支付链路

```
结账页选择渠道 -> POST /orders（payment_method）
  -> 订单详情页支付：POST /orders/{no}/payment-session {channel}
  -> 有 redirect_url/approve_url：浏览器跳转渠道收银台，完成后回跳 ?st=1 / ?pp=1
  -> 回跳页读取 sessionStorage 会话 -> POST /orders/{no}/payment-capture 确认
  -> webhook（可选，异步兜底）：POST /api/v1/webhooks/stripe
```

回跳参数与会话暂存 key 一一对应：

| 渠道 | 回跳参数 | sessionStorage key |
| --- | --- | --- |
| PayPal | `?pp=1` | `forge_pp_{orderId}` |
| Stripe | `?st=1` | `forge_st_{orderId}` |

## 5. Webhook 配置

Stripe Dashboard → Developers → Webhooks → 添加端点：

- URL：`https://<域名>/api/v1/webhooks/stripe`
- 事件：`checkout.session.completed`、`checkout.session.async_payment_succeeded`、`charge.refunded`
- 签名密钥写入 `STRIPE_WEBHOOK_SECRET`

验签在本地完成（不调用 Stripe 接口），未配置 secret 时接口返回 `PAYMENT_GATEWAY_ERROR / STRIPE_WEBHOOK_SECRET is not configured.`。

## 6. 验证方法

```powershell
# 渠道能力（应看到 stripe，且 available 与凭证是否配置一致）
Invoke-WebRequest http://127.0.0.1:8080/api/v1/orders/payment-channels -UseBasicParsing

# 容器内确认渠道注册状态
podman exec forge-backend python -c "from forge.application.services.payment_gateway import get_payment_registry; r=get_payment_registry(); print([(n, getattr(r.get(n),'configured',None)) for n in ('stripe','paypal','mock')])"

# 单测（17 例：会话/捕获/退款/验签/零小数币种）
cd D:\codeRepo\forge\backend; uv run pytest tests/unit/application/test_payment_stripe.py -q
```

## 7. 当前限制（后续 P0/P1 处理）

| 项 | 现状 | 计划 |
| --- | --- | --- |
| 凭证 | `docker/.env` 未填，渠道对 C 端隐藏 | 用户提供 sk/whsec 后填入并重启 backend |
| 币种 | 全链路仍按站点默认币种下单 | 多币种汇率落单（P0 第 3 项） |
| 税费 | Stripe 会话未带 `tax_amount` | 税费引擎（P0 第 2 项）接入后补 |
| 幂等 | webhook 未做事件去重表 | 优惠码核销同批做事件处理表 |
