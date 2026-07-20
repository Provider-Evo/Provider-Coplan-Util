
from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = ["UserStore", "hash_password", "verify_password"]

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{2,32}$")
_PBKDF2_ROUNDS = 120_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ROUNDS,
    ).hex()
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds_text, salt, digest = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        check = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            rounds,
        ).hex()
        return secrets.compare_digest(check, digest)
    except Exception:
        return False


class UserStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "users.json"
        if not self._path.is_file():
            self._path.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _save(self, users: List[Dict[str, Any]]) -> None:
        self._path.write_text(
            json.dumps(users, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_users(self) -> List[Dict[str, Any]]:
        return [self._public_user(user) for user in self._load()]

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        for user in self._load():
            if user.get("username") == username:
                return self._public_user(user)
        return None

    def get_user_record(self, username: str) -> Optional[Dict[str, Any]]:
        for user in self._load():
            if user.get("username") == username:
                return user
        return None

    def _public_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "email": user.get("email") or "",
            "role": user.get("role") or "user",
            "status": user.get("status") or "active",
            "active_plan_id": user.get("active_plan_id") or "",
            "created_at": user.get("created_at"),
        }

    def create_user(
        self,
        username: str,
        password: str,
        *,
        email: str = "",
        role: str = "user",
        active_plan_id: str = "",
    ) -> Dict[str, Any]:
        name = username.strip()
        if not _USERNAME_RE.match(name):
            raise ValueError("用户名须为 2-32 位字母数字下划线")
        if len(password) < 6:
            raise ValueError("密码至少 6 位")
        users = self._load()
        if any(user.get("username") == name for user in users):
            raise ValueError("用户名已存在")
        entry = {
            "id": str(uuid.uuid4()),
            "username": name,
            "email": email.strip(),
            "password_hash": hash_password(password),
            "role": role,
            "status": "active",
            "active_plan_id": active_plan_id,
            "created_at": int(time.time()),
        }
        users.append(entry)
        self._save(users)
        return self._public_user(entry)

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        record = self.get_user_record(username.strip())
        if record is None:
            return None
        if record.get("status") != "active":
            return None
        if not verify_password(password, str(record.get("password_hash") or "")):
            return None
        return self._public_user(record)

    def change_password(self, username: str, current: str, new_password: str) -> None:
        if len(new_password) < 6:
            raise ValueError("新密码至少 6 位")
        users = self._load()
        for user in users:
            if user.get("username") != username:
                continue
            if not verify_password(current, str(user.get("password_hash") or "")):
                raise ValueError("当前密码错误")
            user["password_hash"] = hash_password(new_password)
            self._save(users)
            return
        raise KeyError(username)

    def set_active_plan(self, username: str, plan_id: str) -> Dict[str, Any]:
        users = self._load()
        for user in users:
            if user.get("username") != username:
                continue
            user["active_plan_id"] = plan_id
            self._save(users)
            return self._public_user(user)
        raise KeyError(username)

    def ensure_admin_user(
        self,
        username: str,
        password: str,
        *,
        active_plan_id: str,
    ) -> Dict[str, Any]:
        """确保 config 管理员在 users.json 中存在，并绑定最高套餐。"""
        name = username.strip()
        if not name:
            raise ValueError("管理员用户名不能为空")
        if not _USERNAME_RE.match(name):
            raise ValueError("管理员用户名须为 2-32 位字母数字下划线")
        users = self._load()
        for user in users:
            if user.get("username") != name:
                continue
            user["role"] = "admin"
            user["status"] = "active"
            user["active_plan_id"] = active_plan_id
            user["password_hash"] = hash_password(password)
            self._save(users)
            return self._public_user(user)
        entry = {
            "id": str(uuid.uuid4()),
            "username": name,
            "email": "",
            "password_hash": hash_password(password),
            "role": "admin",
            "status": "active",
            "active_plan_id": active_plan_id,
            "created_at": int(time.time()),
        }
        users.append(entry)
        self._save(users)
        return self._public_user(entry)
