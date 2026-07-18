"""插件路由共享辅助函数：会话与鉴权解析。"""
from __future__ import annotations

from typing import Any, Optional

import aiohttp.web


def bearer_token(request: aiohttp.web.Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


def require_session(plugin: Any, request: aiohttp.web.Request) -> Optional[Any]:
    return plugin._sessions.get(bearer_token(request))


def require_admin(plugin: Any, request: aiohttp.web.Request) -> Optional[Any]:
    record = require_session(plugin, request)
    if record is None or record.role != "admin":
        return None
    return record
