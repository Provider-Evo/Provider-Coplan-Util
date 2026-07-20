

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

__all__ = ["UsageStore"]


def _parse_json_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


class UsageStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "usage_counters.json"
        if not self._path.is_file():
            self._path.write_text("{}", encoding="utf-8")

    def _load(self) -> Dict[str, Any]:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def _save(self, data: Dict[str, Any]) -> None:
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _bucket(self, username: str) -> Dict[str, Any]:
        data = self._load()
        entry = data.setdefault(username, {})
        now = int(time.time())
        window_5h = int(entry.get("window_5h_start") or now)
        if now - window_5h >= 5 * 3600:
            entry["window_5h_start"] = now
            entry["requests_5h"] = 0
        month_key = time.strftime("%Y-%m", time.localtime(now))
        if entry.get("month_key") != month_key:
            entry["month_key"] = month_key
            entry["requests_month"] = 0
        entry.setdefault("requests_5h", 0)
        entry.setdefault("requests_month", 0)
        data[username] = entry
        self._save(data)
        return entry

    def assert_within_plan(self, username: str, plan: Optional[Mapping[str, Any]]) -> None:
        if not plan:
            return
        entry = self._bucket(username)
        limit_5h = int(plan.get("requests_per_5h") or 0)
        limit_month = int(plan.get("requests_per_month") or 0)
        if limit_5h > 0 and int(entry.get("requests_5h") or 0) >= limit_5h:
            raise PermissionError("已超出套餐每 5 小时请求配额")
        if limit_month > 0 and int(entry.get("requests_month") or 0) >= limit_month:
            raise PermissionError("已超出套餐每月请求配额")

    def record_request(self, username: str) -> None:
        entry = self._bucket(username)
        entry["requests_5h"] = int(entry.get("requests_5h") or 0) + 1
        entry["requests_month"] = int(entry.get("requests_month") or 0) + 1
        data = self._load()
        data[username] = entry
        self._save(data)

    def get_usage(self, username: str) -> Dict[str, int]:
        entry = self._bucket(username)
        return {
            "requests_5h": int(entry.get("requests_5h") or 0),
            "requests_month": int(entry.get("requests_month") or 0),
        }
