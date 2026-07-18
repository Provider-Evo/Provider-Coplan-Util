"""轻量横切路由：公开信息、前端页面、鉴权与网关 Hook。"""
from __future__ import annotations

from typing import Any, Dict, Optional

import aiohttp.web
from provider_sdk import Hook, Route

from provider_coplan_util import BRAND_NAME, BRAND_TITLE, KEY_PREFIX
from provider_coplan_util.auth.gw_resolve import is_coplan_api_key, resolve_gateway_request
from provider_coplan_util.support.contracts import STRATEGY_PREFIX
from provider_coplan_util.routing.content import build_public_payload
from provider_coplan_util.routing.plans import active_plans


class PublicRoutesMixin:
    @Route("/v1/coplan/public", methods=["GET"])
    async def public_content(self) -> Dict[str, Any]:
        assert self._store is not None
        assert self._catalog is not None
        assert self._market is not None
        cfg = self._cfg()
        payload = build_public_payload(
            cfg,
            self._store.get_settings(),
            self._market.list_entries(),
        )
        if self._standalone is not None and self._standalone.running:
            payload["standalone_url"] = "http://{0}:{1}/".format(cfg.standalone_host, cfg.standalone_port)
        payload["plans"] = active_plans(self._catalog)
        payload["strategy_prefix"] = STRATEGY_PREFIX
        return payload

    @Route("/api/plans", methods=["GET"])
    async def public_plans(self) -> aiohttp.web.Response:
        assert self._catalog is not None
        return aiohttp.web.json_response({
            "success": True,
            "plans": active_plans(self._catalog),
        })

    @Route("/v1/coplan/status", methods=["GET"])
    async def status(self) -> Dict[str, Any]:
        groups = self._store.list_groups() if self._store else []
        cfg = self._cfg()
        market_count = len(self._market.list_entries()) if self._market else 0
        plan_count = len(self._catalog.list_plans(active_only=True)) if self._catalog else 0
        payload = {
            "brand": BRAND_NAME,
            "brand_title": BRAND_TITLE,
            "key_prefix": KEY_PREFIX,
            "hero_tagline": cfg.hero_tagline,
            "strategy_groups": len(groups),
            "strategy_market": market_count,
            "market_templates": market_count,
            "active_plans": plan_count,
            "api_keys": (self._keys.key_count() if self._keys else 0) + (self._store.key_count() if self._store else 0),
            "strategy_prefix": STRATEGY_PREFIX,
            **cfg.as_public_dict(),
        }
        if self._standalone is not None and self._standalone.running:
            payload["standalone_url"] = "http://{0}:{1}/".format(cfg.standalone_host, cfg.standalone_port)
        return payload


class PagesRoutesMixin:
    @Route("/coplan", methods=["GET"])
    async def user_page(self) -> aiohttp.web.Response:
        html_path = self._plugin_path() / "provider_coplan_util" / "frontend_media" / "index.html"
        if not html_path.is_file():
            return aiohttp.web.Response(text="Coplan UI missing", status=404)
        return aiohttp.web.Response(
            text=html_path.read_text(encoding="utf-8"),
            content_type="text/html",
        )

    @Route("/coplan/admin", methods=["GET"])
    async def admin_page(self) -> aiohttp.web.Response:
        html_path = self._plugin_path() / "provider_coplan_util" / "frontend_media" / "admin.html"
        if not html_path.is_file():
            return aiohttp.web.Response(text="Coplan admin UI missing", status=404)
        return aiohttp.web.Response(
            text=html_path.read_text(encoding="utf-8"),
            content_type="text/html",
        )


class HooksMixin:
    @Hook("auth.credentials.validate", order=10)
    async def hook_auth_validate(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        token = str(context.get("token") or "")
        if not is_coplan_api_key(token):
            return None
        if self._keys is None:
            return None
        if self._keys.find_by_secret(token) is None:
            return {"valid": False}
        return {"valid": True}

    @Hook("gateway.request.before", order=10)
    async def hook_gateway_before(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from src.core.server.http.request_context import get_api_token

        token = str(context.get("api_token") or get_api_token() or "")
        if not is_coplan_api_key(token):
            return None
        if (
            self._store is None
            or self._keys is None
            or self._users is None
            or self._catalog is None
            or self._usage is None
        ):
            return {"aborted": True, "abort_reason": "Coplan 插件未就绪"}
        model = str(context.get("model") or "")
        return resolve_gateway_request(
            token=token,
            client_model=model,
            store=self._store,
            keys=self._keys,
            users=self._users,
            catalog=self._catalog,
            usage=self._usage,
        )
