"""多供应商 MCP/API 集成抽象层（P2-5）。

结构：
- base.py      供应商抽象基类与领域异常
- schemas.py   统一货源 DTO
- registry.py  供应商注册表（list/get/register）
- bootstrap.py 显式触发 providers 注册（API/调度器入口 import）
- providers/   厂商适配器实现（zendrop 为首个，后续厂商在此新增）
"""
