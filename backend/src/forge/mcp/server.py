"""MCP Server 主入口（P3）。

- 创建 FastMCP 实例并注册 9 个 Tools（含 scope 校验 + 审计日志包装）
- sse_app() 生成 Starlette 子应用（/mcp/sse + /mcp/messages/）
- 外层 ASGI 中间件做 API Key 鉴权（Authorization: Bearer <api_key>）
"""

from __future__ import annotations

import contextvars
import functools
from collections.abc import Callable, MutableMapping
from typing import Any

from forge.mcp.auth import check_scope, verify_api_key, write_audit_log
from forge.mcp.tools import TOOLS
from mcp.server.fastmcp import FastMCP

# 当前请求绑定的 API Key 记录（由鉴权中间件设置）
_current_key: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("mcp_current_key", default=None)

_MCP_NAME = "forge-mcp"


def build_mcp() -> FastMCP:
    mcp = FastMCP(
        _MCP_NAME,
        instructions=(
            "Forge 电商后台管理接口。可用于创建/查询/更新商品、管理商品上下架与定价、"
            "查询供应商及其商品、获取销售统计。创建商品默认 draft 状态。"
        ),
    )

    for tool_name, (fn, description) in TOOLS.items():
        mcp.add_tool(_wrap_tool(fn, tool_name), name=tool_name, description=description)

    return mcp


def _wrap_tool(fn: Callable[..., Any], tool_name: str) -> Callable[..., Any]:
    """包装工具函数：scope 校验 + 审计日志。"""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = _current_key.get()
        if key is None or not await check_scope(key, tool_name):
            raise PermissionError(f"API Key 无权调用工具 {tool_name}")
        result_status = "ok"
        error = None
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            result_status = "error"
            error = str(exc)
            raise
        finally:
            await write_audit_log(
                api_key_id=key.get("id") if key else None,
                agent_name=key.get("name") if key else None,
                tool_name=tool_name,
                arguments={**kwargs},
                result_status=result_status,
                error=error,
            )

    return wrapper


async def _verify_bearer(authorization: str | None) -> dict[str, Any] | None:
    """从 Authorization header 解析 Bearer token 并校验。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization[7:].strip()
    if not token:
        return None
    key = await verify_api_key(token)
    if key is None:
        return None
    return {"id": str(key.id), "name": key.name, "scopes": list(key.scopes or [])}


async def _auth_middleware(scope: dict, receive: Callable, send: Callable) -> None:
    """ASGI 中间件：/mcp/* 请求必须携带有效 API Key。"""
    if scope["type"] != "http":
        await _inner_app(scope, receive, send)
        return

    # FastAPI mount 传入的 scope["headers"] 可能是 list[tuple] 或 dict，手动解析避免类型差异
    raw_headers = scope.get("headers") or []
    auth_value = ""
    if isinstance(raw_headers, dict):
        for hk, hv in raw_headers.items():
            if hk.lower() in (b"authorization", "authorization"):
                auth_value = hv.decode("latin-1") if isinstance(hv, bytes) else str(hv)
                break
    else:
        for k, v in raw_headers:
            if k.lower() in (b"authorization", "authorization"):
                auth_value = v.decode("latin-1") if isinstance(v, bytes) else str(v)
                break
    key_info = await _verify_bearer(auth_value)

    # SSE 长连接握手后，/messages/ 的 POST 请求通常不带鉴权头（复用 SSE 会话），
    # 此处放行 POST 消息端点，鉴权在 SSE 建立时完成。
    path = scope.get("path", "")
    if key_info is None and not (scope["method"] == "POST" and "/messages/" in path):
        response_started = False

        async def _send_401(message: MutableMapping[str, Any]) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        from starlette.responses import JSONResponse

        resp = JSONResponse({"detail": "Unauthorized: valid API Key required"}, status_code=401)
        await resp(scope, receive, _send_401)
        return

    token = _current_key.set(key_info)
    try:
        await _inner_app(scope, receive, send)
    finally:
        _current_key.reset(token)


_inner_app: Any = None


def build_mcp_app() -> Any:
    """构建挂载到 FastAPI /mcp 的 Starlette 子应用。"""
    global _inner_app
    mcp = build_mcp()
    # mount_path 需为 "/"：外层 FastAPI 已挂 /mcp 并设置 root_path，
    # SDK 生成客户端消息端点 = root_path + mount_path + message_path，
    # 若 mount_path="/mcp" 会导致 /mcp/mcp/messages/ 前缀重复。
    _inner_app = mcp.sse_app(mount_path="/")
    return _auth_middleware
