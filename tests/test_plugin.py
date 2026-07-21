"""Provider-Coplan-Util smoke tests."""
from __future__ import annotations

from pathlib import Path


def test_manifest_exists() -> None:
    parent = Path(__file__).parent.parent
    manifest = parent / "_manifest.json"
    disabled = parent / "_manifest.json.disabled"
    assert manifest.is_file() or disabled.is_file()


def test_plugin_entry() -> None:
    plugin_py = Path(__file__).parent.parent / "plugin.py"
    text = plugin_py.read_text(encoding="utf-8")
    assert "def create_plugin" in text
