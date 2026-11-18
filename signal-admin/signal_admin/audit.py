# pyright: basic
"""HAD-0008: Manipulationsgeschütztes Audit Log mit Hash-Kette."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .store import Store


def _canonical(ts: int, actor: str, action: str, target: str, detail: str) -> str:
    return json.dumps(
        {
            "ts": int(ts),
            "actor": actor,
            "action": action,
            "target": target,
            "detail": detail,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _entry_hash(prev_hash: str, canonical: str) -> str:
    return hashlib.sha256((prev_hash + "|" + canonical).encode("utf-8")).hexdigest()


class AuditLog:
    """Schreibt Audit-Einträge mit prev_hash/entry_hash fort und prüft die Kette."""

    def __init__(self, store: Store):
        self.store = store

    def append(
        self,
        actor: str,
        action: str,
        target: str,
        detail: str = "",
        now: float | None = None,
    ) -> dict[str, Any]:
        ts = int(now if now is not None else time.time())
        prev_hash = self.store.last_audit_hash()
        canonical = _canonical(ts, actor, action, target, detail)
        entry_hash = _entry_hash(prev_hash, canonical)
        entry_id = self.store.append_audit(
            ts, actor, action, target, detail, prev_hash, entry_hash
        )
        return {
            "id": entry_id,
            "ts": ts,
            "actor": actor,
            "action": action,
            "target": target,
            "detail": detail,
            "prev_hash": prev_hash,
            "entry_hash": entry_hash,
        }

    def verify(self) -> tuple[bool, int | None]:
        """Prueft die Hash-Kette. Gibt (ok, erste fehlerhafte id) zurueck."""
        prev = ""
        for entry in self.store.all_audit_ascending():
            canonical = _canonical(
                entry["ts"],
                entry["actor"],
                entry["action"],
                entry["target"],
                entry["detail"],
            )
            expected = _entry_hash(prev, canonical)
            if entry["prev_hash"] != prev or entry["entry_hash"] != expected:
                return False, entry["id"]
            prev = entry["entry_hash"]
        return True, None

    def list(self, limit: int = 200) -> list[dict[str, Any]]:
        return self.store.list_audit(limit)
