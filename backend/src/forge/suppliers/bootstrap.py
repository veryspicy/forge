"""供应商适配器注册引导（P2-5）。

显式 import 本模块以触发 providers/ 下各厂商调用 register()；
避免在 registry / 包 __init__ 中隐式导入造成的循环依赖与 mypy 推断退化。

用法：API 路由模块与调度器在启动路径中 `import forge.suppliers.bootstrap`。
"""

from forge.suppliers import providers  # noqa: F401
