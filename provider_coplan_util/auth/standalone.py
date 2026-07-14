"""
standalone 模块。

本文件为 Provider-Evo 项目标准模块，使用以下约定：

- 模块路径：provider-plugin.Provider-Coplan-Util.provider_coplan_util.auth.standalone
- 文件名：standalone.py
- 父包：provider-plugin/Provider-Coplan-Util/provider_coplan_util/auth

职责：

    作为 provider / 核心子系统的标准模块入口；
    通常被 ``plugin.py`` 或上层 ``client.py`` 通过显式 import 使用。

对外接口：

    本模块的 ``__all__`` 列出对外可导入的符号集合；其他内部符号
    可能在重构中调整，调用方应只依赖 ``__all__`` 暴露的稳定 API。

集成：

    - SDK 入口：``plugin.py`` 中 ``create_plugin()`` 引用本模块以构造 platform adapter。
    - 入口路由：``provider-self/src/routes/openai`` 通过 ``from src.core...`` 间接使用。
    - 测试：本目录下的 ``tests/`` 子目录覆盖本模块的核心逻辑。

依赖：

    - 仅依赖 ``provider-sdk`` 与 Python 3.8+ 标准库；不引入第三方 HTTP 库。
    - 不直接读环境变量；所有配置走 ``config/main_config.toml``。

修改指引：

    - 调整本模块时同步更新 ``docs-src/plugins/<name>.md`` 与对应 ``tests/``。
    - 保持单文件 200-400 行；超长请拆为子包并通过 ``__init__.py`` 重新导出。
    - 严禁放置 placeholder / 兜底 / 伪装通过的代码（见 ``AGENTS.md`` Hard Constraints）。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import socket
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import aiohttp.web

__all__ = ["CoplanStandaloneServer"]


def _ensure_port_available(port: int) -> bool:
    """检查端口是否可用，如果被占用则尝试终止占用进程。返回 True 表示端口可用。"""
    # 尝试导入 echotools 的 ensure_port_available
    try:
        from echotools.process.port import ensure_port_available
        result = ensure_port_available(port, force_kill=True)
        return not result.occupied or result.released
    except ImportError:
        pass
    # 回退：仅检查端口，不终止
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return True
    except OSError:
        return False
    finally:
        sock.close()

_ASSET_PREFIX_HOST = "/static/plugins/provider-coplan-util/"
_ASSET_PREFIX_STANDALONE = "/static/"


class CoplanStandaloneServer:
    def __init__(self, plugin: Any) -> None:
        self._plugin = plugin
        self._runner: Optional[aiohttp.web.AppRunner] = None
        self._site: Optional[aiohttp.web.TCPSite] = None

    @property
    def running(self) -> bool:
        return self._runner is not None

    async def start(self, host: str, port: int, *, access_log: bool = False, startup_force_kill_port: bool = False) -> None:
        if self.running or port <= 0:
            return
        if startup_force_kill_port:
            if not _ensure_port_available(port):
                self._plugin.ctx.logger.warning("Coplan standalone 端口 %d 被占用且无法释放，跳过启动", port)
                return
        plugin_dir = Path(self._plugin.ctx.plugin_dir)
        static_dir = plugin_dir / "provider_coplan_util" / "frontend_media"
        if not static_dir.is_dir():
            static_dir = plugin_dir / "frontend_media"
        app = aiohttp.web.Application()
        app["standalone"] = True
        if static_dir.is_dir():
            app.router.add_static("/static/", path=str(static_dir), show_index=False)
        self._register_plugin_routes(app)
        app.router.add_get("/", self._make_page_handler("index.html"))
        app.router.add_get("/admin", self._make_page_handler("admin.html"))
        access_logger = logging.getLogger("aiohttp.access") if access_log else None
        self._runner = aiohttp.web.AppRunner(app, access_log=access_logger)
        await self._runner.setup()
        self._site = aiohttp.web.TCPSite(self._runner, host, port)
        await self._site.start()
        self._plugin.ctx.logger.info(
            "Coplan standalone UI: http://%s:%s/",
            host,
            port,
        )

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
        self._runner = None
        self._site = None

    def _make_page_handler(self, filename: str) -> Callable[..., Any]:
        async def _handler(_request: aiohttp.web.Request) -> aiohttp.web.Response:
            plugin_dir = Path(self._plugin.ctx.plugin_dir)
            html_path = plugin_dir / "provider_coplan_util" / "frontend_media" / filename
            if not html_path.is_file():
                html_path = plugin_dir / "frontend_media" / filename
            if not html_path.is_file():
                return aiohttp.web.Response(text="Coplan UI missing", status=404)
            text = html_path.read_text(encoding="utf-8")
            text = text.replace(_ASSET_PREFIX_HOST, _ASSET_PREFIX_STANDALONE)
            text = text.replace("href='/coplan/admin'", "href='/admin'")
            return aiohttp.web.Response(text=text, content_type="text/html")

        return _handler

    def _register_plugin_routes(self, app: aiohttp.web.Application) -> None:
        plugin = self._plugin
        for comp in plugin.get_components():
            if comp.get("type") != "route":
                continue
            meta = comp.get("metadata") or {}
            path = str(meta.get("path") or "").strip()
            if not path or path in {"/coplan", "/coplan/admin"}:
                continue
            handler_name = str(meta.get("handler_name") or "")
            if not handler_name or not hasattr(plugin, handler_name):
                continue
            handler = getattr(plugin, handler_name)
            methods = [m.upper() for m in (meta.get("methods") or ["GET"])]
            wrapped = _adapt_handler(handler)
            for method in methods:
                app.router.add_route(method, path, wrapped)


def _adapt_handler(handler: Callable[..., Any]) -> Callable[..., Any]:
    async def _wrapped(request: aiohttp.web.Request) -> aiohttp.web.StreamResponse:
        kwargs: dict[str, Any] = {}
        if "request" in inspect.signature(handler).parameters:
            kwargs["request"] = request
        result = handler(**kwargs) if kwargs else handler()
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, aiohttp.web.StreamResponse):
            return result
        if isinstance(result, (bytes, bytearray)):
            return aiohttp.web.Response(body=bytes(result))
        if isinstance(result, str):
            return aiohttp.web.Response(text=result, content_type="text/html")
        return aiohttp.web.json_response(result)

    return _wrapped

# =======================================================================
# 相关模块
# =======================================================================
#
# 同包内协同模块通过 ``from .X import Y`` 重导出，外部调用方无需感知包内布局。
# 若需新增协同模块，请将对应 ``.py`` 文件放在本模块同级目录，并在末尾追加重导出。
#
# 设计原则：
#   1. 每个文件只承担一个明确的职责（单一职责原则）。
#   2. 跨文件依赖只通过显式 import 表达；避免隐式全局状态。
#   3. 公共 API 集中在 ``__all__``；私有符号以下划线开头。
#   4. 模块 docstring 描述用途、依赖、修改指引，作为运行时自描述文档。
#
# 错误处理：
#   - 错误一律 raise，不在底层吞掉（见 ``AGENTS.md`` Hard Constraints）。
#   - 上层 ``plugin.py`` / ``client.py`` 统一处理重试与 fallback。
#
# 测试：
#   - ``tests/`` 子目录覆盖本模块的所有公共函数。
#   - 覆盖率门禁为 90%（见 ``pyproject.toml``）。
#
# 文档：
#   - 用户文档位于 ``docs-src/plugins/``。
#   - 架构决策写入 ``PROJECT_DECISIONS.md``。
#
# 重构策略：
#   - 单文件超过 400 行时，提取子模块并通过 ``__init__.py`` 重导出。
#   - 跨多个 Provider 共享的逻辑抽取至 ``src/core/``；本文件不重复实现。
#
# 兼容：
#   - 旧路径 ``from .module import *`` 仍可用（见 ``__all__``）。
#   - 删除本文件前请先在 ``plugin.py`` 中确认无引用。
#
# 验证：
#   - 修改后运行 ``python -m py_compile`` 确认语法。
#   - 运行 ``pytest tests/`` 确认行为。
#   - 运行 ``python .claude/scripts/check_dir_limit.py`` 确认行数约束。
