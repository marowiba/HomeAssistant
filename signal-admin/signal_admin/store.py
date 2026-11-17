# pyright: basic
"""HAD-0008: SQLite-Speicher fuer Benutzer, Sitzungen, Audit und Einstellungen."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    detail TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Store:
    """Duenne SQLite-Huelle. Oeffnet je Operation eine eigene Verbindung."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _db(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # Benutzer
    def create_user(self, username: str, password_hash: str, now: float | None = None) -> None:
        ts = int(now if now is not None else time.time())
        with self._db() as conn:
            conn.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES (?,?,?)",
                (username, password_hash, ts),
            )

    def get_user(self, username: str) -> dict[str, Any] | None:
        with self._db() as conn:
            row = conn.execute(
                "SELECT username, password_hash, created_at FROM users WHERE username=?",
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def list_users(self) -> list[dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT username, created_at FROM users ORDER BY username"
            ).fetchall()
        return [dict(row) for row in rows]

    def set_password(self, username: str, password_hash: str) -> None:
        with self._db() as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash=? WHERE username=?",
                (password_hash, username),
            )
        if cursor.rowcount == 0:
            raise KeyError(username)

    def delete_user(self, username: str) -> None:
        with self._db() as conn:
            conn.execute("DELETE FROM users WHERE username=?", (username,))

    # Sitzungen
    def create_session(
        self,
        token_hash: str,
        username: str,
        expires_at: int,
        now: float | None = None,
    ) -> None:
        ts = int(now if now is not None else time.time())
        with self._db() as conn:
            conn.execute(
                "INSERT INTO sessions(token_hash, username, created_at, expires_at)"
                " VALUES (?,?,?,?)",
                (token_hash, username, ts, int(expires_at)),
            )

    def get_session(self, token_hash: str, now: float | None = None) -> dict[str, Any] | None:
        ts = int(now if now is not None else time.time())
        with self._db() as conn:
            row = conn.execute(
                "SELECT token_hash, username, created_at, expires_at"
                " FROM sessions WHERE token_hash=?",
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        session = dict(row)
        if session["expires_at"] <= ts:
            self.delete_session(token_hash)
            return None
        return session

    def delete_session(self, token_hash: str) -> None:
        with self._db() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))

    def purge_expired_sessions(self, now: float | None = None) -> int:
        ts = int(now if now is not None else time.time())
        with self._db() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (ts,))
        return cursor.rowcount

    # Einstellungen
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._db() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._db() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES (?,?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    # Audit
    def last_audit_hash(self) -> str:
        with self._db() as conn:
            row = conn.execute(
                "SELECT entry_hash FROM audit ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return row["entry_hash"] if row else ""

    def append_audit(
        self,
        ts: int,
        actor: str,
        action: str,
        target: str,
        detail: str,
        prev_hash: str,
        entry_hash: str,
    ) -> int:
        with self._db() as conn:
            cursor = conn.execute(
                "INSERT INTO audit(ts, actor, action, target, detail, prev_hash, entry_hash)"
                " VALUES (?,?,?,?,?,?,?)",
                (int(ts), actor, action, target, detail, prev_hash, entry_hash),
            )
        return int(cursor.lastrowid or 0)

    def list_audit(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT id, ts, actor, action, target, detail, prev_hash, entry_hash"
                " FROM audit ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def all_audit_ascending(self) -> list[dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT id, ts, actor, action, target, detail, prev_hash, entry_hash"
                " FROM audit ORDER BY id ASC"
            ).fetchall()
        return [dict(row) for row in rows]
