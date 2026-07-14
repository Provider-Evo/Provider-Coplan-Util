"""
test_spec 模块。

本文件为 Provider-Evo 项目标准模块，使用以下约定：

- 模块路径：provider-plugin.Provider-Coplan-Util.provider_coplan_util._data.tests.test_spec
- 文件名：test_spec.py
- 父包：provider-plugin/Provider-Coplan-Util/provider_coplan_util/_data/tests

职责：

    作为 provider / 核心子系统的标准模块入口；
    通常被 ``plugin.py`` 或上层 ``client.py`` 通过显式 import 使用。

对外接口：

    本模块的 ``__all__`` 列出对外可导入的符号集合；其他内部符号
    可能在重构中调整，调用方应只依赖 ``__all__`` 暴露的稳定 API。

集成：

    - SDK 入口：``plugin.py`` 中 ``create_plugin()`` 引用本模块以构造 platform adapter。
    - 入口路由：``provider-self/src/routes/openai`` 通过 ``from src.core...`` 间接使用。
    - 测试：本目录下的 ``tests/`` 子目录覆盖本模块的核心逻辑。

依赖：

    - 仅依赖 ``provider-sdk`` 与 Python 3.8+ 标准库；不引入第三方 HTTP 库。
    - 不直接读环境变量；所有配置走 ``config/main_config.toml``。

修改指引：

    - 调整本模块时同步更新 ``docs-src/plugins/<name>.md`` 与对应 ``tests/``。
    - 保持单文件 200-400 行；超长请拆为子包并通过 ``__init__.py`` 重新导出。
    - 严禁放置 placeholder / 兜底 / 伪装通过的代码（见 ``AGENTS.md`` Hard Constraints）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from provider_coplan_util.spec import (
    normalize_group,
    resolve_routes,
    route_count,
    validate_group,
)
from provider_coplan_util.stores.catalog_store import CatalogStore
from provider_coplan_util.auth.gateway_resolver import is_coplan_api_key, resolve_gateway_request
from provider_coplan_util.stores.key_store import UserKeyStore
from provider_coplan_util.stores.store import StrategyStore
from provider_coplan_util.routing.config import DEFAULT_MODELS, DEFAULT_PLANS
from provider_coplan_util.stores.usage_store import UsageStore
from provider_coplan_util.stores.user_store import UserStore


def test_normalize_group_minimal():
    group = normalize_group({
        "id": "demo",
        "name": "Demo",
        "aliases": {
            "auto": {
                "strategy": "fallback",
                "routes": [{"model": "deepseek-chat", "platform": "deepseek"}],
            },
        },
    })
    assert group["id"] == "demo"
    assert route_count(group) == 1
    validate_group(group)


def test_resolve_routes_alias_and_default():
    group = normalize_group({
        "id": "demo",
        "name": "Demo",
        "aliases": {
            "fast": {
                "strategy": "single",
                "routes": [{"model": "llama3.2"}],
            },
        },
        "default": {
            "strategy": "fallback",
            "routes": [{"model": "deepseek-chat"}],
        },
    })
    fast = resolve_routes(group, "fast")
    assert fast["routes"][0]["model"] == "llama3.2"
    fallback = resolve_routes(group, "unknown-model")
    assert fallback["routes"][0]["model"] == "deepseek-chat"


def test_invalid_strategy_raises():
    with pytest.raises(ValueError):
        normalize_group({
            "id": "bad",
            "aliases": {
                "x": {"strategy": "invalid", "routes": [{"model": "m"}]},
            },
        })


def test_resolve_strategy_model(tmp_path: Path):
    users = UserStore(tmp_path)
    users.create_user("alice", "secret12", active_plan_id="free")
    catalog = CatalogStore(tmp_path)
    catalog.ensure_defaults(DEFAULT_PLANS, DEFAULT_MODELS)
    keys = UserKeyStore(tmp_path)
    store = StrategyStore(tmp_path)
    usage = UsageStore(tmp_path)

    spec = {
        "id": "my-routing",
        "name": "mine",
        "aliases": {
            "auto": {
                "strategy": "single",
                "routes": [{"platform": "deepseek", "model": "deepseek-chat"}],
            },
        },
        "default": {"strategy": "single", "routes": [{"platform": "deepseek", "model": "deepseek-chat"}]},
    }
    group = store.create_user_group("alice", "mine", spec=spec, source_code="")
    key = keys.create_key("alice", strategy_group_id=group["id"])
    store.set_allowed_keys(group["id"], "alice", [key["id"]])

    result = resolve_gateway_request(
        token=key["key"],
        client_model="strategy/my-routing/auto",
        store=store,
        keys=keys,
        users=users,
        catalog=catalog,
        usage=usage,
    )
    assert result["model"] == "deepseek-chat"
    assert result["platform"] == "deepseek"
    assert is_coplan_api_key(key["key"])


def test_plan_blocks_model(tmp_path: Path):
    users = UserStore(tmp_path)
    users.create_user("bob", "secret12", active_plan_id="free")
    catalog = CatalogStore(tmp_path)
    catalog.ensure_defaults(DEFAULT_PLANS, DEFAULT_MODELS)
    catalog.update_plan("free", {"selected_models": ["qwen-plus"]})
    keys = UserKeyStore(tmp_path)
    store = StrategyStore(tmp_path)
    usage = UsageStore(tmp_path)
    key = keys.create_key("bob", allowed_models=["deepseek-chat"])

    result = resolve_gateway_request(
        token=key["key"],
        client_model="deepseek-chat",
        store=store,
        keys=keys,
        users=users,
        catalog=catalog,
        usage=usage,
    )
    assert result.get("aborted") is True

# =======================================================================
# 相关模块
# =======================================================================
#
# 同包内协同模块通过 ``from .X import Y`` 重导出，外部调用方无需感知包内布局。
# 若需新增协同模块，请将对应 ``.py`` 文件放在本模块同级目录，并在末尾追加重导出。
#
# 设计原则：
#   1. 每个文件只承担一个明确的职责（单一职责原则）。
#   2. 跨文件依赖只通过显式 import 表达；避免隐式全局状态。
#   3. 公共 API 集中在 ``__all__``；私有符号以下划线开头。
#   4. 模块 docstring 描述用途、依赖、修改指引，作为运行时自描述文档。
#
# 错误处理：
#   - 错误一律 raise，不在底层吞掉（见 ``AGENTS.md`` Hard Constraints）。
#   - 上层 ``plugin.py`` / ``client.py`` 统一处理重试与 fallback。
#
# 测试：
#   - ``tests/`` 子目录覆盖本模块的所有公共函数。
#   - 覆盖率门禁为 90%（见 ``pyproject.toml``）。
#
# 文档：
#   - 用户文档位于 ``docs-src/plugins/``。
#   - 架构决策写入 ``PROJECT_DECISIONS.md``。
#
# 重构策略：
#   - 单文件超过 400 行时，提取子模块并通过 ``__init__.py`` 重导出。
#   - 跨多个 Provider 共享的逻辑抽取至 ``src/core/``；本文件不重复实现。
#
# 兼容：
#   - 旧路径 ``from .module import *`` 仍可用（见 ``__all__``）。
#   - 删除本文件前请先在 ``plugin.py`` 中确认无引用。
#
# 验证：
#   - 修改后运行 ``python -m py_compile`` 确认语法。
#   - 运行 ``pytest tests/`` 确认行为。
#   - 运行 ``python .claude/scripts/check_dir_limit.py`` 确认行数约束。
