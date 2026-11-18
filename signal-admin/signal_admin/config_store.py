# pyright: basic
"""HAD-0008: Bridge-Konfiguration lesen, validieren, schreiben, sichern."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

FIXED_COMMANDS = (
    {"id": "on", "text": "HO M an", "description": "Home Office einschalten"},
    {"id": "off", "text": "HO M aus", "description": "Home Office ausschalten"},
    {"id": "status", "text": "HO M Status", "description": "Status abfragen"},
)
FIXED_COMMAND_IDS = frozenset(command["id"] for command in FIXED_COMMANDS)
_ALLOWED_SCHEMES = frozenset({"http", "https"})


class ConfigError(Exception):
    """Ungueltige oder unvollstaendige Konfiguration."""


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.netloc)


def load_config(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Konfiguration nicht gefunden: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Konfiguration ist kein gueltiges JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Konfiguration muss ein JSON-Objekt sein")
    return data


def _validate_entry(item: Any, index: int) -> list[str]:
    if not isinstance(item, dict):
        return [f"allowlist[{index}] muss ein Objekt sein"]
    errors: list[str] = []
    label = item.get("label")
    if not isinstance(label, str) or not label.strip():
        errors.append(f"allowlist[{index}].label fehlt oder ist leer")
    number = item.get("number")
    uuid = item.get("uuid")
    if number is not None and not isinstance(number, str):
        errors.append(f"allowlist[{index}].number muss Text sein")
    if uuid is not None and not isinstance(uuid, str):
        errors.append(f"allowlist[{index}].uuid muss Text sein")
    if not number and not uuid:
        errors.append(f"allowlist[{index}] braucht number oder uuid")
    enabled = item.get("enabled", True)
    if not isinstance(enabled, bool):
        errors.append(f"allowlist[{index}].enabled muss true oder false sein")
    return errors


def _validate_actions(section: dict[str, Any], enabled: bool) -> list[str]:
    actions = section.get("actions", {})
    if not isinstance(actions, dict):
        return ["home_assistant.actions muss ein Objekt sein"]
    errors: list[str] = []
    for key in ("on", "off"):
        value = actions.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not _is_http_url(value):
            errors.append(f"home_assistant.actions.{key} muss eine http(s)-URL sein")
    if enabled:
        missing = [key for key in ("on", "off") if key not in actions]
        if missing:
            errors.append("home_assistant.actions fehlen: " + ", ".join(missing))
    return errors


def _validate_status(section: dict[str, Any]) -> list[str]:
    status = section.get("status")
    if status is None:
        return []
    if not isinstance(status, dict):
        return ["home_assistant.status muss ein Objekt sein"]
    errors: list[str] = []
    url = status.get("url")
    token = status.get("token")
    if not isinstance(url, str) or not _is_http_url(url):
        errors.append("home_assistant.status.url muss eine http(s)-URL sein")
    if not isinstance(token, str) or not token:
        errors.append("home_assistant.status.token fehlt")
    return errors


def _validate_home_assistant(section: Any) -> list[str]:
    if not isinstance(section, dict):
        return ["home_assistant muss ein Objekt sein"]
    errors: list[str] = []
    enabled = section.get("enabled", False)
    if not isinstance(enabled, bool):
        errors.append("home_assistant.enabled muss true oder false sein")
    errors.extend(_validate_actions(section, enabled))
    errors.extend(_validate_status(section))
    return errors


def _validate_signal(section: Any) -> list[str]:
    if not isinstance(section, dict):
        return ["signal muss ein Objekt sein"]
    errors: list[str] = []
    enabled = section.get("enabled", True)
    if not isinstance(enabled, bool):
        errors.append("signal.enabled muss true oder false sein")
    rpc_url = section.get("rpc_url")
    if rpc_url is not None and (
        not isinstance(rpc_url, str) or not _is_http_url(rpc_url)
    ):
        errors.append("signal.rpc_url muss eine http(s)-URL sein")
    return errors


def _validate_allowlist(data: dict[str, Any]) -> list[str]:
    allowlist = data.get("allowlist", [])
    if not isinstance(allowlist, list):
        return ["allowlist muss eine Liste sein"]
    errors: list[str] = []
    for index, item in enumerate(allowlist):
        errors.extend(_validate_entry(item, index))
    return errors


def _validate_retention(data: dict[str, Any]) -> list[str]:
    retention = data.get("retention_days", 30)
    if not isinstance(retention, int) or isinstance(retention, bool) or retention <= 0:
        return ["retention_days muss eine positive Ganzzahl sein"]
    return []


def _validate_commands(data: dict[str, Any]) -> list[str]:
    commands = data.get("commands")
    if commands is None:
        return []
    if not isinstance(commands, dict):
        return ["commands muss ein Objekt sein"]
    errors: list[str] = []
    for key, value in commands.items():
        if key not in FIXED_COMMAND_IDS:
            errors.append(f"commands.{key} ist kein festes Kommando")
        elif not isinstance(value, bool):
            errors.append(f"commands.{key} muss true oder false sein")
    return errors


def validate_config(data: Any) -> list[str]:
    """Prueft die verwalteten Felder und gibt eine Liste von Fehlern zurueck."""
    if not isinstance(data, dict):
        return ["Konfiguration muss ein JSON-Objekt sein"]
    errors: list[str] = []
    errors.extend(_validate_allowlist(data))
    errors.extend(_validate_retention(data))
    errors.extend(_validate_commands(data))
    home_assistant = data.get("home_assistant")
    if home_assistant is not None:
        errors.extend(_validate_home_assistant(home_assistant))
    signal = data.get("signal")
    if signal is not None:
        errors.extend(_validate_signal(signal))
    return errors


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
        os.chmod(path, 0o640)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def save_config(path: str | Path, data: dict[str, Any]) -> None:
    errors = validate_config(data)
    if errors:
        raise ConfigError("; ".join(errors))
    _atomic_write(Path(path), json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def backup_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def restore_config(path: str | Path, raw: bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Backup ist kein gueltiges JSON: {exc}") from exc
    errors = validate_config(data)
    if errors:
        raise ConfigError("; ".join(errors))
    save_config(path, data)
    return data


def _copy(data: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(data))


def _ensure_valid(data: dict[str, Any]) -> None:
    errors = validate_config(data)
    if errors:
        raise ConfigError("; ".join(errors))


def add_allowlist_entry(
    data: dict[str, Any],
    label: str,
    number: str | None,
    uuid: str | None,
    enabled: bool = True,
) -> dict[str, Any]:
    result = _copy(data)
    entry: dict[str, Any] = {"label": label, "enabled": enabled}
    if number:
        entry["number"] = number
    if uuid:
        entry["uuid"] = uuid
    allowlist = result.setdefault("allowlist", [])
    if not isinstance(allowlist, list):
        raise ConfigError("allowlist muss eine Liste sein")
    allowlist.append(entry)
    _ensure_valid(result)
    return result


def update_allowlist_entry(
    data: dict[str, Any],
    index: int,
    label: str,
    number: str | None,
    uuid: str | None,
    enabled: bool,
) -> dict[str, Any]:
    result = _copy(data)
    allowlist = result.get("allowlist", [])
    if not isinstance(allowlist, list) or index < 0 or index >= len(allowlist):
        raise ConfigError("Allowlist-Eintrag nicht gefunden")
    entry: dict[str, Any] = {"label": label, "enabled": enabled}
    if number:
        entry["number"] = number
    if uuid:
        entry["uuid"] = uuid
    allowlist[index] = entry
    _ensure_valid(result)
    return result


def delete_allowlist_entry(data: dict[str, Any], index: int) -> dict[str, Any]:
    result = _copy(data)
    allowlist = result.get("allowlist", [])
    if not isinstance(allowlist, list) or index < 0 or index >= len(allowlist):
        raise ConfigError("Allowlist-Eintrag nicht gefunden")
    del allowlist[index]
    _ensure_valid(result)
    return result


def set_command_enabled(
    data: dict[str, Any], command_id: str, enabled: bool
) -> dict[str, Any]:
    if command_id not in FIXED_COMMAND_IDS:
        raise ConfigError(f"Unbekanntes Kommando: {command_id}")
    result = _copy(data)
    commands = result.setdefault("commands", {})
    if not isinstance(commands, dict):
        raise ConfigError("commands muss ein Objekt sein")
    commands[command_id] = bool(enabled)
    _ensure_valid(result)
    return result


def command_enabled(data: dict[str, Any], command_id: str) -> bool:
    commands = data.get("commands", {})
    if isinstance(commands, dict):
        return bool(commands.get(command_id, True))
    return True


def set_retention(data: dict[str, Any], days: int) -> dict[str, Any]:
    result = _copy(data)
    result["retention_days"] = days
    _ensure_valid(result)
    return result
