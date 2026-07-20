
from __future__ import annotations

import asyncio
import inspect
import logging
import os
import socket
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import aiohttp.web

__all__ = ["CoplanStandaloneServer"]


def _ensure_port_available(port: int) -> bool:
    """检查端口是否可用，如果被占用则尝试终止占用进程。返回 True 表示端口可用。"""
    try:
        from echotools.process.port import ensure_port_available
        result = ensure_port_available(port, force_kill=True)
        if not result.occupied or result.released:
            return True
        # 若占用者全是当前进程本身，则无法自杀；交由 reuse_address=True 处理
        remaining = {p for p in result.pids if p > 0}
        if remaining <= {os.getpid()}:
            return True
        return False
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
        self._site = aiohttp.web.TCPSite(self._runner, host, port, reuse_address=True)
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
