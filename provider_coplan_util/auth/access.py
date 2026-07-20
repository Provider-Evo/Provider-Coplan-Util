

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

from provider_coplan_util.support.contracts import (
    STRATEGY_PREFIX,
    is_strategy_model,
    parse_strategy_model,
    resolve_routes,
)

__all__ = [
    "STRATEGY_PREFIX",
    "plan_allowed_models",
    "effective_allowed_models",
    "assert_model_allowed",
    "resolve_request_model",
    "key_can_use_group",
]


def _parse_json_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except Exception:
            pass
    return []


def plan_allowed_models(plan: Optional[Mapping[str, Any]]) -> Optional[Set[str]]:
    """套餐允许的模型；空集合或 None 表示不限制模型（仅受配额约束）。"""
    if not plan:
        return None
    selected = _parse_json_list(plan.get("selected_models"))
    if not selected:
        return None
    return set(selected)


def effective_allowed_models(
    plan: Optional[Mapping[str, Any]],
    key: Mapping[str, Any],
) -> Optional[Set[str]]:
    """有效允许模型 = 套餐允许 ∩ 密钥允许（套餐优先）。"""
    plan_set = plan_allowed_models(plan)
    key_models = key.get("allowed_models") or []
    key_set = {str(item) for item in key_models if str(item).strip()} if key_models else None
    if plan_set is None and key_set is None:
        return None
    if plan_set is None:
        return set(key_set) if key_set else None
    if key_set is None:
        return set(plan_set)
    return plan_set & key_set


def assert_model_allowed(
    plan: Optional[Mapping[str, Any]],
    key: Mapping[str, Any],
    client_model: str,
) -> None:
    allowed = effective_allowed_models(plan, key)
    if allowed is None:
        return
    model = str(client_model or "").strip()
    if not model:
        raise PermissionError("模型名不能为空")
    if model not in allowed:
        raise PermissionError(f"模型 {model!r} 不在当前套餐与密钥允许范围内")


def key_can_use_group(key: Mapping[str, Any], group: Mapping[str, Any]) -> bool:
    group_id = str(group.get("id") or "")
    allowed_on_group = group.get("allowed_key_ids") or []
    if allowed_on_group and key.get("id") not in allowed_on_group:
        return False
    default_group = str(key.get("strategy_group_id") or "")
    allowed_groups = key.get("allowed_group_ids") or []
    if default_group and group_id == default_group:
        return True
    if allowed_groups and group_id in allowed_groups:
        return True
    if not allowed_on_group and not default_group and not allowed_groups:
        return group.get("owner") == key.get("user")
    return False


def resolve_request_model(
    *,
    plan: Optional[Mapping[str, Any]],
    key: Mapping[str, Any],
    group: Mapping[str, Any],
    client_model: str,
) -> Dict[str, Any]:
    """解析客户端 model（含 strategy/ 前缀）为路由块，并校验套餐/密钥权限。"""
    if not key_can_use_group(key, group):
        raise PermissionError("此 API 密钥无权使用该策略组")
    model = str(client_model or "").strip()
    assert_model_allowed(plan, key, model)

    spec = group.get("spec") or group
    if is_strategy_model(model):
        group_slug, alias = parse_strategy_model(model)
        spec_id = str(spec.get("id") or group.get("id") or "")
        if group_slug != spec_id:
            raise PermissionError(f"策略组 {group_slug!r} 与密钥绑定不一致")
        alias_model = alias or group_slug
        return resolve_routes(spec, alias_model)
    assert_model_allowed(plan, key, model)
    return resolve_routes(spec, model)
