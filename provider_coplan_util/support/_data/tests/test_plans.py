"""test_plans 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 test_plans 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

from pathlib import Path

import pytest

from provider_coplan_util.stores.catalog_store import CatalogStore
from provider_coplan_util.routing.plans import (
    default_active_plan_id,
    highest_active_plan_id,
    resolve_user_active_plan,
)
from provider_coplan_util.routing.config import DEFAULT_MODELS, DEFAULT_PLANS
from provider_coplan_util.stores.user_store import UserStore
from provider_coplan_util.routing.loader import load_strategy_groups
from provider_coplan_util.stores.store import StrategyStore
from provider_coplan_util.routing.strat_sbox import validate_and_extract_strategy_group
from provider_coplan_util.routing.user_strat import compile_strategy_source, spec_to_source_code


def test_highest_and_default_plan_ids(tmp_path: Path):
    catalog = CatalogStore(tmp_path)
    catalog.ensure_defaults(DEFAULT_PLANS, DEFAULT_MODELS)
    assert highest_active_plan_id(catalog) == "ultra"
    assert default_active_plan_id(catalog) == "free"


def test_admin_always_gets_highest_plan(tmp_path: Path):
    catalog = CatalogStore(tmp_path)
    catalog.ensure_defaults(DEFAULT_PLANS, DEFAULT_MODELS)
    users = UserStore(tmp_path)
    users.ensure_admin_user("admin", "changeme", active_plan_id="free")
    plan = resolve_user_active_plan(catalog, users, "admin")
    assert plan is not None
    assert plan["id"] == "ultra"


def test_ensure_admin_user_syncs_highest_plan(tmp_path: Path):
    catalog = CatalogStore(tmp_path)
    catalog.ensure_defaults(DEFAULT_PLANS, DEFAULT_MODELS)
    users = UserStore(tmp_path)
    admin = users.ensure_admin_user(
        "admin",
        "changeme",
        active_plan_id=highest_active_plan_id(catalog),
    )
    assert admin["role"] == "admin"
    assert admin["active_plan_id"] == "ultra"
    users.set_active_plan("admin", "free")
    admin = users.ensure_admin_user(
        "admin",
        "changeme",
        active_plan_id=highest_active_plan_id(catalog),
    )
    assert admin["active_plan_id"] == "ultra"


def test_load_builtin_default_strategy():
    plugin_dir = Path(__file__).resolve().parents[1]
    groups = load_strategy_groups(plugin_dir / "strategies")
    ids = {g["id"] for g in groups}
    assert "default" in ids


def test_sync_code_group_merges_legacy_default(tmp_path: Path):
    store = StrategyStore(tmp_path)
    legacy = store.create_group("default", "旧默认组")
    store.add_key(legacy["id"], label="keep-me")
    plugin_dir = Path(__file__).resolve().parents[1]
    definitions = load_strategy_groups(plugin_dir / "strategies")
    store.sync_code_groups(definitions)
    groups = store.list_groups()
    code_default = next(g for g in groups if g.get("id") == "default")
    assert code_default.get("source") == "code"
    assert len(code_default.get("keys") or []) == 1
    assert code_default["keys"][0]["label"] == "keep-me"


def test_literal_strategy_group_ok():
    source = '''
"""demo"""

STRATEGY_GROUP = {
    "id": "demo",
    "name": "Demo",
    "aliases": {
        "auto": {
            "strategy": "single",
            "routes": [{"platform": "deepseek", "model": "deepseek-chat"}],
        },
    },
}
'''
    raw = validate_and_extract_strategy_group(source)
    assert raw["id"] == "demo"
    spec = compile_strategy_source(source)
    assert spec["aliases"]["auto"]["strategy"] == "single"


def test_reject_import():
    source = 'import os\nSTRATEGY_GROUP = {"id": "x", "name": "x"}'
    with pytest.raises(ValueError, match="不允许"):
        validate_and_extract_strategy_group(source)


def test_reject_function_call():
    source = 'STRATEGY_GROUP = dict(id="x", name="x")'
    with pytest.raises(ValueError, match="不允许"):
        validate_and_extract_strategy_group(source)


def test_spec_roundtrip():
    spec = {
        "id": "round",
        "name": "Round",
        "aliases": {"auto": {"strategy": "single", "routes": [{"platform": "qwen", "model": "qwen-plus"}]}},
    }
    source = spec_to_source_code(spec)
    compiled = compile_strategy_source(source)
    assert compiled["id"] == "round"
