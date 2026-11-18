"""HAD-0004/HAD-0010: Anbindung an Home Assistant ueber die REST-API.

Alle Aktionen laufen ueber die REST-API mit einem dedizierten
Nicht-Admin-Token. Der Dienstname wird nie aus Nutzereingaben gebildet: Die
Entitaets-Domain wird auf einen festen Dienst abgebildet. Der Token erscheint
nie in einem Log oder in einer Antwort.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, cast

from command_parser import (
    ACTION_HELP,
    ACTION_OFF,
    ACTION_ON,
    ACTION_SET_VALUE,
    ACTION_STATUS,
    VALUE_SERVICES,
    Command,
    format_value,
)

SWITCH_DOMAIN = "switch"


@dataclass(frozen=True)
class ActionResult:
    attempted: bool
    ok: bool | None
    detail: str | None

    def as_dict(self) -> dict[str, Any]:
        return {"attempted": self.attempted, "ok": self.ok, "detail": self.detail}


def _request(request: urllib.request.Request, timeout: int) -> tuple[bool, str]:
    """Fuehrt eine Anfrage aus und gibt (ok, body-oder-fehlertext) zurueck.

    Fehlertexte enthalten bewusst weder URL noch Token.
    """
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return True, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"Verbindung fehlgeschlagen: {exc.reason}"
    except TimeoutError:
        return False, "Zeitueberschreitung"
    except OSError as exc:
        return False, f"Netzwerkfehler: {exc.strerror or exc}"


def _base(base_url: str) -> str:
    return base_url.rstrip("/")


def _post_service(
    base_url: str,
    token: str,
    domain: str,
    service: str,
    payload: dict[str, Any],
    timeout: int,
) -> tuple[bool, str | None]:
    """Ruft einen festen Dienst auf. Der Dienstname kommt nicht aus Eingaben."""
    url = f"{_base(base_url)}/api/services/{domain}/{service}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    ok, body = _request(request, timeout)
    if not ok:
        return False, body
    return True, None


def _state_summary(payload: dict[str, Any]) -> str:
    """Fasst Zustand und, falls vorhanden, Temperaturen zusammen."""
    state = payload.get("state")
    if not isinstance(state, str) or not state:
        return ""
    attributes = payload.get("attributes")
    if not isinstance(attributes, dict):
        return state
    attrs = cast(dict[str, Any], attributes)
    parts: list[str] = []
    current = attrs.get("current_temperature")
    target = attrs.get("temperature")
    if isinstance(current, (int, float)) and not isinstance(current, bool):
        parts.append(f"Ist {format_value(float(current))}")
    if isinstance(target, (int, float)) and not isinstance(target, bool):
        parts.append(f"Soll {format_value(float(target))}")
    if not parts:
        return state
    return f"{state} ({', '.join(parts)})"


def read_state(
    base_url: str, token: str, entity_id: str, timeout: int
) -> tuple[bool, str | None]:
    """Liest den Zustand einer Entitaet ueber die REST-API."""
    url = f"{_base(base_url)}/api/states/{entity_id}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    ok, body = _request(request, timeout)
    if not ok:
        return False, body

    if not body.strip():
        return False, "Leere Antwort"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False, "Antwort ist kein gueltiges JSON"
    if not isinstance(payload, dict):
        return False, "Antwort ist kein Objekt"

    summary = _state_summary(cast(dict[str, Any], payload))
    if not summary:
        return False, "Antwort enthaelt keinen Zustand"
    return True, summary


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


def _in_range(command: Command, value: float) -> bool:
    if command.min is not None and value < command.min:
        return False
    if command.max is not None and value > command.max:
        return False
    return True


def _perform_switch(
    command: Command, entity_id: str, base_url: str, token: str, timeout: int
) -> ActionResult:
    if _domain(entity_id) != SWITCH_DOMAIN:
        return ActionResult(
            attempted=False, ok=None, detail="Aktion nur fuer switch-Entitaeten"
        )
    service = "turn_on" if command.action == ACTION_ON else "turn_off"
    ok, detail = _post_service(
        base_url, token, SWITCH_DOMAIN, service, {"entity_id": entity_id}, timeout
    )
    return ActionResult(attempted=True, ok=ok, detail=detail)


def _perform_set_value(
    command: Command,
    value: float | None,
    entity_id: str,
    base_url: str,
    token: str,
    timeout: int,
) -> ActionResult:
    mapping = VALUE_SERVICES.get(_domain(entity_id))
    if mapping is None:
        return ActionResult(
            attempted=False,
            ok=None,
            detail="Werte nur fuer climate, number, input_number",
        )
    if value is None:
        return ActionResult(attempted=False, ok=None, detail="kein Wert erkannt")
    if not _in_range(command, value):
        return ActionResult(
            attempted=False, ok=None, detail="Wert ausserhalb des Bereichs"
        )
    domain, service, key = mapping
    ok, detail = _post_service(
        base_url, token, domain, service, {"entity_id": entity_id, key: value}, timeout
    )
    return ActionResult(attempted=True, ok=ok, detail=detail)


def perform_action(
    command: Command | None,
    value: float | None,
    base_url: str | None,
    token: str | None,
    timeout: int,
    enabled: bool,
) -> ActionResult:
    """Fuehrt die zum Kommando gehoerende Aktion aus.

    Es gibt keine dynamische Zuordnung: Die Aktion stammt aus der validierten
    Konfiguration, der Dienst aus einer festen Domain-Tabelle.
    """
    if command is None:
        return ActionResult(attempted=False, ok=None, detail="kein Kommando")
    if command.action == ACTION_HELP:
        return ActionResult(attempted=False, ok=None, detail="keine Aktion")
    if not enabled:
        return ActionResult(attempted=False, ok=None, detail="Anbindung deaktiviert")
    if not base_url or not token:
        return ActionResult(attempted=False, ok=None, detail="Anbindung nicht konfiguriert")

    entity_id = command.entity_id
    if not entity_id:
        return ActionResult(attempted=False, ok=None, detail="keine Entitaet konfiguriert")

    if command.action == ACTION_STATUS:
        ok, detail = read_state(base_url, token, entity_id, timeout)
        return ActionResult(attempted=True, ok=ok, detail=detail)
    if command.action in (ACTION_ON, ACTION_OFF):
        return _perform_switch(command, entity_id, base_url, token, timeout)
    if command.action == ACTION_SET_VALUE:
        return _perform_set_value(command, value, entity_id, base_url, token, timeout)
    return ActionResult(attempted=False, ok=None, detail="unbekannte Aktion")
