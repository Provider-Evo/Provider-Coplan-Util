"""管理员策略组管理路由（含 spec 文档、编译、增删）。"""
from __future__ import annotations

from typing import Any, Dict

import aiohttp.web
from provider_sdk import Route

from provider_coplan_util.support.contracts import (
    ROUTING_STRATEGIES,
    SPEC_VERSION,
    STRATEGY_PREFIX,
    alias_count,
    route_count,
    strategy_public_id,
)
from provider_coplan_util.handlers.shared import require_admin, require_session
from provider_coplan_util.routing.user_strat import (
    DEFAULT_USER_STRATEGY_TEMPLATE,
    build_strategy_template,
    compile_strategy_source,
)


class AdminStrategyRoutesMixin:
    @Route("/v1/coplan/strategy-groups", methods=["GET"])
    async def list_groups(self) -> Dict[str, Any]:
        assert self._store is not None
        groups = []
        for group in self._store.list_groups():
            spec = group.get("spec") or {}
            groups.append({
                **group,
                "public_id": strategy_public_id(str(spec.get("id") or group.get("id") or "")),
                "alias_count": alias_count(spec),
                "route_count": route_count(spec),
            })
        return {"groups": groups, "spec_version": SPEC_VERSION, "strategy_prefix": STRATEGY_PREFIX}

    @Route("/v1/coplan/strategy-spec", methods=["GET"])
    async def strategy_spec_doc(self) -> Dict[str, Any]:
        return {
            "spec_version": SPEC_VERSION,
            "strategy_prefix": STRATEGY_PREFIX,
            "routing_strategies": sorted(ROUTING_STRATEGIES),
            "strategies_dir": self._cfg().strategies_dir,
            "python_entry": "STRATEGY_GROUP",
            "user_python_entry": "STRATEGY_GROUP",
            "python_sandbox": "仅允许 STRATEGY_GROUP = {...} 字面量 dict；禁止 import/函数/调用",
            "compile_endpoint": "/v1/coplan/strategy-groups/compile",
            "code_endpoint": "/v1/coplan/strategy-groups/{id}/code",
            "route_fields": ["model", "platform?", "weight?", "params?"],
            "alias_fields": ["match?", "strategy", "routes", "description?"],
            "group_fields": [
                "id",
                "name",
                "description?",
                "aliases",
                "default?",
                "constraints?",
                "limits?",
            ],
        }

    @Route("/v1/coplan/strategy-groups/compile", methods=["POST"])
    async def compile_strategy_code(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
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

    @Route("/v1/coplan/strategy-groups/{group_id}/code", methods=["GET"])
    async def admin_get_strategy_code(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        group = self._store.get_group(group_id)
        if group is None:
            return aiohttp.web.json_response({"error": "group not found"}, status=404)
        return aiohttp.web.json_response({
            "source_code": self._store.get_group_source_code(group),
            "template": DEFAULT_USER_STRATEGY_TEMPLATE,
            "compiled_spec": group.get("spec") or {},
            "readonly": group.get("source") == "code",
            "source_file": group.get("source_file") or "",
        })

    @Route("/v1/coplan/strategy-groups/{group_id}/code", methods=["PUT"])
    async def admin_put_strategy_code(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        source_code = str(body.get("source_code") or "")
        try:
            spec = compile_strategy_source(source_code)
            group = self._store.update_group_code(
                group_id,
                source_code,
                spec,
                admin=True,
            )
        except KeyError:
            return aiohttp.web.json_response({"error": "group not found"}, status=404)
        except (ValueError, PermissionError) as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({
            "group": {**group, "public_id": strategy_public_id(str(spec.get("id") or ""))},
        })

    @Route("/v1/coplan/strategy-groups/{group_id}/spec", methods=["GET"])
    async def get_group_spec(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        group = self._store.get_group(group_id)
        if group is None:
            return aiohttp.web.json_response({"error": "group not found"}, status=404)
        return aiohttp.web.json_response({"group": group})

    @Route("/v1/coplan/strategy-groups/{group_id}/spec", methods=["PUT"])
    async def put_group_spec(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        return aiohttp.web.json_response(
            {
                "error": "策略组请使用 Python 编辑器：PUT /v1/coplan/strategy-groups/{id}/code",
            },
            status=410,
        )

    @Route("/v1/coplan/strategy-groups", methods=["POST"])
    async def create_group(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        name = str(body.get("name") or "").strip()
        if not name:
            return aiohttp.web.json_response({"error": "name required"}, status=400)
        description = str(body.get("description") or "")
        try:
            source_code = build_strategy_template(group_id=name, name=name, description=description)
            spec = compile_strategy_source(source_code)
            group = self._store.create_group(
                name,
                description,
                source="runtime",
                source_code=source_code,
                spec=spec,
            )
        except ValueError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"group": group})

    @Route("/v1/coplan/strategy-groups/{group_id}", methods=["DELETE"])
    async def delete_group(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        try:
            if not self._store.delete_group(group_id):
                return aiohttp.web.json_response({"error": "group not found"}, status=404)
        except PermissionError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=403)
        return aiohttp.web.json_response({"success": True})

    @Route("/v1/coplan/strategy-groups/{group_id}/keys", methods=["POST"])
    async def add_key(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        try:
            body = await request.json()
        except Exception:
            body = {}
        label = str(body.get("label") or "")
        try:
            key_entry = self._store.add_key(group_id, label=label)
        except KeyError:
            return aiohttp.web.json_response({"error": "group not found"}, status=404)
        return aiohttp.web.json_response({"key": key_entry})

    @Route("/v1/coplan/strategy-groups/{group_id}/keys/{key_id}", methods=["DELETE"])
    async def delete_key(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        key_id = request.match_info.get("key_id", "")
        if not self._store.delete_key(group_id, key_id):
            return aiohttp.web.json_response({"error": "key not found"}, status=404)
        return aiohttp.web.json_response({"success": True})
