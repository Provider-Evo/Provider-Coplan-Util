"""test_store 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 test_store 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

import re
from pathlib import Path

from provider_coplan_util import KEY_BODY_LENGTH, KEY_PREFIX, KEY_TOTAL_LENGTH, generate_api_key
from provider_coplan_util.routing.config import load_coplan_config
from provider_coplan_util.routing.content import DEFAULT_FAQS, build_public_payload
from provider_coplan_util.stores.store import StrategyStore
from provider_coplan_util.stores.user_store import UserStore, verify_password, hash_password

_BODY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def test_create_group_and_key(tmp_path: Path):
    store = StrategyStore(tmp_path)
    group = store.create_group("default", "test")
    assert group["name"] == "default"
    key = store.add_key(group["id"], label="test")
    assert key["key"].startswith(KEY_PREFIX)
    assert len(key["key"]) == KEY_TOTAL_LENGTH
    groups = store.list_groups()
    assert len(groups) == 1
    assert len(groups[0]["keys"]) == 1
    flat = store.list_keys_flat()
    assert len(flat) == 1
    assert store.key_count() == 1
    assert store.delete_key(group["id"], key["id"]) is True
    assert store.key_count() == 0
    assert store.delete_group(group["id"]) is True
    assert store.list_groups() == []


def test_user_register_and_login(tmp_path: Path):
    store = UserStore(tmp_path)
    user = store.create_user("alice", "secret12", email="a@example.com", active_plan_id="free")
    assert user["username"] == "alice"
    authed = store.authenticate("alice", "secret12")
    assert authed is not None
    assert store.authenticate("alice", "wrong") is None
    store.change_password("alice", "secret12", "newpass9")
    assert store.authenticate("alice", "newpass9") is not None
    assert verify_password("newpass9", hash_password("newpass9"))


def test_public_payload_multi_platform(tmp_path) -> None:
    cfg = load_coplan_config(tmp_path)
    payload = build_public_payload(cfg, {}, [])
    assert "Ollama" in payload["platforms"]
    assert payload["faqs"]
    assert payload["faqs"][0]["q"] == DEFAULT_FAQS[0]["q"]
    assert payload["market_templates"] == []


def test_generate_api_key_format():
    key = generate_api_key()
    assert key.startswith(KEY_PREFIX)
    body = key[len(KEY_PREFIX) :]
    assert len(key) == KEY_TOTAL_LENGTH
    assert len(body) == KEY_BODY_LENGTH
    assert _BODY_RE.fullmatch(body)
    assert generate_api_key() != key
