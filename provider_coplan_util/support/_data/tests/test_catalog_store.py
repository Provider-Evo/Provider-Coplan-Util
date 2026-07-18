"""test_catalog_store 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 test_catalog_store 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

from pathlib import Path

from provider_coplan_util.stores.catalog_store import CatalogStore
from provider_coplan_util.routing.config import DEFAULT_MODELS, DEFAULT_PLANS
from provider_coplan_util.stores.market_store import StrategyMarketStore


def test_catalog_seed_and_crud(tmp_path: Path):
    store = CatalogStore(tmp_path)
    store.ensure_defaults(DEFAULT_PLANS, DEFAULT_MODELS)
    plans = store.list_plans()
    assert len(plans) == 3
    models = store.list_models()
    assert len(models) == 3

    plan = store.create_plan({
        "name": "Team",
        "price": 199,
        "requests_per_5h": 500,
        "requests_per_month": 20000,
        "features": ["团队席位"],
        "selected_models": ["qwen-plus"],
    })
    assert plan["name"] == "Team"
    updated = store.update_plan(plan["id"], {"price": 189})
    assert updated["price"] == 189
    assert store.delete_plan(plan["id"]) is True

    model = store.add_model({
        "model_id": "deepseek-chat",
        "display_name": "DeepSeek Chat",
        "description": "test",
        "sort_order": 5,
    })
    assert model["model_id"] == "deepseek-chat"
    assert store.toggle_model("deepseek-chat", False) is True
    assert store.delete_model("deepseek-chat") is True


def test_market_publish_fork_delete(tmp_path: Path):
    store = StrategyMarketStore(tmp_path)
    spec = {
        "id": "demo",
        "name": "demo",
        "aliases": {
            "fast": {
                "strategy": "single",
                "routes": [{"platform": "qwen", "model": "qwen-plus"}],
            },
        },
    }
    entry = store.publish(
        spec=spec,
        title="Demo Routing",
        description="shared demo",
        author="tester",
        source_group_id="group-1",
        tags=["demo"],
    )
    assert entry["title"] == "Demo Routing"
    assert entry["alias_count"] == 1
    assert entry["route_count"] == 1

    entries = store.list_entries()
    assert len(entries) == 1

    forked = store.increment_fork(entry["id"])
    assert forked is not None
    assert forked["fork_count"] == 1

    assert store.delete_entry(entry["id"]) is True
    assert store.list_entries() == []
