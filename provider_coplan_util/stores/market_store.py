

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from provider_coplan_util.support.contracts import alias_count, route_count

__all__ = ["StrategyMarketStore"]


class StrategyMarketStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "strategy_market.json"
        if not self._path.is_file():
            self._path.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _save(self, entries: List[Dict[str, Any]]) -> None:
        self._path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _public_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        spec = entry.get("spec") or {}
        return {
            **entry,
            "alias_count": alias_count(spec),
            "route_count": route_count(spec),
            "has_source_code": bool(str(entry.get("source_code") or "").strip()),
        }

    def list_entries(self) -> List[Dict[str, Any]]:
        entries = sorted(self._load(), key=lambda item: item.get("published_at", 0), reverse=True)
        return [self._public_entry(entry) for entry in entries]

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        for entry in self._load():
            if str(entry.get("id")) == str(entry_id):
                return self._public_entry(entry)
        return None

    def publish(
        self,
        *,
        spec: Dict[str, Any],
        title: str,
        description: str = "",
        author: str = "",
        source_group_id: str = "",
        source_code: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("title required")
        if not isinstance(spec, dict) or not spec:
            raise ValueError("spec required")
        entries = self._load()
        entry = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description.strip(),
            "author": author.strip() or "anonymous",
            "spec": spec,
            "source_code": source_code.strip(),
            "source_group_id": source_group_id,
            "tags": [str(tag).strip() for tag in (tags or []) if str(tag).strip()],
            "fork_count": 0,
            "published_at": int(time.time()),
        }
        entries.append(entry)
        self._save(entries)
        return self._public_entry(entry)

    def increment_fork(self, entry_id: str) -> Optional[Dict[str, Any]]:
        entries = self._load()
        for entry in entries:
            if str(entry.get("id")) != str(entry_id):
                continue
            entry["fork_count"] = int(entry.get("fork_count") or 0) + 1
            self._save(entries)
            return self._public_entry(entry)
        return None

    def delete_entry(self, entry_id: str) -> bool:
        entries = self._load()
        new_entries = [entry for entry in entries if str(entry.get("id")) != str(entry_id)]
        if len(new_entries) == len(entries):
            return False
        self._save(new_entries)
        return True
