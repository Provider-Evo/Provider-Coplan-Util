"""Coplan 策略组规范（Strategy Group Spec v1）。"""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

SPEC_VERSION = 1
STRATEGY_PREFIX = "strategy/"

ROUTING_STRATEGIES = frozenset({
    "single",
    "fallback",
    "round_robin",
    "weighted",
    "random",
})

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

__all__ = [
    "SPEC_VERSION",
    "ROUTING_STRATEGIES",
    "empty_spec",
    "normalize_group",
    "validate_group",
    "route_count",
    "alias_count",
    "list_client_aliases",
    "resolve_routes",
    "STRATEGY_PREFIX",
    "is_strategy_model",
    "parse_strategy_model",
    "strategy_public_id",
]


def empty_spec(group_id: str, name: str) -> Dict[str, Any]:
    """运行时新建策略组的空规范。"""
    return {
        "spec_version": SPEC_VERSION,
        "id": group_id,
        "name": name,
        "description": "",
        "aliases": {},
        "default": {"strategy": "single", "routes": []},
        "constraints": {},
        "limits": {},
    }


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_route(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("route 必须为对象")
    model = str(raw.get("model") or "").strip()
    if not model:
        raise ValueError("route.model 不能为空")
    route: Dict[str, Any] = {"model": model}
    platform = str(raw.get("platform") or "").strip()
    if platform:
        route["platform"] = platform
    weight = raw.get("weight")
    if weight is not None:
        route["weight"] = float(weight)
    params = raw.get("params")
    if isinstance(params, dict) and params:
        route["params"] = params
    return route


def _normalize_alias(alias_key: str, raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"别名 {alias_key!r} 必须为对象")
    strategy = str(raw.get("strategy") or "single").strip().lower()
    if strategy not in ROUTING_STRATEGIES:
        raise ValueError(f"别名 {alias_key!r} 的 strategy 无效: {strategy}")
    routes_raw = raw.get("routes")
    if not isinstance(routes_raw, list) or not routes_raw:
        raise ValueError(f"别名 {alias_key!r} 至少需要一个 route")
    routes = [_normalize_route(item) for item in routes_raw]
    alias: Dict[str, Any] = {
        "match": str(raw.get("match") or alias_key).strip() or alias_key,
        "strategy": strategy,
        "routes": routes,
    }
    description = str(raw.get("description") or "").strip()
    if description:
        alias["description"] = description
    return alias


def normalize_group(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """将 Python dict / StrategyGroup 规范化为持久化结构。"""
    if not isinstance(raw, Mapping):
        raise ValueError("策略组必须为 dict")
    group_id = str(raw.get("id") or "").strip()
    name = str(raw.get("name") or group_id).strip()
    if not group_id:
        raise ValueError("策略组 id 不能为空")
    if not _SLUG_RE.match(group_id):
        raise ValueError(f"策略组 id 须为小写 slug: {group_id!r}")

    aliases_raw = _as_dict(raw.get("aliases"))
    aliases: Dict[str, Any] = {}
    for key, value in aliases_raw.items():
        alias_key = str(key).strip()
        if not alias_key:
            continue
        aliases[alias_key] = _normalize_alias(alias_key, value)

    default_raw = raw.get("default")
    default: Optional[Dict[str, Any]] = None
    if default_raw is not None:
        default = _normalize_alias("__default__", default_raw)

    group: Dict[str, Any] = {
        "spec_version": int(raw.get("spec_version") or SPEC_VERSION),
        "id": group_id,
        "name": name or group_id,
        "description": str(raw.get("description") or "").strip(),
        "aliases": aliases,
        "constraints": dict(_as_dict(raw.get("constraints"))),
        "limits": dict(_as_dict(raw.get("limits"))),
    }
    if default is not None:
        group["default"] = default
    else:
        group["default"] = {"strategy": "single", "routes": [], "match": "*"}

    validate_group(group)
    return group


def validate_group(group: Mapping[str, Any]) -> None:
    """校验策略组规范，失败时抛出 ValueError。"""
    if int(group.get("spec_version") or 0) != SPEC_VERSION:
        raise ValueError(f"不支持的 spec_version: {group.get('spec_version')}")
    group_id = str(group.get("id") or "").strip()
    if not group_id or not _SLUG_RE.match(group_id):
        raise ValueError(f"策略组 id 须为小写 slug: {group_id!r}")
    aliases = group.get("aliases")
    if not isinstance(aliases, dict):
        raise ValueError("aliases 必须为对象")
    for key, alias in aliases.items():
        if not str(key).strip():
            raise ValueError("aliases 键不能为空")
        _normalize_alias(str(key), alias)
    default = group.get("default")
    if default is not None:
        routes = default.get("routes") if isinstance(default, dict) else None
        if isinstance(routes, list) and routes:
            _normalize_alias("__default__", default)


def route_count(group: Mapping[str, Any]) -> int:
    total = 0
    aliases = group.get("aliases")
    if isinstance(aliases, dict):
        for alias in aliases.values():
            if isinstance(alias, dict):
                routes = alias.get("routes")
                if isinstance(routes, list):
                    total += len(routes)
    default = group.get("default")
    if isinstance(default, dict):
        routes = default.get("routes")
        if isinstance(routes, list):
            total += len(routes)
    return total


def alias_count(group: Mapping[str, Any]) -> int:
    aliases = group.get("aliases")
    return len(aliases) if isinstance(aliases, dict) else 0


def list_client_aliases(group: Mapping[str, Any]) -> List[str]:
    aliases = group.get("aliases")
    if not isinstance(aliases, dict):
        return []
    return sorted(str(key) for key in aliases.keys())


def strategy_public_id(group_id: str) -> str:
    slug = str(group_id or "").strip()
    return f"{STRATEGY_PREFIX}{slug}"


def is_strategy_model(client_model: str) -> bool:
    return str(client_model or "").startswith(STRATEGY_PREFIX)


def parse_strategy_model(client_model: str) -> tuple[str, Optional[str]]:
    text = str(client_model or "").strip()
    if not text.startswith(STRATEGY_PREFIX):
        raise ValueError(f"非策略模型: {client_model!r}")
    remainder = text[len(STRATEGY_PREFIX):]
    if not remainder:
        raise ValueError("strategy/ 后须带策略组 id")
    parts = remainder.split("/", 1)
    group_slug = parts[0].strip()
    alias = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    if not group_slug:
        raise ValueError("策略组 id 不能为空")
    return group_slug, alias


def _match_alias(pattern: str, client_model: str) -> bool:
    if pattern == "*" or pattern == client_model:
        return True
    if "*" in pattern:
        regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        return re.match(regex, client_model) is not None
    return False


def resolve_routes(group: Mapping[str, Any], client_model: str) -> Dict[str, Any]:
    """根据客户端 model 解析应使用的路由块（供网关集成）。"""
    aliases = group.get("aliases")
    if isinstance(aliases, dict):
        if client_model in aliases:
            return deepcopy(aliases[client_model])
        for alias in aliases.values():
            if not isinstance(alias, dict):
                continue
            pattern = str(alias.get("match") or "")
            if pattern and _match_alias(pattern, client_model):
                return deepcopy(alias)
    default = group.get("default")
    if isinstance(default, dict) and default.get("routes"):
        return deepcopy(default)
    raise KeyError(client_model)
