"""HAD-0004: Anbindung an Home Assistant.

Schaltbefehle laufen ueber Webhooks und brauchen keinen Token. Der Status wird
ueber die REST-API gelesen, weil Webhooks in Home Assistant keine Daten
zurueckgeben koennen. Dafuer ist ein dedizierter Nicht-Admin-Benutzer mit
Long-Lived-Token vorgesehen; der Token wird nur fuer einen GET auf genau eine
Entitaet verwendet und erscheint nie in einem Log.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, cast

STATUS_COMMAND = "status"


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


def call_webhook(url: str, timeout: int) -> tuple[bool, str | None]:
    """Loest einen Webhook per POST aus. Webhooks liefern keine Antwort."""
    request = urllib.request.Request(url, data=b"", method="POST")
    ok, body = _request(request, timeout)
    if not ok:
        return False, body
    return True, None


def read_state(url: str, token: str, timeout: int) -> tuple[bool, str | None]:
    """Liest den Zustand einer Entitaet ueber die REST-API."""
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

    state = cast(dict[str, Any], payload).get("state")
    if not isinstance(state, str) or not state:
        return False, "Antwort enthaelt keinen Zustand"
    return True, state


def perform_action(
    command: str | None,
    actions: dict[str, str],
    status_url: str | None,
    status_token: str | None,
    timeout: int,
    enabled: bool,
) -> ActionResult:
    """Fuehrt die zum Kommando gehoerende Aktion aus.

    Es gibt keine dynamische Zuordnung: `command` ist einer der drei festen
    Werte. Schaltbefehle gehen an je einen Webhook, der Status an einen GET.
    """
    if command is None:
        return ActionResult(attempted=False, ok=None, detail="kein Kommando")
    if command == "help":
        return ActionResult(attempted=False, ok=None, detail="keine Aktion")
    if not enabled:
        return ActionResult(attempted=False, ok=None, detail="Anbindung deaktiviert")

    if command == STATUS_COMMAND:
        if not status_url or not status_token:
            return ActionResult(
                attempted=False, ok=None, detail="Statusabfrage nicht konfiguriert"
            )
        ok, detail = read_state(status_url, status_token, timeout)
        return ActionResult(attempted=True, ok=ok, detail=detail)

    url = actions.get(command)
    if not url:
        return ActionResult(attempted=False, ok=None, detail=f"kein Webhook fuer {command}")

    ok, detail = call_webhook(url, timeout)
    return ActionResult(attempted=True, ok=ok, detail=detail)
