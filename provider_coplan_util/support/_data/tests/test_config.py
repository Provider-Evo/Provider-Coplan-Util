"""test_config 模块 — Provider 适配器层。

职责：
    作为 Provider-Evo 项目标准模块，提供 test_config 能力。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""


from __future__ import annotations

from pathlib import Path

from provider_coplan_util.routing.config import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_HERO_TAGLINE,
    DEFAULT_STANDALONE_PORT,
    load_coplan_config,
)


def test_manifest_exists():
    """验证 manifest 文件存在（enabled 或 disabled）。"""
    parent = Path(__file__).parent.parent
    manifest = parent / "_manifest.json"
    disabled = parent / "_manifest.json.disabled"
    assert manifest.is_file() or disabled.is_file()


def test_plugin_entry():
    """验证插件入口模块可导入。"""
    import sys
    plugin_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(plugin_dir))
    import plugin
    assert hasattr(plugin, "create_plugin"), "create_plugin not found"


def test_load_default_when_missing(tmp_path: Path) -> None:
    cfg = load_coplan_config(tmp_path)
    assert cfg.hero_tagline == DEFAULT_HERO_TAGLINE
    assert cfg.standalone_enabled is True
    assert cfg.standalone_port == DEFAULT_STANDALONE_PORT
    assert cfg.standalone_access_log is False
    assert cfg.admin_username == DEFAULT_ADMIN_USERNAME
    assert cfg.admin_password == DEFAULT_ADMIN_PASSWORD


def test_load_custom_tagline(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        '[coplan]\nhero_tagline = "自定义标语"\n',
        encoding="utf-8",
    )
    cfg = load_coplan_config(tmp_path)
    assert cfg.hero_tagline == "自定义标语"


def test_load_server_and_admin(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        """
[coplan]
hero_tagline = "标语"

[server]
enabled = false
host = "0.0.0.0"
port = 9001
access_log = true

[admin]
username = "root"
password = "secret"
""".strip(),
        encoding="utf-8",
    )
    cfg = load_coplan_config(tmp_path)
    assert cfg.standalone_enabled is False
    assert cfg.standalone_host == "0.0.0.0"
    assert cfg.standalone_port == 9001
    assert cfg.standalone_access_log is True
    assert cfg.admin_username == "root"
    assert cfg.admin_password == "secret"


def test_duplicate_keys_fall_back_to_defaults(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        """
[coplan]
strategies_dir = "strategies"
strategies_dir = "dup"

[admin]
username = "root"
password = "secret"
""".strip(),
        encoding="utf-8",
    )
    cfg = load_coplan_config(tmp_path)
    assert cfg.admin_username == DEFAULT_ADMIN_USERNAME
    assert cfg.admin_password == DEFAULT_ADMIN_PASSWORD
