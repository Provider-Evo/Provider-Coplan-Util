"""Provider-Coplan-Util smoke tests."""
from __future__ import annotations


def test_manifest_exists() -> None:
    from pathlib import Path

    parent = Path(__file__).parent.parent
    manifest = parent / "_manifest.json"
    disabled = parent / "_manifest.json.disabled"
    assert manifest.is_file() or disabled.is_file()
