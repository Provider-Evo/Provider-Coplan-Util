"""Provider-Coplan-Util 插件入口。"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp.web
from provider_sdk import Hook, ProviderPlugin, Route

from provider_coplan_util.auth.auth import SessionStore, verify_admin_credentials
from provider_coplan_util import BRAND_NAME, BRAND_TITLE, KEY_PREFIX
from provider_coplan_util.stores.catalog_store import CatalogStore
from provider_coplan_util.routing.config import load_coplan_config, DEFAULT_MODELS, DEFAULT_PLANS
from provider_coplan_util.routing.content import build_public_payload
from provider_coplan_util.stores.key_store import UserKeyStore
from provider_coplan_util.stores.market_store import StrategyMarketStore
from provider_coplan_util.auth.standalone import CoplanStandaloneServer
from provider_coplan_util.routing.loader import load_strategy_groups
from provider_coplan_util.spec import (
    SPEC_VERSION,
    ROUTING_STRATEGIES,
    STRATEGY_PREFIX,
    alias_count,
    route_count,
    strategy_public_id,
)
from provider_coplan_util.stores.store import StrategyStore
from provider_coplan_util.stores.user_store import UserStore
from provider_coplan_util.routing.user_strategy import (
    DEFAULT_USER_STRATEGY_TEMPLATE,
    build_strategy_template,
    compile_strategy_source,
    spec_to_source_code,
)
from provider_coplan_util.auth.access import resolve_request_model
from provider_coplan_util.auth.gateway_resolver import is_coplan_api_key, resolve_gateway_request
from provider_coplan_util.stores.usage_store import UsageStore


from provider_coplan_util.routing.plans import (
    active_plans,
    default_active_plan_id,
    highest_active_plan_id,
    resolve_user_active_plan,
)


def _bearer_token(request: aiohttp.web.Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


def _require_session(plugin: "CoplanUtilPlugin", request: aiohttp.web.Request) -> Optional[Any]:
    return plugin._sessions.get(_bearer_token(request))


def _require_admin(plugin: "CoplanUtilPlugin", request: aiohttp.web.Request) -> Optional[Any]:
    record = _require_session(plugin, request)
    if record is None or record.role != "admin":
        return None
    return record


class CoplanUtilPlugin(ProviderPlugin):
    def __init__(self) -> None:
        self._store: StrategyStore | None = None
        self._catalog: CatalogStore | None = None
        self._market: StrategyMarketStore | None = None
        self._users: UserStore | None = None
        self._keys: UserKeyStore | None = None
        self._usage: UsageStore | None = None
        self._sessions = SessionStore()
        self._standalone: Optional[CoplanStandaloneServer] = None

    def _user_active_plan(self, username: str) -> Optional[Dict[str, Any]]:
        assert self._users is not None
        assert self._catalog is not None
        return resolve_user_active_plan(self._catalog, self._users, username)

    def _plugin_path(self) -> Path:
        return Path(self.ctx.plugin_dir)

    def _cfg(self):
        return load_coplan_config(self._plugin_path())

    async def on_load(self) -> None:
        data_dir = self._plugin_path() / "provider_coplan_util" / "_data" / "data"
        self._store = StrategyStore(data_dir)
        self._catalog = CatalogStore(data_dir)
        self._catalog.ensure_defaults(DEFAULT_PLANS, DEFAULT_MODELS)
        self._market = StrategyMarketStore(data_dir)
        self._users = UserStore(data_dir)
        self._keys = UserKeyStore(data_dir)
        self._usage = UsageStore(data_dir)
        cfg = self._cfg()
        self._users.ensure_admin_user(
            cfg.admin_username,
            cfg.admin_password,
            active_plan_id=highest_active_plan_id(self._catalog),
        )
        strategies_dir = self._plugin_path() / "provider_coplan_util" / "_data" / cfg.strategies_dir
        try:
            definitions = load_strategy_groups(strategies_dir)
            if definitions:
                synced = self._store.sync_code_groups(definitions)
                self.ctx.logger.info(
                    "Coplan strategies: loaded %d group(s) from %s",
                    len(synced),
                    strategies_dir,
                )
        except ValueError as exc:
            self.ctx.logger.error("Coplan strategies 加载失败: %s", exc)
        self._store.ensure_default_group()
        self.ctx.logger.info(
            "Provider-Coplan-Util: loaded (brand: %s, key_prefix: %s)",
            BRAND_NAME,
            KEY_PREFIX,
        )
        if cfg.standalone_enabled and cfg.standalone_port > 0:
            self._standalone = CoplanStandaloneServer(self)
            try:
                await self._standalone.start(
                    cfg.standalone_host,
                    cfg.standalone_port,
                    access_log=cfg.standalone_access_log,
                    startup_force_kill_port=cfg.standalone_startup_force_kill_port,
                )
            except OSError as exc:
                self.ctx.logger.warning("Coplan standalone 启动失败: %s", exc)
                self._standalone = None

    async def on_unload(self) -> None:
        if self._standalone is not None:
            await self._standalone.stop()
            self._standalone = None

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
            payload["standalone_url"] = f"http://{cfg.standalone_host}:{cfg.standalone_port}/"
        payload["plans"] = active_plans(self._catalog)
        payload["strategy_prefix"] = STRATEGY_PREFIX
        return payload

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
        record = _require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录或令牌无效"}, status=401)
        return aiohttp.web.json_response({
            "user": {"username": record.username, "role": record.role},
        })

    @Route("/api/auth/change-password", methods=["POST"])
    async def auth_change_password(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = _require_session(self, request)
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

    @Route("/api/user/usage", methods=["GET"])
    async def user_usage(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = _require_session(self, request)
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
        record = _require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._keys is not None
        return aiohttp.web.json_response({"keys": self._keys.list_keys(record.username)})

    @Route("/api/user/api-keys", methods=["POST"])
    async def user_create_api_key(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
        if record is None:
            return aiohttp.web.json_response({"error": "未登录"}, status=401)
        assert self._keys is not None
        key_id = request.match_info.get("key_id", "")
        if not self._keys.revoke_key(key_id, record.username):
            return aiohttp.web.json_response({"error": "密钥不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})

    @Route("/api/user/plans", methods=["GET"])
    async def user_plans(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = _require_session(self, request)
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

    @Route("/api/user/strategy-groups", methods=["GET"])
    async def user_strategy_groups(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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
        record = _require_session(self, request)
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

    @Route("/api/plans", methods=["GET"])
    async def public_plans(self) -> aiohttp.web.Response:
        assert self._catalog is not None
        return aiohttp.web.json_response({
            "success": True,
            "plans": active_plans(self._catalog),
        })

    @Route("/v1/coplan/admin/settings", methods=["GET"])
    async def admin_settings_get(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = _require_session(self, request)
        if record is None or record.role != "admin":
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        cfg = self._cfg()
        settings = self._store.get_settings()
        admin_contact = settings.get("admin_contact") or cfg.admin_contact
        return aiohttp.web.json_response({"settings": {"admin_contact": admin_contact}})

    @Route("/v1/coplan/admin/settings", methods=["PUT"])
    async def admin_settings_put(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        record = _require_session(self, request)
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
            payload["standalone_url"] = f"http://{cfg.standalone_host}:{cfg.standalone_port}/"
        return payload

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
        record = _require_session(self, request)
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
        if _require_admin(self, request) is None:
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
        if _require_admin(self, request) is None:
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
        if _require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        return aiohttp.web.json_response(
            {
                "error": "策略组请使用 Python 编辑器：PUT /v1/coplan/strategy-groups/{id}/code",
            },
            status=410,
        )

    @Route("/v1/coplan/strategy-groups", methods=["POST"])
    async def create_group(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if _require_admin(self, request) is None:
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
        if _require_admin(self, request) is None:
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
        record = _require_session(self, request)
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
        if _require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._store is not None
        group_id = request.match_info.get("group_id", "")
        key_id = request.match_info.get("key_id", "")
        if not self._store.delete_key(group_id, key_id):
            return aiohttp.web.json_response({"error": "key not found"}, status=404)
        return aiohttp.web.json_response({"success": True})

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
        record = _require_admin(self, request)
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
        if _require_admin(self, request) is None:
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
        if _require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._market is not None
        entry_id = request.match_info.get("entry_id", "")
        if not self._market.delete_entry(entry_id):
            return aiohttp.web.json_response({"error": "市场条目不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})

    @Route("/api/admin/plans", methods=["GET"])
    async def admin_plans_list(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if _require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        return aiohttp.web.json_response({"success": True, "plans": self._catalog.list_plans()})

    @Route("/api/admin/plans", methods=["POST"])
    async def admin_plans_create(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if _require_admin(self, request) is None:
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
        if _require_admin(self, request) is None:
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
        if _require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        plan_id = request.match_info.get("plan_id", "")
        if not self._catalog.delete_plan(plan_id):
            return aiohttp.web.json_response({"error": "套餐不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})

    @Route("/api/admin/models", methods=["GET"])
    async def admin_models_list(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if _require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        return aiohttp.web.json_response({"success": True, "models": self._catalog.list_models()})

    @Route("/api/admin/models", methods=["POST"])
    async def admin_models_create(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        if _require_admin(self, request) is None:
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
        if _require_admin(self, request) is None:
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
        if _require_admin(self, request) is None:
            return aiohttp.web.json_response({"error": "需要管理员权限"}, status=403)
        assert self._catalog is not None
        model_id = request.match_info.get("model_id", "")
        if not self._catalog.delete_model(model_id):
            return aiohttp.web.json_response({"error": "模型不存在"}, status=404)
        return aiohttp.web.json_response({"success": True})

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


def create_plugin() -> CoplanUtilPlugin:
    return CoplanUtilPlugin()
