"""账户认证与策略市场路由。"""
from __future__ import annotations

from typing import Any, Dict

import aiohttp.web
from provider_sdk import Route

from provider_coplan_util import BRAND_NAME
from provider_coplan_util.auth.auth import verify_admin_credentials
from provider_coplan_util.handlers.shared import require_admin, require_session
from provider_coplan_util.routing.plans import active_plans
from provider_coplan_util.routing.user_strat import compile_strategy_source, spec_to_source_code


class AuthRoutesMixin:
    @Route("/api/auth/login", methods=["POST"])
    async def auth_login(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"success": False, "error": "invalid json"}, status=400)
        username = str(body.get("username") or "")
        password = str(body.get("password") or "")
        cfg = self._cfg()
        if verify_admin_credentials(username, password, cfg.admin_username, cfg.admin_password):
            token = self._sessions.issue(cfg.admin_username, role="admin")
            active_plan = self._user_active_plan(cfg.admin_username)
            return aiohttp.web.json_response({
                "success": True,
                "token": token,
                "user": {
                    "username": cfg.admin_username,
                    "role": "admin",
                    "active_plan_id": (active_plan or {}).get("id", ""),
                },
                "activePlan": active_plan,
            })
        assert self._users is not None
        user = self._users.authenticate(username, password)
        if user is None:
            return aiohttp.web.json_response(
                {"success": False, "error": "用户名或密码错误"},
                status=401,
            )
        token = self._sessions.issue(user["username"], role=user.get("role") or "user")
        return aiohttp.web.json_response({
            "success": True,
            "token": token,
            "user": user,
        })

    @Route("/api/auth/register", methods=["POST"])
    async def auth_register(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        from provider_coplan_util.routing.plans import default_active_plan_id

        assert self._users is not None
        assert self._catalog is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"success": False, "error": "invalid json"}, status=400)
        username = str(body.get("username") or "")
        password = str(body.get("password") or "")
        email = str(body.get("email") or "")
        try:
            user = self._users.create_user(
                username,
                password,
                email=email,
                active_plan_id=default_active_plan_id(self._catalog),
            )
        except ValueError as exc:
            return aiohttp.web.json_response({"success": False, "error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True, "user": user})

    @Route("/api/auth/me", methods=["GET"])
    async def auth_me(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录或令牌无效"}, status=401)
        return aiohttp.web.json_response({
            "user": {"username": record.username, "role": record.role},
        })

    @Route("/api/auth/change-password", methods=["POST"])
    async def auth_change_password(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        if record.role == "admin":
            return aiohttp.web.json_response(
                {"error": "管理员请修改插件 config.toml 中 [admin] 密码后重启插件"},
                status=501,
            )
        assert self._users is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        try:
            self._users.change_password(
                record.username,
                str(body.get("current") or body.get("current_password") or ""),
                str(body.get("new") or body.get("new_password") or ""),
            )
        except ValueError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True})


class MarketRoutesMixin:
    @Route("/v1/coplan/market/templates", methods=["GET"])
    async def market_templates(self) -> Dict[str, Any]:
        assert self._market is not None
        assert self._catalog is not None
        entries = self._market.list_entries()
        return {
            "templates": entries,
            "entries": entries,
            "brand": BRAND_NAME,
            "plans": active_plans(self._catalog),
        }

    @Route("/v1/coplan/strategy-market", methods=["GET"])
    async def strategy_market_list(self) -> Dict[str, Any]:
        assert self._market is not None
        entries = self._market.list_entries()
        return {"entries": entries, "count": len(entries)}

    @Route("/v1/coplan/strategy-market", methods=["POST"])
    async def strategy_market_publish(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_admin(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        assert self._market is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        group_id = str(body.get("group_id") or "").strip()
        if not group_id:
            return aiohttp.web.json_response({"error": "group_id required"}, status=400)
        group = self._store.get_group(group_id)
        if group is None:
            return aiohttp.web.json_response({"error": "策略组不存在"}, status=404)
        spec = group.get("spec") or {}
        source_code = self._store.get_group_source_code(group)
        try:
            entry = self._market.publish(
                spec=spec,
                title=str(body.get("title") or group.get("name") or group_id),
                description=str(body.get("description") or group.get("description") or ""),
                author=record.username,
                source_group_id=group_id,
                source_code=source_code,
                tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
            )
        except ValueError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True, "entry": entry})

    @Route("/v1/coplan/strategy-market/{entry_id}/fork", methods=["POST"])
    async def strategy_market_fork(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        assert self._market is not None
        entry_id = request.match_info.get("entry_id", "")
        entry = self._market.get_entry(entry_id)
        if entry is None:
            return aiohttp.web.json_response({"error": "市场条目不存在"}, status=404)
        try:
            body = await request.json()
        except Exception:
            body = {}
        name = str(body.get("name") or entry.get("title") or "forked").strip()
        description = str(entry.get("description") or "")
        source_code = str(entry.get("source_code") or "").strip()
        if not source_code:
            source_code = spec_to_source_code(dict(entry.get("spec") or {}))
        try:
            spec = compile_strategy_source(source_code)
            group = self._store.create_group(
                name,
                description,
                source="runtime",
                source_code=source_code,
                spec=spec,
            )
            self._market.increment_fork(entry_id)
        except (ValueError, KeyError) as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True, "group": group})

    @Route("/v1/coplan/strategy-market/{entry_id}", methods=["GET"])
    async def strategy_market_get(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        assert self._market is not None
        entry_id = request.match_info.get("entry_id", "")
        entry = self._market.get_entry(entry_id)
        if entry is None:
            return aiohttp.web.json_response({"error": "市场条目不存在"}, status=404)
        if not str(entry.get("source_code") or "").strip():
            entry = dict(entry)
            entry["source_code"] = spec_to_source_code(dict(entry.get("spec") or {}))
        return aiohttp.web.json_response({"entry": entry})

    @Route("/v1/coplan/strategy-market/{entry_id}", methods=["DELETE"])
    async def strategy_market_delete(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._market is not None
        entry_id = request.match_info.get("entry_id", "")
        if not self._market.delete_entry(entry_id):
            return aiohttp.web.json_response({"error": "市场条目不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})
