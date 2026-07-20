

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional

__all__ = ["SessionStore", "verify_admin_credentials"]

DEFAULT_MAX_SESSIONS = 1000


@dataclass
class SessionRecord:
    username: str
    role: str
    expires_at: float


class SessionStore:
    def __init__(
        self,
        ttl_seconds: int = 86400,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max(1, max_sessions)
        self._sessions: Dict[str, SessionRecord] = {}

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [
            token
            for token, record in self._sessions.items()
            if record.expires_at < now
        ]
        for token in expired:
            self._sessions.pop(token, None)

    def _enforce_cap(self) -> None:
        overflow = len(self._sessions) - self._max
        if overflow <= 0:
            return
        victims = sorted(
            self._sessions.items(),
            key=lambda item: item[1].expires_at,
        )[:overflow]
        for token, _ in victims:
            self._sessions.pop(token, None)

    def issue(self, username: str, role: str = "admin") -> str:
        self._purge_expired()
        token = "ent-" + secrets.token_urlsafe(24)
        self._sessions[token] = SessionRecord(
            username=username,
            role=role,
            expires_at=time.time() + self._ttl,
        )
        self._enforce_cap()
        return token

    def get(self, token: str) -> Optional[SessionRecord]:
        if not token:
            return None
        self._purge_expired()
        record = self._sessions.get(token)
        if record is None:
            return None
        if record.expires_at < time.time():
            self._sessions.pop(token, None)
            return None
        return record

    def revoke(self, token: str) -> None:
        self._sessions.pop(token, None)


def verify_admin_credentials(username: str, password: str, expected_user: str, expected_pass: str) -> bool:
    user_ok = secrets.compare_digest(username.strip(), expected_user.strip())
    pass_ok = secrets.compare_digest(password, expected_pass)
    return user_ok and pass_ok
