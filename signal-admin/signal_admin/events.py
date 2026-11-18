# pyright: basic
"""HAD-0008: Event Log lesen, filtern und löschen."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

_SEARCH_FIELDS = (
    "text",
    "sender_name",
    "sender_number",
    "sender_uuid",
    "matched_label",
    "command",
    "reason",
)


def event_id(record: dict[str, Any]) -> str:
    canonical = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def read_events(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                record = dict(record)
                record["_id"] = event_id(record)
                events.append(record)
    return events


def _matches(
    event: dict[str, Any],
    needle: str,
    decision: str,
    command: str,
    date_from: str,
    date_to: str,
) -> bool:
    if decision and event.get("decision") != decision:
        return False
    if command and event.get("command") != command:
        return False
    timestamp = str(event.get("ts", ""))
    if date_from and timestamp[:10] < date_from:
        return False
    if date_to and timestamp[:10] > date_to:
        return False
    if needle:
        haystack = " ".join(str(event.get(field, "")) for field in _SEARCH_FIELDS)
        if needle not in haystack.lower():
            return False
    return True


def filter_events(
    events: list[dict[str, Any]],
    query: str = "",
    decision: str = "",
    command: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    return [
        event
        for event in events
        if _matches(event, needle, decision, command, date_from, date_to)
    ]


SORT_KEYS = ("ts", "sender", "text", "decision", "command")
SORT_DIRECTIONS = ("asc", "desc")
DEFAULT_SORT = "ts"
DEFAULT_DIRECTION = "desc"


def _sort_value(event: dict[str, Any], key: str) -> str:
    if key == "ts":
        received = event.get("received_ms")
        if isinstance(received, int) and not isinstance(received, bool):
            return f"{received:020d}"
        return str(event.get("ts", ""))
    if key == "sender":
        return str(
            event.get("sender_name") or event.get("sender_number") or ""
        ).casefold()
    return str(event.get(key) or "").casefold()


def sort_events(
    events: list[dict[str, Any]],
    sort_key: str = DEFAULT_SORT,
    direction: str = DEFAULT_DIRECTION,
) -> list[dict[str, Any]]:
    """Sortiert Ereignisse stabil nach einem erlaubten Schluessel.

    Unbekannte Schluessel und Richtungen fallen auf den Standard zurueck.
    """
    if sort_key not in SORT_KEYS:
        sort_key = DEFAULT_SORT
    if direction not in SORT_DIRECTIONS:
        direction = DEFAULT_DIRECTION
    return sorted(
        events,
        key=lambda event: (_sort_value(event, sort_key), str(event.get("_id", ""))),
        reverse=direction == "desc",
    )


def _atomic_write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def prune_events(
    path: str | Path, retention_days: int, now: float | None = None
) -> int:
    """Entfernt Ereignisse ausserhalb der Aufbewahrungsfrist."""
    path = Path(path)
    if not path.exists():
        return 0
    reference = now if now is not None else time.time()
    cutoff_ms = int((reference - retention_days * 86400) * 1000)
    kept: list[str] = []
    removed = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                kept.append(stripped)
                continue
            received = record.get("received_ms") if isinstance(record, dict) else None
            if (
                isinstance(received, int)
                and not isinstance(received, bool)
                and received < cutoff_ms
            ):
                removed += 1
                continue
            kept.append(stripped)
    _atomic_write_lines(path, kept)
    return removed


def delete_events(path: str | Path, ids: set[str]) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    kept: list[str] = []
    removed = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                kept.append(stripped)
                continue
            if isinstance(record, dict) and event_id(record) in ids:
                removed += 1
                continue
            kept.append(stripped)
    _atomic_write_lines(path, kept)
    return removed
