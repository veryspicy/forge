"""Forge 对外 MCP Server（P3）。

将管理后台能力通过 MCP 协议暴露给外部大模型 Agent。
- /mcp/sse       SSE 传输端点
- /mcp/messages/ 客户端消息端点
- API Key 鉴权（SHA-256 哈希存储）
"""

from forge.mcp.server import build_mcp_app

__all__ = ["build_mcp_app"]
