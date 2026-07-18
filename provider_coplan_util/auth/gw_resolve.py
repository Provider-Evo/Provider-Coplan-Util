"""gw_resolve 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 gw_resolve 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from provider_coplan_util.auth.access import assert_model_allowed, key_can_use_group, resolve_request_model
from provider_coplan_util import KEY_PREFIX
from provider_coplan_util.stores.catalog_store import CatalogStore
from provider_coplan_util.stores.key_store import UserKeyStore
from provider_coplan_util.support.contracts import is_strategy_model
from provider_coplan_util.stores.store import StrategyStore
from provider_coplan_util.routing.plans import resolve_user_active_plan
from provider_coplan_util.stores.usage_store import UsageStore
from provider_coplan_util.stores.user_store import UserStore

__all__ = ["is_coplan_api_key", "resolve_gateway_request"]


def is_coplan_api_key(token: str) -> bool:
    return bool(token) and token.startswith(KEY_PREFIX)


def _pick_route(route_block: Mapping[str, Any]) -> Tuple[str, str]:
    routes = route_block.get("routes") or []
    if not routes:
        raise PermissionError("策略组未配置可用路由")
    first = routes[0]
    if not isinstance(first, dict):
        raise PermissionError("路由格式无效")
    model = str(first.get("model") or "").strip()
    if not model:
        raise PermissionError("路由缺少 model")
    platform = str(first.get("platform") or "").strip()
    return platform, model


def _resolve_strategy_model_route(
    *,
    model: str,
    group_row_id: str,
    plan: Any,
    key: Mapping[str, Any],
    store: StrategyStore,
    usage: UsageStore,
    username: str,
) -> Dict[str, Any]:
    """处理 strategy/ 模型的路由解析：必须绑定策略组且路由成功。"""
    if not group_row_id:
        return {"aborted": True, "abort_reason": "密钥未绑定策略组，无法使用 strategy/ 模型"}
    group = store.get_group(group_row_id)
    if group is None:
        return {"aborted": True, "abort_reason": "绑定的策略组不存在"}
    try:
        route_block = resolve_request_model(plan=plan, key=key, group=group, client_model=model)
    except PermissionError as exc:
        return {"aborted": True, "abort_reason": str(exc)}
    platform, backend_model = _pick_route(route_block)
    usage.record_request(username)
    return {
        "model": backend_model,
        "platform": platform,
        "coplan": {
            "client_model": model,
            "strategy_group_id": group_row_id,
            "route_strategy": route_block.get("strategy"),
        },
    }


def _resolve_plain_model_route(
    *,
    model: str,
    group_row_id: str,
    plan: Any,
    key: Mapping[str, Any],
    store: StrategyStore,
    usage: UsageStore,
    username: str,
) -> Dict[str, Any]:
    """处理普通模型的路由解析：可选按策略组路由，失败时回退为直传模型名。"""
    if group_row_id:
        group = store.get_group(group_row_id)
        if group is not None and key_can_use_group(key, group):
            try:
                route_block = resolve_request_model(plan=plan, key=key, group=group, client_model=model)
                platform, backend_model = _pick_route(route_block)
                usage.record_request(username)
                return {
                    "model": backend_model,
                    "platform": platform,
                    "coplan": {"client_model": model, "strategy_group_id": group_row_id},
                }
            except (PermissionError, KeyError):
                pass

    usage.record_request(username)
    return {"model": model}


def resolve_gateway_request(
    *,
    token: str,
    client_model: str,
    store: StrategyStore,
    keys: UserKeyStore,
    users: UserStore,
    catalog: CatalogStore,
    usage: UsageStore,
) -> Dict[str, Any]:
    """解析 sk-ent-* 请求：套餐配额 → 密钥模型白名单 → 策略组 → 后端 model/platform。"""
    if not is_coplan_api_key(token):
        return {}
    key = keys.find_by_secret(token)
    if key is None:
        return {"aborted": True, "abort_reason": "invalid_api_key"}
    username = str(key.get("user") or "")
    plan = resolve_user_active_plan(catalog, users, username)
    try:
        usage.assert_within_plan(username, plan)
    except PermissionError as exc:
        return {"aborted": True, "abort_reason": str(exc)}

    model = str(client_model or "").strip()
    group_row_id = str(key.get("strategy_group_id") or "")
    if is_strategy_model(model):
        return _resolve_strategy_model_route(
            model=model, group_row_id=group_row_id, plan=plan, key=key,
            store=store, usage=usage, username=username,
        )

    try:
        assert_model_allowed(plan, key, model)
    except PermissionError as exc:
        return {"aborted": True, "abort_reason": str(exc)}

    return _resolve_plain_model_route(
        model=model, group_row_id=group_row_id, plan=plan, key=key,
        store=store, usage=usage, username=username,
    )
