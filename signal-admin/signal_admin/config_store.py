# pyright: basic
"""HAD-0008/HAD-0010: Bridge-Konfiguration lesen, validieren, schreiben, sichern."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ACTIONS = ("on", "off", "status", "set_value", "help")
ENTITY_ACTIONS = ("on", "off", "status", "set_value")
VALUE_PLACEHOLDER = "{wert}"
VALUE_DOMAINS = ("climate", "number", "input_number")
SWITCH_DOMAIN = "switch"
ENTITY_RE = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")

# Standard-Kommandos fuer die Migration alter Konfigurationen.
DEFAULT_COMMANDS = (
    ("on", "HO M an", "on"),
    ("off", "HO M aus", "off"),
    ("status", "HO M Status", "status"),
    ("help", "Hilfe", "help"),
    ("help_q", "?", "help"),
)

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_STATE_MARKER = "/api/states/"


class ConfigError(Exception):
    """Ungueltige oder unvollstaendige Konfiguration."""


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.netloc)


def _copy(data: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(data))


def _entity_from_state_url(url: Any) -> str | None:
    if not isinstance(url, str) or _STATE_MARKER not in url:
        return None
    entity = url.split(_STATE_MARKER, 1)[1].strip("/")
    return entity or None


def _base_from_state_url(url: Any) -> str | None:
    if not isinstance(url, str) or _STATE_MARKER not in url:
        return None
    base = url.split(_STATE_MARKER, 1)[0]
    return base or None


def _migrate_commands(
    commands: dict[str, Any], entity_id: str | None
) -> list[dict[str, Any]]:
    migrated: list[dict[str, Any]] = []
    for command_id, text, action in DEFAULT_COMMANDS:
        if action in ENTITY_ACTIONS and not entity_id:
            continue
        item: dict[str, Any] = {
            "id": command_id,
            "text": text,
            "action": action,
            "enabled": bool(commands.get(command_id, True)),
        }
        if action in ENTITY_ACTIONS:
            item["entity_id"] = entity_id
        migrated.append(item)
    return migrated


def _migrate_home_assistant(ha: dict[str, Any], status_obj: dict[str, Any]) -> None:
    if "base_url" in ha:
        return
    base_url = _base_from_state_url(status_obj.get("url"))
    if base_url:
        ha["base_url"] = base_url
    if status_obj.get("token") and "token" not in ha:
        ha["token"] = status_obj["token"]
    ha.pop("actions", None)
    ha.pop("status", None)


def migrate_config(data: dict[str, Any]) -> dict[str, Any]:
    """Wandelt das alte Format (commands als Objekt, Webhooks) ins neue."""
    result = _copy(data)
    ha = result.get("home_assistant")
    ha_obj = ha if isinstance(ha, dict) else {}
    status = ha_obj.get("status")
    status_obj = status if isinstance(status, dict) else {}
    entity_id = _entity_from_state_url(status_obj.get("url"))

    commands = result.get("commands")
    if isinstance(commands, dict):
        result["commands"] = _migrate_commands(commands, entity_id)

    if isinstance(ha, dict):
        _migrate_home_assistant(ha, status_obj)
    return result


def load_config(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Konfiguration nicht gefunden: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Konfiguration ist kein gueltiges JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Konfiguration muss ein JSON-Objekt sein")
    return migrate_config(data)


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


def _validate_command_identity(item: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    command_id = item.get("id")
    if not isinstance(command_id, str) or not command_id.strip():
        errors.append(f"commands[{index}].id fehlt")
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        errors.append(f"commands[{index}].text fehlt")
    enabled = item.get("enabled", True)
    if not isinstance(enabled, bool):
        errors.append(f"commands[{index}].enabled muss true oder false sein")
    return errors


def _validate_command_entity(
    item: dict[str, Any], index: int, action: str
) -> list[str]:
    errors: list[str] = []
    entity_id = item.get("entity_id")
    if entity_id is not None and not isinstance(entity_id, str):
        errors.append(f"commands[{index}].entity_id muss Text sein")
    if action not in ENTITY_ACTIONS:
        return errors
    if not entity_id:
        errors.append(f"commands[{index}].entity_id fehlt")
        return errors
    if not isinstance(entity_id, str):
        return errors
    if not ENTITY_RE.match(entity_id):
        errors.append(f"commands[{index}].entity_id ist ungueltig")
        return errors
    domain = entity_id.split(".", 1)[0]
    if action in ("on", "off") and domain != SWITCH_DOMAIN:
        errors.append(f"commands[{index}]: on/off nur fuer switch-Entitaeten")
    if action == "set_value" and domain not in VALUE_DOMAINS:
        errors.append(
            f"commands[{index}]: set_value nur fuer climate, number, input_number"
        )
    return errors


def _validate_command_text(
    item: dict[str, Any], index: int, action: str
) -> list[str]:
    text = item.get("text")
    if not isinstance(text, str):
        return []
    if action == "set_value":
        if text.count(VALUE_PLACEHOLDER) != 1:
            return [f"commands[{index}].text braucht genau ein {VALUE_PLACEHOLDER}"]
        if not text.rstrip().endswith(VALUE_PLACEHOLDER):
            return [f"commands[{index}].text muss mit {VALUE_PLACEHOLDER} enden"]
        return []
    if VALUE_PLACEHOLDER in text:
        return [
            f"commands[{index}].text darf {VALUE_PLACEHOLDER} nur bei set_value enthalten"
        ]
    return []


def _validate_command_range(item: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    min_value = item.get("min")
    max_value = item.get("max")
    min_ok = isinstance(min_value, (int, float)) and not isinstance(min_value, bool)
    max_ok = isinstance(max_value, (int, float)) and not isinstance(max_value, bool)
    if not min_ok:
        errors.append(f"commands[{index}].min fehlt")
    if not max_ok:
        errors.append(f"commands[{index}].max fehlt")
    if (
        isinstance(min_value, (int, float))
        and not isinstance(min_value, bool)
        and isinstance(max_value, (int, float))
        and not isinstance(max_value, bool)
        and float(min_value) >= float(max_value)
    ):
        errors.append(f"commands[{index}].min muss kleiner als max sein")
    unit = item.get("unit")
    if unit is not None and not isinstance(unit, str):
        errors.append(f"commands[{index}].unit muss Text sein")
    return errors


def _validate_command(item: Any, index: int) -> list[str]:
    if not isinstance(item, dict):
        return [f"commands[{index}] muss ein Objekt sein"]
    errors = _validate_command_identity(item, index)
    action = item.get("action")
    if action not in ACTIONS:
        errors.append(f"commands[{index}].action ist ungueltig")
        return errors
    errors.extend(_validate_command_entity(item, index, action))
    errors.extend(_validate_command_text(item, index, action))
    if action == "set_value":
        errors.extend(_validate_command_range(item, index))
    return errors


def _validate_commands(data: dict[str, Any]) -> list[str]:
    commands = data.get("commands")
    if commands is None:
        return []
    if not isinstance(commands, list):
        return ["commands muss eine Liste sein"]
    errors: list[str] = []
    ids: set[str] = set()
    texts: set[str] = set()
    for index, item in enumerate(commands):
        errors.extend(_validate_command(item, index))
        if not isinstance(item, dict):
            continue
        command_id = item.get("id")
        if isinstance(command_id, str):
            if command_id in ids:
                errors.append(f"commands[{index}].id ist doppelt")
            ids.add(command_id)
        text = item.get("text")
        if isinstance(text, str):
            key = " ".join(text.split()).casefold()
            if key in texts:
                errors.append(f"commands[{index}].text ist doppelt")
            texts.add(key)
    return errors


def _validate_home_assistant(section: Any) -> list[str]:
    if not isinstance(section, dict):
        return ["home_assistant muss ein Objekt sein"]
    errors: list[str] = []
    enabled = section.get("enabled", False)
    if not isinstance(enabled, bool):
        errors.append("home_assistant.enabled muss true oder false sein")
    base_url = section.get("base_url")
    if base_url is not None and (
        not isinstance(base_url, str) or not _is_http_url(base_url)
    ):
        errors.append("home_assistant.base_url muss eine http(s)-URL sein")
    token = section.get("token")
    if token is not None and not isinstance(token, str):
        errors.append("home_assistant.token muss Text sein")
    if enabled and (not base_url or not token):
        errors.append("home_assistant.base_url und token fehlen")
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
    if not isinstance(data, dict):
        raise ConfigError("Backup muss ein JSON-Objekt sein")
    data = migrate_config(data)
    errors = validate_config(data)
    if errors:
        raise ConfigError("; ".join(errors))
    save_config(path, data)
    return data


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


def _find_command(data: dict[str, Any], command_id: str) -> int | None:
    commands = data.get("commands")
    if not isinstance(commands, list):
        return None
    for index, item in enumerate(commands):
        if isinstance(item, dict) and item.get("id") == command_id:
            return index
    return None


def _command_item(
    command_id: str,
    text: str,
    action: str,
    entity_id: str | None,
    min_value: float | None,
    max_value: float | None,
    unit: str | None,
    enabled: bool,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": command_id,
        "text": text,
        "action": action,
        "enabled": enabled,
    }
    if entity_id:
        item["entity_id"] = entity_id
    if action == "set_value":
        item["min"] = min_value
        item["max"] = max_value
        if unit:
            item["unit"] = unit
    return item


def add_command(
    data: dict[str, Any],
    text: str,
    action: str,
    entity_id: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    unit: str | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    result = _copy(data)
    commands = result.setdefault("commands", [])
    if not isinstance(commands, list):
        raise ConfigError("commands muss eine Liste sein")
    command_id = "cmd_" + secrets.token_hex(4)
    commands.append(
        _command_item(
            command_id, text, action, entity_id, min_value, max_value, unit, enabled
        )
    )
    _ensure_valid(result)
    return result


def update_command(
    data: dict[str, Any],
    command_id: str,
    text: str,
    action: str,
    entity_id: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    unit: str | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    result = _copy(data)
    index = _find_command(result, command_id)
    if index is None:
        raise ConfigError(f"Kommando nicht gefunden: {command_id}")
    commands = result["commands"]
    commands[index] = _command_item(
        command_id, text, action, entity_id, min_value, max_value, unit, enabled
    )
    _ensure_valid(result)
    return result


def delete_command(data: dict[str, Any], command_id: str) -> dict[str, Any]:
    result = _copy(data)
    index = _find_command(result, command_id)
    if index is None:
        raise ConfigError(f"Kommando nicht gefunden: {command_id}")
    del result["commands"][index]
    _ensure_valid(result)
    return result


def set_command_enabled(
    data: dict[str, Any], command_id: str, enabled: bool
) -> dict[str, Any]:
    result = _copy(data)
    index = _find_command(result, command_id)
    if index is None:
        raise ConfigError(f"Kommando nicht gefunden: {command_id}")
    result["commands"][index]["enabled"] = bool(enabled)
    _ensure_valid(result)
    return result


def command_enabled(data: dict[str, Any], command_id: str) -> bool:
    index = _find_command(data, command_id)
    if index is None:
        return True
    item = data["commands"][index]
    return bool(item.get("enabled", True))


def set_retention(data: dict[str, Any], days: int) -> dict[str, Any]:
    result = _copy(data)
    result["retention_days"] = days
    _ensure_valid(result)
    return result
