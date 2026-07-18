"""test_auth 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 test_auth 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

from provider_coplan_util.auth.access import assert_model_allowed, effective_allowed_models
from provider_coplan_util.auth import SessionStore, verify_admin_credentials
from provider_coplan_util.support.contracts import parse_strategy_model, strategy_public_id


def test_verify_admin_credentials() -> None:
    assert verify_admin_credentials("admin", "pass", "admin", "pass") is True
    assert verify_admin_credentials("admin", "wrong", "admin", "pass") is False
    assert verify_admin_credentials("other", "pass", "admin", "pass") is False


def test_session_store_issue_and_get() -> None:
    store = SessionStore(ttl_seconds=3600)
    token = store.issue("admin", role="admin")
    record = store.get(token)
    assert record is not None
    assert record.username == "admin"
    assert record.role == "admin"
    store.revoke(token)
    assert store.get(token) is None


def test_session_store_max_cap() -> None:
    store = SessionStore(ttl_seconds=3600, max_sessions=2)
    t1 = store.issue("u1")
    t2 = store.issue("u2")
    t3 = store.issue("u3")
    assert store.get(t1) is None
    assert store.get(t2) is not None
    assert store.get(t3) is not None


def test_strategy_public_id():
    assert strategy_public_id("my-routing") == "strategy/my-routing"


def test_parse_strategy_model():
    group, alias = parse_strategy_model("strategy/my-routing/auto")
    assert group == "my-routing"
    assert alias == "auto"


def test_plan_priority_over_key():
    plan = {"selected_models": '["qwen-plus"]'}
    key = {"allowed_models": ["qwen-max", "qwen-plus"]}
    allowed = effective_allowed_models(plan, key)
    assert allowed == {"qwen-plus"}


def test_assert_model_denied():
    plan = {"selected_models": '["qwen-plus"]'}
    key = {"allowed_models": []}
    try:
        assert_model_allowed(plan, key, "qwen-max")
        raised = False
    except PermissionError:
        raised = True
    assert raised
