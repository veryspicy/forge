"""支付渠道运行期配置（Admin 配置页 + 启停开关）。

Why this module
---------------
渠道适配器原先直接 ``os.getenv`` 读凭证、启用集合读 ``app_settings``，两者都没有
后台写入口，改一次凭证或开关就得重新发布。这里把「凭证 + 启停」收敛成一份可配置
数据 + 进程内运行期快照，Admin 保存后下一次请求即生效，无需重启容器。

存储
----
- 开关：``app_settings`` key ``payment`` → ``{"enabled_channels": ["stripe", ...]}``
- 凭证：``system_configs`` key ``payment.channels``
  - ``value``：非敏感字段（如 ``STRIPE_API_BASE``、``PAYPAL_MODE``）
  - ``secret_value``：敏感字段（``STRIPE_SECRET_KEY`` 等）的 Fernet 密文 JSON 映射
  - 明文永不落库、永不回显，接口只回 ``*_masked`` / ``*_set``

运行期快照
----------
``refresh(db)`` 从 DB 重建快照（TTL 5s，写操作后 `invalidate()` 立即失效）；
渠道适配器用 ``resolve(channel, key)`` / ``is_channel_enabled(channel)`` 同步读取，
因此「保存即生效」。

优先级：DB 配置 > 环境变量 > 内置默认。环境变量保留为首次部署的无后台场景兜底。
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, cast

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.models import ORMAppSetting, ORMSystemConfig
from forge.infrastructure.services.crypto_service import decrypt_str, encrypt_str, mask_secret

logger = logging.getLogger(__name__)

ENABLED_SETTING_KEY = "payment"
CHANNEL_CONFIG_KEY = "payment.channels"
ENABLED_FIELD = "enabled_channels"
MODE_FIELD = "mode"

# 清空某个已保存的敏感值（前端传该哨兵值）
CLEAR_SENTINEL = "__CLEAR__"

# 运行期快照 TTL（秒）：同一配置下的多次请求不重复查库
SNAPSHOT_TTL_SECONDS = 5.0

DEFAULT_ENABLED_CHANNELS: tuple[str, ...] = ("mock",)


@dataclass(frozen=True)
class CredentialField:
    """一个可后台配置的渠道字段。"""

    key: str
    label: str
    type: str = "text"  # text | secret | select
    required: bool = False
    placeholder: str = ""
    options: tuple[dict[str, str], ...] = ()
    help_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "placeholder": self.placeholder,
            "options": [dict(o) for o in self.options],
            "help_text": self.help_text,
        }


@dataclass(frozen=True)
class ChannelSpec:
    """渠道元信息 + 可配置字段。"""

    channel: str
    name: str
    description: str
    fields: tuple[CredentialField, ...] = ()
    # 判断「已配置」所必需的字段（DB 或 env 任一来源具备即可）
    configured_when: tuple[str, ...] = ()
    docs_url: str = ""

    @property
    def secret_keys(self) -> tuple[str, ...]:
        return tuple(f.key for f in self.fields if f.type == "secret")

    @property
    def plain_keys(self) -> tuple[str, ...]:
        return tuple(f.key for f in self.fields if f.type != "secret")


STRIPE_SPEC = ChannelSpec(
    channel="stripe",
    name="Stripe",
    description="信用卡 / Apple Pay / Google Pay（Stripe Checkout 托管跳转，PCI 范围留在 Stripe 侧）",
    fields=(
        CredentialField(
            key="STRIPE_SECRET_KEY",
            label="Secret Key",
            type="secret",
            required=True,
            placeholder="sk_live_... / sk_test_...",
            help_text="Stripe Dashboard → Developers → API keys。测试密钥以 sk_test_ 开头。",
        ),
        CredentialField(
            key="STRIPE_WEBHOOK_SECRET",
            label="Webhook Signing Secret",
            type="secret",
            placeholder="whsec_...",
            help_text="Webhook 端点 /api/v1/orders/webhooks/stripe 的签名密钥；未配置时 webhook 会被拒绝，"
            "但客户回跳时仍可通过 capture 兜底确认支付。",
        ),
        CredentialField(
            key="STRIPE_API_BASE",
            label="API Base URL",
            type="text",
            placeholder="https://api.stripe.com",
            help_text="仅在使用代理/沙箱网关时需要修改，留空即官方地址。",
        ),
    ),
    configured_when=("STRIPE_SECRET_KEY",),
    docs_url="https://dashboard.stripe.com/apikeys",
)

PAYPAL_SPEC = ChannelSpec(
    channel="paypal",
    name="PayPal",
    description="PayPal 钱包支付（Orders v2，跳转 approve 后 capture）",
    fields=(
        CredentialField(
            key="PAYPAL_CLIENT_ID",
            label="Client ID",
            type="text",
            required=True,
            help_text="PayPal Developer Dashboard → REST apps。",
        ),
        CredentialField(
            key="PAYPAL_CLIENT_SECRET",
            label="Client Secret",
            type="secret",
            required=True,
        ),
        CredentialField(
            key="PAYPAL_MODE",
            label="运行模式",
            type="select",
            options=({"label": "sandbox（沙箱）", "value": "sandbox"}, {"label": "live（生产）", "value": "live"}),
        ),
        CredentialField(
            key="PAYPAL_WEBHOOK_ID",
            label="Webhook ID",
            type="text",
            help_text="Webhook 签名校验用；未配置时 webhook 会被拒绝，客户回跳 capture 仍可兜底。",
        ),
    ),
    configured_when=("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"),
    docs_url="https://developer.paypal.com/dashboard/applications",
)

MOCK_SPEC = ChannelSpec(
    channel="mock",
    name="Mock 测试支付",
    description="本地/QA 专用无真实扣款渠道；生产站点应关闭，避免用户选到假支付。",
)

# 展示顺序即前端卡片顺序；未列出的已注册渠道追加到末尾
CHANNEL_SPECS: dict[str, ChannelSpec] = {
    "stripe": STRIPE_SPEC,
    "paypal": PAYPAL_SPEC,
    "mock": MOCK_SPEC,
}

CHANNEL_ORDER: tuple[str, ...] = ("stripe", "paypal", "mock")


# --------------------------------------------------------------------------- #
# 运行期快照
# --------------------------------------------------------------------------- #


@dataclass
class _RuntimeSnapshot:
    credentials: dict[str, dict[str, str]] = field(default_factory=dict)
    enabled: list[str] = field(default_factory=list)
    loaded_at: float = 0.0


_SNAPSHOT: _RuntimeSnapshot = _RuntimeSnapshot(loaded_at=0.0)


def invalidate() -> None:
    """使运行期快照立即失效（配置写入后调用）。"""
    _SNAPSHOT.loaded_at = 0.0


def _snapshot_is_fresh() -> bool:
    return _SNAPSHOT.loaded_at > 0 and (time.monotonic() - _SNAPSHOT.loaded_at) < SNAPSHOT_TTL_SECONDS


async def refresh(db: AsyncSession, *, force: bool = False) -> None:
    """从 DB 重建运行期快照（TTL 内跳过）。"""
    if not force and _snapshot_is_fresh():
        return
    try:
        credentials = await _decrypted_credentials(db)
        enabled = await load_enabled_channels(db)
    except Exception:  # noqa: BLE001 - 配置读取失败不应打断支付链路
        logger.exception("payment config refresh failed; keeping previous snapshot")
        return
    _SNAPSHOT.credentials = credentials
    _SNAPSHOT.enabled = enabled
    _SNAPSHOT.loaded_at = time.monotonic()


def resolve(channel: str, key: str) -> str | None:
    """同步读取渠道配置值：运行期快照（DB）> 环境变量 > None。"""
    value = (_SNAPSHOT.credentials.get(channel) or {}).get(key)
    if value:
        return value
    env_value = os.getenv(key)
    return env_value or None


def is_channel_enabled(channel: str) -> bool:
    """同步判定渠道是否启用（快照未加载时按默认集合兜底）。"""
    enabled = _SNAPSHOT.enabled or list(DEFAULT_ENABLED_CHANNELS)
    return channel.lower() in {c.lower() for c in enabled}


# --------------------------------------------------------------------------- #
# 读写（DB）
# --------------------------------------------------------------------------- #


async def _load_channel_row(db: AsyncSession) -> ORMSystemConfig | None:
    return (
        await db.execute(select(ORMSystemConfig).where(ORMSystemConfig.key == CHANNEL_CONFIG_KEY))
    ).scalar_one_or_none()


def _decode_secret_map(row: ORMSystemConfig | None) -> dict[str, dict[str, str]]:
    """解密 ``secret_value`` → {channel: {field: 明文}}；损坏记录按空处理并告警。"""
    if row is None or not row.secret_value:
        return {}
    try:
        raw = decrypt_str(str(row.secret_value))
        payload = json.loads(raw) if raw else {}
    except Exception:  # noqa: BLE001 - 历史脏数据/密钥轮换后无法解密，不应导致支付全挂
        logger.warning("payment channel secret blob is not decryptable; treating as empty")
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for channel, values in payload.items():
        if isinstance(values, dict):
            result[str(channel)] = {str(k): str(v) for k, v in values.items() if v not in (None, "")}
    return result


async def _decrypted_credentials(db: AsyncSession) -> dict[str, dict[str, str]]:
    row = await _load_channel_row(db)
    return _decode_secret_map(row)


async def load_enabled_channels(db: AsyncSession) -> list[str]:
    """启用渠道集合：app_settings ``payment.enabled_channels`` > env > 默认 mock。"""
    row = (
        await db.execute(select(ORMAppSetting).where(ORMAppSetting.key == ENABLED_SETTING_KEY))
    ).scalar_one_or_none()
    value = row.value if row is not None else None
    if isinstance(value, dict):
        enabled = value.get(ENABLED_FIELD)
        if isinstance(enabled, list):
            return [str(c).strip().lower() for c in enabled if str(c).strip()]
    raw_env = os.getenv("FORGE_PAYMENT_ENABLED_CHANNELS")
    if raw_env:
        channels = [c.strip().lower() for c in raw_env.split(",") if c.strip()]
        if channels:
            return channels
    return list(DEFAULT_ENABLED_CHANNELS)


async def _payment_setting(db: AsyncSession) -> dict[str, Any]:
    row = (
        await db.execute(select(ORMAppSetting).where(ORMAppSetting.key == ENABLED_SETTING_KEY))
    ).scalar_one_or_none()
    value = row.value if row is not None else None
    return dict(value) if isinstance(value, dict) else {}


async def save_enabled_channels(
    db: AsyncSession,
    channels: list[str],
    updated_by: str | None = None,
) -> list[str]:
    """整体保存启用渠道集合（顺序即 C 端展示顺序）。"""
    ordered: list[str] = []
    seen: set[str] = set()
    for channel in channels:
        name = str(channel).strip().lower()
        if not name or name in seen:
            continue
        if name not in CHANNEL_SPECS:
            raise APIError(
                ErrorCode.VALIDATION_ERROR,
                message=f"Unknown payment channel: {name}",
            )
        seen.add(name)
        ordered.append(name)
    if not ordered:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            message="At least one payment channel must stay enabled.",
        )
    setting = await _payment_setting(db)
    setting[ENABLED_FIELD] = ordered
    row = (
        await db.execute(select(ORMAppSetting).where(ORMAppSetting.key == ENABLED_SETTING_KEY))
    ).scalar_one_or_none()
    if row is None:
        row = ORMAppSetting(key=ENABLED_SETTING_KEY, value=setting, updated_by=updated_by)
        db.add(row)
    else:
        row.value = cast(Any, setting)
        row.updated_by = cast(Any, updated_by)
    invalidate()
    return ordered


async def set_channel_enabled(
    db: AsyncSession,
    channel: str,
    enabled: bool,
    updated_by: str | None = None,
) -> list[str]:
    """单独启停某个渠道，返回保存后的启用集合。"""
    name = channel.strip().lower()
    if name not in CHANNEL_SPECS:
        raise APIError(ErrorCode.VALIDATION_ERROR, message=f"Unknown payment channel: {name}")
    current = await load_enabled_channels(db)
    if enabled and name not in current:
        current.append(name)
    elif not enabled:
        current = [c for c in current if c != name]
    if not current:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            message="At least one payment channel must stay enabled.",
        )
    return await save_enabled_channels(db, current, updated_by=updated_by)


async def save_credentials(
    db: AsyncSession,
    channel: str,
    values: dict[str, Any],
    updated_by: str | None = None,
) -> None:
    """保存渠道凭证：敏感字段加密入库，空值保留原值，``__CLEAR__`` 表示清除。"""
    name = channel.strip().lower()
    spec = CHANNEL_SPECS.get(name)
    if spec is None:
        raise APIError(ErrorCode.VALIDATION_ERROR, message=f"Unknown payment channel: {name}")
    if not spec.fields:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            message=f"Payment channel '{name}' has no configurable credentials.",
        )
    allowed = {f.key: f for f in spec.fields}
    unknown = [k for k in values if k not in allowed]
    if unknown:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            message=f"Unsupported credential field(s): {', '.join(sorted(unknown))}",
        )

    row = await _load_channel_row(db)
    plain_map: dict[str, Any] = {}
    secret_map: dict[str, dict[str, str]] = {}
    if row is not None:
        plain_map = dict(row.value) if isinstance(row.value, dict) else {}
        secret_map = _decode_secret_map(row)

    channel_plain: dict[str, Any] = dict(plain_map.get(name) or {})
    channel_secret: dict[str, str] = dict(secret_map.get(name) or {})

    for key, raw in values.items():
        if raw is None:
            continue
        text = str(raw).strip()
        target = channel_secret if allowed[key].type == "secret" else channel_plain
        if text == CLEAR_SENTINEL:
            target.pop(key, None)
            continue
        if text == "":
            # 留空 = 保留原值（避免前端无法回显明文时误清空）
            continue
        if allowed[key].type == "select":
            options = {o["value"] for o in allowed[key].options}
            if options and text not in options:
                raise APIError(
                    ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid value for {key}: {text}",
                )
        target[key] = cast(Any, text)

    secret_map[name] = channel_secret
    plain_map[name] = channel_plain

    encrypted = encrypt_str(json.dumps(secret_map, ensure_ascii=False)) if secret_map else None
    if row is None:
        row = ORMSystemConfig(
            key=CHANNEL_CONFIG_KEY,
            value=plain_map,
            secret_value=encrypted,
            is_secret=bool(secret_map),
            updated_by=updated_by,
        )
        db.add(row)
    else:
        row.value = cast(Any, plain_map)
        row.secret_value = cast(Any, encrypted)
        row.is_secret = cast(Any, bool(secret_map))
        row.updated_by = cast(Any, updated_by)
    invalidate()


async def load_channel_states(db: AsyncSession) -> list[dict[str, Any]]:
    """Admin 配置页数据源：渠道 + 启停 + 凭证（脱敏）。"""
    row = await _load_channel_row(db)
    plain_map: dict[str, Any] = dict(row.value) if row is not None and isinstance(row.value, dict) else {}
    secret_map = _decode_secret_map(row)
    enabled = await load_enabled_channels(db)
    enabled_set = {c.lower() for c in enabled}

    states: list[dict[str, Any]] = []
    for name in _all_channels():
        spec = CHANNEL_SPECS.get(name) or ChannelSpec(channel=name, name=name, description="")
        channel_plain = plain_map.get(name) or {}
        channel_secret = secret_map.get(name) or {}
        fields: list[dict[str, Any]] = []
        for f in spec.fields:
            is_secret = f.type == "secret"
            value = "" if is_secret else str(channel_plain.get(f.key) or "")
            saved_value = str(channel_secret.get(f.key) or "") if is_secret else value
            fields.append(
                {
                    **f.to_dict(),
                    "value": value,
                    "saved": bool(saved_value),
                    "masked": mask_secret(saved_value) if (is_secret and saved_value) else "",
                }
            )
        states.append(
            {
                "channel": name,
                "name": spec.name,
                "description": spec.description,
                "enabled": name in enabled_set,
                "configured": _is_configured(spec, channel_plain, channel_secret),
                "fields": fields,
                "docs_url": spec.docs_url,
            }
        )
    return states


def _all_channels() -> list[str]:
    """已注册渠道 ∪ 已知渠道，按 CHANNEL_ORDER 排序。"""
    try:
        from forge.application.services.payment_gateway import get_payment_registry

        registered = set(get_payment_registry().available())
    except Exception:  # noqa: BLE001 - 循环依赖/初始化失败时退化为静态清单
        registered = set(CHANNEL_SPECS)
    names = [c for c in CHANNEL_ORDER if c in registered or c in CHANNEL_SPECS]
    names += sorted(registered - set(names))
    return names


def _is_configured(spec: ChannelSpec, plain: dict[str, Any], secret: dict[str, str]) -> bool:
    """凭证是否齐备：DB 与 env 合并判定。"""
    required = spec.configured_when
    if not required:
        return True
    for key in required:
        if secret.get(key):
            continue
        if plain.get(key):
            continue
        if os.getenv(key):
            continue
        return False
    return True


# --------------------------------------------------------------------------- #
# 连通性测试
# --------------------------------------------------------------------------- #


async def test_channel(db: AsyncSession, channel: str) -> dict[str, Any]:
    """用当前生效配置做一次只读连通性探测（不产生任何扣款）。"""
    name = channel.strip().lower()
    await refresh(db, force=True)
    if name == "stripe":
        return await _test_stripe()
    if name == "paypal":
        return await _test_paypal()
    return {"channel": name, "ok": True, "message": "该渠道无需凭证，无需测试。"}


async def _test_stripe() -> dict[str, Any]:
    secret = resolve("stripe", "STRIPE_SECRET_KEY")
    if not secret:
        return {"channel": "stripe", "ok": False, "message": "未配置 Secret Key。"}
    base = (resolve("stripe", "STRIPE_API_BASE") or "https://api.stripe.com").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{base}/v1/balance", headers={"Authorization": f"Bearer {secret}"})
    except httpx.HTTPError as exc:
        return {"channel": "stripe", "ok": False, "message": f"网络错误：{exc}"}
    if resp.status_code == 200:
        livemode = bool(resp.json().get("livemode"))
        mode = "live" if livemode else "test"
        return {"channel": "stripe", "ok": True, "message": f"连接成功，密钥模式：{mode}。"}
    detail = ""
    try:
        detail = str((resp.json().get("error") or {}).get("message") or "")
    except Exception:  # noqa: BLE001 - 错误体结构不保证
        detail = (resp.text or "")[:200]
    return {
        "channel": "stripe",
        "ok": False,
        "message": f"Stripe 返回 HTTP {resp.status_code}。{detail}".strip(),
    }


async def _test_paypal() -> dict[str, Any]:
    client_id = resolve("paypal", "PAYPAL_CLIENT_ID")
    client_secret = resolve("paypal", "PAYPAL_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {"channel": "paypal", "ok": False, "message": "未配置 Client ID / Client Secret。"}
    mode = (resolve("paypal", "PAYPAL_MODE") or "sandbox").lower()
    base = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{base}/v1/oauth2/token",
                headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
                content="grant_type=client_credentials",
            )
    except httpx.HTTPError as exc:
        return {"channel": "paypal", "ok": False, "message": f"网络错误：{exc}"}
    if resp.status_code == 200:
        return {"channel": "paypal", "ok": True, "message": f"连接成功，模式：{mode}。"}
    return {
        "channel": "paypal",
        "ok": False,
        "message": f"PayPal 返回 HTTP {resp.status_code}（通常是 Client ID/Secret 与模式不匹配）。",
    }
