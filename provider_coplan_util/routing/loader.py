

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

from provider_coplan_util.support.contracts import normalize_group

__all__ = ["load_strategy_groups"]


def _load_module(path: Path) -> Any:
    module_name = f"coplan_strategy_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载策略模块: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_strategy_groups(strategies_dir: Path) -> List[Dict[str, Any]]:
    """扫描 strategies_dir 下 *.py，读取 STRATEGY_GROUPS 列表。"""
    if not strategies_dir.is_dir():
        return []

    groups: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(strategies_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module = _load_module(path)
        raw_groups = getattr(module, "STRATEGY_GROUPS", None)
        if raw_groups is None:
            continue
        if not isinstance(raw_groups, list):
            raise ValueError(f"{path.name}: STRATEGY_GROUPS 必须为 list")
        for index, item in enumerate(raw_groups):
            try:
                normalized = normalize_group(item)
            except ValueError as exc:
                raise ValueError(f"{path.name}[{index}]: {exc}") from exc
            group_id = normalized["id"]
            if group_id in seen_ids:
                raise ValueError(f"策略组 id 重复: {group_id!r} ({path.name})")
            seen_ids.add(group_id)
            normalized["source_file"] = path.name
            groups.append(normalized)
    return groups
