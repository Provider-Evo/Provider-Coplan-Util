"""普通用户路由：用量、API Key、套餐、策略组管理。"""
from __future__ import annotations

import time
from typing import Any, Dict

import aiohttp.web
from provider_sdk import Route

from provider_coplan_util.support.contracts import (
    STRATEGY_PREFIX,
    alias_count,
    route_count,
    strategy_public_id,
)
from provider_coplan_util.handlers.shared import require_session
from provider_coplan_util.routing.user_strat import (
    DEFAULT_USER_STRATEGY_TEMPLATE,
    compile_strategy_source,
    spec_to_source_code,
)


class UserRoutesMixin:
    @Route("/api/user/usage", methods=["GET"])
    async def user_usage(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._keys is not None
        assert self._usage is not None
        active_plan = self._user_active_plan(record.username)
        usage_counts = self._usage.get_usage(record.username)
        key_count = self._keys.key_count(record.username)
        return aiohttp.web.json_response({
            "activePlan": active_plan,
            "currentPeriodUsage": usage_counts,
            "total": {"total_requests": key_count, "total_input_tokens": 0, "total_output_tokens": 0},
            "usage": [],
        })

    @Route("/api/user/api-keys", methods=["GET"])
    async def user_api_keys(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._keys is not None
        return aiohttp.web.json_response({"keys": self._keys.list_keys(record.username)})

    @Route("/api/user/api-keys", methods=["POST"])
    async def user_create_api_key(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._keys is not None
        try:
            body = await request.json()
        except Exception:
            body = {}
        key_entry = self._keys.create_key(
            record.username,
            label=str(body.get("label") or ""),
            strategy_group_id=str(body.get("strategy_group_id") or ""),
            allowed_group_ids=body.get("allowed_group_ids") if isinstance(body.get("allowed_group_ids"), list) else None,
            allowed_models=body.get("allowed_models") if isinstance(body.get("allowed_models"), list) else None,
        )
        return aiohttp.web.json_response({"key": key_entry["key"], "entry": key_entry})

    @Route("/api/user/api-keys/{key_id}", methods=["PUT"])
    async def user_update_api_key(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._keys is not None
        key_id = request.match_info.get("key_id", "")
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        try:
            entry = self._keys.update_key(key_id, record.username, body)
        except KeyError:
            return aiohttp.web.json_response({"error": "密钥不存在"}, status=404)
        return aiohttp.web.json_response({"success": True, "entry": entry})

    @Route("/api/user/api-keys/{key_id}", methods=["DELETE"])
    async def user_revoke_api_key(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._keys is not None
        key_id = request.match_info.get("key_id", "")
        if not self._keys.revoke_key(key_id, record.username):
            return aiohttp.web.json_response({"error": "密钥不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})

    @Route("/api/user/plans", methods=["GET"])
    async def user_plans(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        from provider_coplan_util.routing.plans import active_plans

        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._catalog is not None
        plans = active_plans(self._catalog)
        active = self._user_active_plan(record.username)
        if active is not None:
            active = {**active, "activated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        return aiohttp.web.json_response({
            "plans": [{**p, "activated_at": time.strftime("%Y-%m-%d %H:%M:%S")} for p in plans],
            "activePlan": active,
        })


class StrategyUserRoutesMixin:
    @Route("/api/user/strategy-groups", methods=["GET"])
    async def user_strategy_groups(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        groups = []
        for group in self._store.list_groups(owner=record.username):
            if group.get("owner") and group.get("owner") != record.username:
                continue
            spec = group.get("spec") or {}
            groups.append({
                **group,
                "public_id": strategy_public_id(str(spec.get("id") or group.get("id") or "")),
                "alias_count": alias_count(spec),
                "route_count": route_count(spec),
            })
        return aiohttp.web.json_response({"groups": groups, "strategy_prefix": STRATEGY_PREFIX})

    @Route("/api/user/strategy-groups", methods=["POST"])
    async def user_create_strategy_group(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        name = str(body.get("name") or "").strip()
        if not name:
            return aiohttp.web.json_response({"error": "name required"}, status=400)
        source_code = str(body.get("source_code") or DEFAULT_USER_STRATEGY_TEMPLATE)
        try:
            spec = compile_strategy_source(source_code)
            group = self._store.create_user_group(
                record.username,
                name,
                str(body.get("description") or spec.get("description") or ""),
                source_code=source_code,
                spec=spec,
            )
        except (ValueError, PermissionError) as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        spec = group.get("spec") or {}
        return aiohttp.web.json_response({
            "group": {
                **group,
                "public_id": strategy_public_id(str(spec.get("id") or "")),
            },
        })

    @Route("/api/user/strategy-groups/compile", methods=["POST"])
    async def user_compile_strategy_code(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        source_code = str(body.get("source_code") or "")
        try:
            spec = compile_strategy_source(source_code)
        except ValueError as exc:
            return aiohttp.web.json_response({"success": False, "error": str(exc)}, status=400)
        return aiohttp.web.json_response({
            "success": True,
            "spec": spec,
            "public_id": strategy_public_id(str(spec.get("id") or "")),
        })

    @Route("/api/user/strategy-groups/{group_id}/code", methods=["GET"])
    async def user_get_strategy_code(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        group = self._store.get_group_for_owner(group_id, record.username)
        if group is None or group.get("owner") != record.username:
            return aiohttp.web.json_response({"error": "策略组不存在"}, status=404)
        return aiohttp.web.json_response({
            "source_code": self._store.get_group_source_code(group),
            "template": DEFAULT_USER_STRATEGY_TEMPLATE,
            "compiled_spec": group.get("spec") or {},
            "readonly": group.get("source") == "code",
        })

    @Route("/api/user/strategy-groups/{group_id}/code", methods=["PUT"])
    async def user_put_strategy_code(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        source_code = str(body.get("source_code") or "")
        try:
            spec = compile_strategy_source(source_code)
            group = self._store.update_source_code(group_id, record.username, source_code, spec)
        except KeyError:
            return aiohttp.web.json_response({"error": "策略组不存在"}, status=404)
        except (ValueError, PermissionError) as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        spec = group.get("spec") or {}
        return aiohttp.web.json_response({
            "group": {**group, "public_id": strategy_public_id(str(spec.get("id") or ""))},
        })

    @Route("/api/user/strategy-groups/{group_id}/keys", methods=["PUT"])
    async def user_set_strategy_keys(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        key_ids = body.get("key_ids") if isinstance(body.get("key_ids"), list) else []
        try:
            group = self._store.set_allowed_keys(group_id, record.username, [str(item) for item in key_ids])
        except KeyError:
            return aiohttp.web.json_response({"error": "策略组不存在"}, status=404)
        except PermissionError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=403)
        return aiohttp.web.json_response({"group": group})

    @Route("/api/user/strategy-groups/{group_id}", methods=["DELETE"])
    async def user_delete_strategy_group(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        try:
            if not self._store.delete_group(group_id, owner=record.username):
                return aiohttp.web.json_response({"error": "策略组不存在"}, status=404)
        except PermissionError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=403)
        return aiohttp.web.json_response({"success": True})

    @Route("/api/user/strategy-groups/fork", methods=["POST"])
    async def user_fork_market_entry(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        assert self._market is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        entry_id = str(body.get("market_entry_id") or "").strip()
        if not entry_id:
            return aiohttp.web.json_response({"error": "market_entry_id is required"}, status=400)
        entry = self._market.get_entry(entry_id)
        if entry is None:
            return aiohttp.web.json_response({"error": "市场条目不存在"}, status=404)
        name = str(entry.get("title") or "forked").strip()
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
                owner=record.username,
            )
            self._market.increment_fork(entry_id)
        except (ValueError, KeyError) as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True, "group": group})

    @Route("/api/user/strategy-groups/{group_id}/publish", methods=["POST"])
    async def user_publish_strategy_group(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        assert self._market is not None
        group_id = request.match_info.get("group_id", "")
        group = self._store.get_group_for_owner(group_id, record.username)
        if group is None or group.get("owner") != record.username:
            return aiohttp.web.json_response({"error": "策略组不存在"}, status=404)
        try:
            body = await request.json()
        except Exception:
            body = {}
        spec = group.get("spec") or {}
        source_code = self._store.get_group_source_code(group)
        try:
            entry = self._market.publish(
                spec=spec,
                title=str(body.get("title") or group.get("name") or spec.get("id") or ""),
                description=str(body.get("description") or group.get("description") or ""),
                author=record.username,
                source_group_id=group_id,
                source_code=source_code,
                tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
            )
        except ValueError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True, "entry": entry})

    @Route("/api/user/resolve-model", methods=["POST"])
    async def user_resolve_model(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        from provider_coplan_util.auth.access import resolve_request_model

        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._keys is not None
        assert self._store is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        key_id = str(body.get("key_id") or "")
        client_model = str(body.get("model") or "")
        key = self._keys.get_key(key_id)
        if key is None or key.get("user") != record.username:
            return aiohttp.web.json_response({"error": "密钥不存在"}, status=404)
        group_row_id = str(key.get("strategy_group_id") or body.get("group_id") or "")
        if not group_row_id:
            return aiohttp.web.json_response({"error": "密钥未绑定策略组"}, status=400)
        group = self._store.get_group(group_row_id)
        if group is None:
            return aiohttp.web.json_response({"error": "策略组不存在"}, status=404)
        plan = self._user_active_plan(record.username)
        try:
            routes = resolve_request_model(plan=plan, key=key, group=group, client_model=client_model)
        except PermissionError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=403)
        return aiohttp.web.json_response({"routes": routes, "strategy_prefix": STRATEGY_PREFIX})
