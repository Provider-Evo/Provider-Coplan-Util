"""策略组持久化。"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from provider_coplan_util import generate_api_key
from provider_coplan_util.spec import empty_spec, normalize_group

__all__ = ["StrategyStore"]


def _public_group(group: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(group)
    payload.setdefault("keys", [])
    payload.setdefault("source", "runtime")
    payload.setdefault("owner", "")
    payload.setdefault("allowed_key_ids", [])
    payload.setdefault("source_code", "")
    payload.setdefault("spec", empty_spec(str(group.get("id") or ""), str(group.get("name") or "")))
    return payload


class StrategyStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._groups_path = self._dir / "strategy_groups.json"
        self._settings_path = self._dir / "settings.json"
        if not self._groups_path.is_file():
            self._groups_path.write_text("[]", encoding="utf-8")
        if not self._settings_path.is_file():
            self._settings_path.write_text("{}", encoding="utf-8")

    def list_groups(self, *, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        groups = json.loads(self._groups_path.read_text(encoding="utf-8"))
        rows = [_public_group(group) for group in groups]
        if owner is not None:
            rows = [
                group for group in rows
                if group.get("owner") == owner or group.get("source") == "code"
            ]
        return rows

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        for group in self.list_groups():
            if group.get("id") == group_id:
                return group
        return None

    def get_settings(self) -> Dict[str, Any]:
        try:
            data = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_settings(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_settings()
        current.update(patch)
        self._settings_path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return current

    def _load_raw(self) -> List[Dict[str, Any]]:
        return json.loads(self._groups_path.read_text(encoding="utf-8"))

    def _save(self, groups: List[Dict[str, Any]]) -> None:
        self._groups_path.write_text(
            json.dumps(groups, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def sync_code_groups(self, definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将 strategies/*.py 中的定义同步到存储（按 spec.id 合并，保留密钥）。"""
        groups = self._load_raw()
        by_id = {str(g.get("id")): g for g in groups}
        synced: List[Dict[str, Any]] = []

        for spec in definitions:
            group_id = spec["id"]
            existing = by_id.get(group_id)
            if existing is None:
                legacy_keys: List[Dict[str, Any]] = []
                legacy_match = [
                    g for g in groups
                    if g.get("source") != "code"
                    and (str(g.get("name")) == group_id or str(g.get("id")) == group_id)
                ]
                if legacy_match:
                    legacy = legacy_match[0]
                    legacy_keys = list(legacy.get("keys") or [])
                    groups = [g for g in groups if g is not legacy]
                    by_id = {str(g.get("id")): g for g in groups}
                entry = {
                    "id": group_id,
                    "name": spec.get("name") or group_id,
                    "description": spec.get("description") or "",
                    "spec": spec,
                    "source": "code",
                    "source_file": spec.get("source_file", ""),
                    "keys": legacy_keys,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
                groups.append(entry)
                by_id[group_id] = entry
                synced.append(entry)
                continue

            existing["name"] = spec.get("name") or existing.get("name") or group_id
            existing["description"] = spec.get("description") or existing.get("description") or ""
            existing["spec"] = spec
            existing["source"] = "code"
            existing["source_file"] = spec.get("source_file", "")
            existing["updated_at"] = int(time.time())
            synced.append(existing)

        self._save(groups)
        return [_public_group(group) for group in synced]

    def create_group(
        self,
        name: str,
        description: str = "",
        *,
        owner: str = "",
        source: str = "runtime",
        source_code: str = "",
        spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        groups = self._load_raw()
        group_id = str(uuid.uuid4())
        spec_data = spec if spec is not None else empty_spec(group_id, name)
        spec_data["description"] = description
        entry = {
            "id": group_id,
            "name": name,
            "description": description,
            "spec": spec_data,
            "source": source,
            "owner": owner,
            "source_code": source_code,
            "allowed_key_ids": [],
            "keys": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        groups.append(entry)
        self._save(groups)
        return _public_group(entry)

    def create_user_group(
        self,
        owner: str,
        name: str,
        description: str = "",
        *,
        source_code: str = "",
        spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if spec is not None:
            group_id = spec["id"]
            groups = self._load_raw()
            if any(str(g.get("spec", {}).get("id")) == group_id and g.get("owner") == owner for g in groups):
                raise ValueError(f"策略组 id 已存在: {group_id}")
            entry = {
                "id": str(uuid.uuid4()),
                "name": name or spec.get("name") or group_id,
                "description": description or spec.get("description") or "",
                "spec": spec,
                "source": "user_code",
                "owner": owner,
                "source_code": source_code,
                "allowed_key_ids": [],
                "keys": [],
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
            groups.append(entry)
            self._save(groups)
            return _public_group(entry)
        return self.create_group(
            name,
            description,
            owner=owner,
            source="user_code",
            source_code=source_code,
        )

    def update_spec(self, group_id: str, spec_raw: Dict[str, Any]) -> Dict[str, Any]:
        groups = self._load_raw()
        for group in groups:
            if group.get("id") != group_id:
                continue
            if group.get("source") == "code":
                raise PermissionError("代码定义的策略组不可通过 API 修改，请编辑 strategies/ 下模块")
            spec = normalize_group({**spec_raw, "id": group.get("spec", {}).get("id") or group_id})
            spec["id"] = str(group.get("spec", {}).get("id") or group_id)
            group["spec"] = spec
            group["name"] = spec.get("name") or group.get("name") or group_id
            group["description"] = spec.get("description") or group.get("description") or ""
            group["updated_at"] = int(time.time())
            self._save(groups)
            return _public_group(group)
        raise KeyError(group_id)

    def get_group_for_owner(self, group_row_id: str, owner: str) -> Optional[Dict[str, Any]]:
        for group in self.list_groups():
            if group.get("id") != group_row_id:
                continue
            if group.get("owner") == owner or group.get("source") == "code":
                return group
        return None

    def update_source_code(self, group_id: str, owner: str, source_code: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        return self.update_group_code(group_id, source_code, spec, owner=owner, admin=False)

    def update_group_code(
        self,
        group_id: str,
        source_code: str,
        spec: Dict[str, Any],
        *,
        owner: str = "",
        admin: bool = False,
    ) -> Dict[str, Any]:
        groups = self._load_raw()
        for group in groups:
            if group.get("id") != group_id:
                continue
            if group.get("source") == "code":
                raise PermissionError("系统内置策略组请编辑 strategies/ 下 Python 文件")
            if not admin and group.get("owner") != owner:
                raise PermissionError("无权修改此策略组")
            group["source_code"] = source_code
            group["spec"] = spec
            group["name"] = spec.get("name") or group.get("name") or spec["id"]
            group["description"] = spec.get("description") or group.get("description") or ""
            if group.get("source") in {"", "runtime"}:
                group["source"] = "runtime" if admin or not owner else "user_code"
            elif owner:
                group["source"] = "user_code"
            group["updated_at"] = int(time.time())
            self._save(groups)
            return _public_group(group)
        raise KeyError(group_id)

    def get_group_source_code(self, group: Dict[str, Any]) -> str:
        from provider_coplan_util.user_strategy import DEFAULT_USER_STRATEGY_TEMPLATE, spec_to_source_code

        stored = str(group.get("source_code") or "").strip()
        if stored:
            return stored
        spec = group.get("spec")
        if isinstance(spec, dict) and spec:
            return spec_to_source_code(spec)
        return DEFAULT_USER_STRATEGY_TEMPLATE

    def set_allowed_keys(self, group_id: str, owner: str, key_ids: List[str]) -> Dict[str, Any]:
        groups = self._load_raw()
        for group in groups:
            if group.get("id") != group_id:
                continue
            if group.get("owner") != owner:
                raise PermissionError("无权修改此策略组")
            group["allowed_key_ids"] = list(key_ids)
            group["updated_at"] = int(time.time())
            self._save(groups)
            return _public_group(group)
        raise KeyError(group_id)

    def delete_group(self, group_id: str, *, owner: Optional[str] = None) -> bool:
        groups = self._load_raw()
        target = next((g for g in groups if g.get("id") == group_id), None)
        if target is None:
            return False
        if owner is not None and target.get("owner") != owner:
            raise PermissionError("无权删除此策略组")
        if target.get("source") == "code":
            raise PermissionError("代码定义的策略组不可删除，请从 strategies/ 移除后重载插件")
        new_groups = [g for g in groups if g.get("id") != group_id]
        self._save(new_groups)
        return True

    def add_key(self, group_id: str, label: str = "") -> Dict[str, Any]:
        groups = self._load_raw()
        for group in groups:
            if group.get("id") != group_id:
                continue
            key_entry = {
                "id": str(uuid.uuid4()),
                "key": generate_api_key(),
                "label": label,
                "is_active": True,
                "created_at": int(time.time()),
            }
            group.setdefault("keys", []).append(key_entry)
            self._save(groups)
            return key_entry
        raise KeyError(group_id)

    def delete_key(self, group_id: str, key_id: str) -> bool:
        groups = self._load_raw()
        changed = False
        for group in groups:
            if group.get("id") != group_id:
                continue
            keys = group.get("keys", [])
            new_keys = [k for k in keys if k.get("id") != key_id]
            if len(new_keys) != len(keys):
                group["keys"] = new_keys
                changed = True
            break
        if changed:
            self._save(groups)
        return changed

    def revoke_key(self, key_id: str) -> bool:
        groups = self._load_raw()
        changed = False
        for group in groups:
            for key in group.get("keys", []):
                if key.get("id") == key_id:
                    key["is_active"] = False
                    changed = True
        if changed:
            self._save(groups)
        return changed

    def list_keys_flat(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for group in self.list_groups():
            for key in group.get("keys", []):
                rows.append({
                    **key,
                    "group_id": group.get("id"),
                    "group_name": group.get("name"),
                    "group_spec_id": (group.get("spec") or {}).get("id"),
                })
        return rows

    def key_count(self) -> int:
        return sum(len(g.get("keys", [])) for g in self.list_groups())

    def ensure_default_group(self) -> Dict[str, Any]:
        groups = self.list_groups()
        code_default = next((g for g in groups if g.get("source") == "code" and g.get("id") == "default"), None)
        if code_default is not None:
            return code_default
        runtime_default = next((g for g in groups if g.get("name") == "default"), None)
        if runtime_default is not None:
            return runtime_default
        if groups:
            return groups[0]
        return self.create_group("default", "默认策略组")
