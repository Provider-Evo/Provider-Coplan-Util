

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from provider_coplan_util import generate_api_key


class UserKeyStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "api_keys.json"
        if not self._path.is_file():
            self._path.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _save(self, keys: List[Dict[str, Any]]) -> None:
        self._path.write_text(
            json.dumps(keys, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_keys(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        keys = self._load()
        if username:
            keys = [key for key in keys if key.get("user") == username]
        return [dict(key) for key in keys]

    def get_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        for key in self._load():
            if key.get("id") == key_id:
                return dict(key)
        return None

    def find_by_secret(self, secret: str) -> Optional[Dict[str, Any]]:
        for key in self._load():
            if key.get("key") == secret and key.get("is_active", True):
                return dict(key)
        return None

    def create_key(
        self,
        username: str,
        *,
        label: str = "",
        strategy_group_id: str = "",
        allowed_group_ids: Optional[List[str]] = None,
        allowed_models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "id": str(uuid.uuid4()),
            "user": username,
            "key": generate_api_key(),
            "label": label,
            "strategy_group_id": strategy_group_id,
            "allowed_group_ids": list(allowed_group_ids or []),
            "allowed_models": list(allowed_models or []),
            "is_active": True,
            "created_at": int(time.time()),
        }
        keys = self._load()
        keys.append(entry)
        self._save(keys)
        return dict(entry)

    def update_key(self, key_id: str, username: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        keys = self._load()
        for key in keys:
            if key.get("id") != key_id or key.get("user") != username:
                continue
            if "label" in patch:
                key["label"] = str(patch.get("label") or "")
            if "strategy_group_id" in patch:
                key["strategy_group_id"] = str(patch.get("strategy_group_id") or "")
            if "allowed_group_ids" in patch:
                value = patch.get("allowed_group_ids")
                key["allowed_group_ids"] = list(value) if isinstance(value, list) else []
            if "allowed_models" in patch:
                value = patch.get("allowed_models")
                key["allowed_models"] = [str(item) for item in value] if isinstance(value, list) else []
            if "is_active" in patch:
                key["is_active"] = bool(patch.get("is_active"))
            self._save(keys)
            return dict(key)
        raise KeyError(key_id)

    def revoke_key(self, key_id: str, username: str) -> bool:
        keys = self._load()
        changed = False
        for key in keys:
            if key.get("id") == key_id and key.get("user") == username:
                key["is_active"] = False
                changed = True
        if changed:
            self._save(keys)
        return changed

    def delete_key(self, key_id: str, username: str) -> bool:
        keys = self._load()
        new_keys = [
            key for key in keys
            if not (key.get("id") == key_id and key.get("user") == username)
        ]
        if len(new_keys) == len(keys):
            return False
        self._save(new_keys)
        return True

    def key_count(self, username: Optional[str] = None) -> int:
        return len(self.list_keys(username))
