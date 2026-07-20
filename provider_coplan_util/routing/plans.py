

from __future__ import annotations

from typing import Any, Dict, List, Optional

from provider_coplan_util.stores.catalog_store import CatalogStore
from provider_coplan_util.stores.user_store import UserStore

__all__ = [
    "active_plans",
    "default_active_plan_id",
    "highest_active_plan_id",
    "resolve_user_active_plan",
]


def active_plans(catalog: CatalogStore) -> List[Dict[str, Any]]:
    return _active_plans(catalog)


def _active_plans(catalog: CatalogStore) -> List[Dict[str, Any]]:
    return catalog.list_plans(active_only=True)


def _plan_rank(plan: Dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(plan.get("price") or 0),
        int(plan.get("requests_per_month") or 0),
        int(plan.get("requests_per_5h") or 0),
    )


def highest_active_plan_id(catalog: CatalogStore) -> str:
    plans = _active_plans(catalog)
    if not plans:
        return ""
    top = max(plans, key=_plan_rank)
    return str(top.get("id") or "")


def default_active_plan_id(catalog: CatalogStore) -> str:
    for plan in _active_plans(catalog):
        if str(plan.get("id")) == "free":
            return str(plan["id"])
    plans = _active_plans(catalog)
    if not plans:
        return ""
    lowest = min(plans, key=_plan_rank)
    return str(lowest.get("id") or "")


def resolve_user_active_plan(
    catalog: CatalogStore,
    users: UserStore,
    username: str,
) -> Optional[Dict[str, Any]]:
    record = users.get_user_record(username)
    if record is None:
        return None
    if str(record.get("role") or "") == "admin":
        plan_id = highest_active_plan_id(catalog)
        if plan_id:
            return catalog.get_plan(plan_id)
    plan_id = str(record.get("active_plan_id") or "")
    if plan_id:
        plan = catalog.get_plan(plan_id)
        if plan is not None:
            return plan
    plans = _active_plans(catalog)
    return plans[0] if plans else None
