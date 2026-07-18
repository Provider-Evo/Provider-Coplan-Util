"""管理员配置类路由：站点设置、套餐目录、模型目录。"""
from __future__ import annotations

import aiohttp.web
from provider_sdk import Route

from provider_coplan_util.handlers.shared import require_admin, require_session


class AdminSettingsRoutesMixin:
    @Route("/v1/coplan/admin/settings", methods=["GET"])
    async def admin_settings_get(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None or record.role != "admin":
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        cfg = self._cfg()
        settings = self._store.get_settings()
        admin_contact = settings.get("admin_contact") or cfg.admin_contact
        return aiohttp.web.json_response({"settings": {"admin_contact": admin_contact}})

    @Route("/v1/coplan/admin/settings", methods=["PUT"])
    async def admin_settings_put(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = require_session(self, request)
        if record is None or record.role != "admin":
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        saved = self._store.save_settings({
            "admin_contact": str(body.get("admin_contact") or ""),
        })
        return aiohttp.web.json_response({"success": True, "settings": saved})


class AdminCatalogRoutesMixin:
    @Route("/api/admin/plans", methods=["GET"])
    async def admin_plans_list(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        return aiohttp.web.json_response({"success": True, "plans": self._catalog.list_plans()})

    @Route("/api/admin/plans", methods=["POST"])
    async def admin_plans_create(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        try:
            plan = self._catalog.create_plan(body)
        except ValueError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True, "plan": plan})

    @Route("/api/admin/plans/{plan_id}", methods=["PUT"])
    async def admin_plans_update(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        plan_id = request.match_info.get("plan_id", "")
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        try:
            plan = self._catalog.update_plan(plan_id, body)
        except KeyError:
            return aiohttp.web.json_response({"error": "套餐不存在"}, status=404)
        except ValueError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True, "plan": plan})

    @Route("/api/admin/plans/{plan_id}", methods=["DELETE"])
    async def admin_plans_delete(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        plan_id = request.match_info.get("plan_id", "")
        if not self._catalog.delete_plan(plan_id):
            return aiohttp.web.json_response({"error": "套餐不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})

    @Route("/api/admin/models", methods=["GET"])
    async def admin_models_list(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        return aiohttp.web.json_response({"success": True, "models": self._catalog.list_models()})

    @Route("/api/admin/models", methods=["POST"])
    async def admin_models_create(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        try:
            body = await request.json()
        except Exception:
            return aiohttp.web.json_response({"error": "invalid json"}, status=400)
        try:
            model = self._catalog.add_model(body)
        except ValueError as exc:
            return aiohttp.web.json_response({"error": str(exc)}, status=400)
        return aiohttp.web.json_response({"success": True, "model": model})

    @Route("/api/admin/models/{model_id}/toggle", methods=["POST"])
    async def admin_models_toggle(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        model_id = request.match_info.get("model_id", "")
        try:
            body = await request.json()
        except Exception:
            body = {}
        is_active = bool(body.get("is_active", True))
        if not self._catalog.toggle_model(model_id, is_active):
            return aiohttp.web.json_response({"error": "模型不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})

    @Route("/api/admin/models/{model_id}", methods=["DELETE"])
    async def admin_models_delete(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        model_id = request.match_info.get("model_id", "")
        if not self._catalog.delete_model(model_id):
            return aiohttp.web.json_response({"error": "模型不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})
