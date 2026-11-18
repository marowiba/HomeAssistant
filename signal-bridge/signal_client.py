"""HAD-0005: Antworten ueber den signal-cli-Daemon senden.

Die Bridge sendet ausschliesslich Antworten auf erkannte Kommandos
freigegebener Absender. Der Sendepfad laeuft ueber die JSON-RPC-Schnittstelle
des laufenden Daemons; ein zweiter signal-cli-Prozess wuerde am Lock scheitern.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, cast

from command_parser import build_help_text

DEFAULT_RPC_URL = "http://127.0.0.1:8080/api/v1/rpc"

REPLY_ON = "Home Office ist eingeschaltet."
REPLY_OFF = "Home Office ist ausgeschaltet."


@dataclass(frozen=True)
class ReplyResult:
    attempted: bool
    ok: bool | None
    detail: str | None

    def as_dict(self) -> dict[str, Any]:
        return {"attempted": self.attempted, "ok": self.ok, "detail": self.detail}


def _friendly_error(detail: str | None) -> str:
    """Uebersetzt einen technischen Fehlertext in eine verstaendliche Meldung."""
    if not detail:
        return "Die Aktion ist fehlgeschlagen."
    if detail.startswith(("HTTP 401", "HTTP 403")):
        return "Home Assistant hat den Zugriff abgelehnt."
    if detail.startswith("HTTP 404"):
        return "Die Aktion ist in Home Assistant nicht vorhanden."
    if detail.startswith("Verbindung fehlgeschlagen"):
        return "Home Assistant ist nicht erreichbar."
    if detail == "Zeitueberschreitung":
        return "Home Assistant antwortet nicht."
    if detail == "Statusabfrage nicht konfiguriert":
        return "Die Statusabfrage ist nicht eingerichtet."
    if detail == "Anbindung deaktiviert":
        return "Die Home-Assistant-Anbindung ist deaktiviert."
    return f"Die Aktion ist fehlgeschlagen ({detail})."


def build_reply(command: str | None, action: Any) -> str | None:
    """Erzeugt die Antwort auf ein Kommando. None bedeutet: nicht antworten."""
    if command is None or not isinstance(action, dict):
        return None

    action_obj = cast(dict[str, Any], action)

    if command == "help":
        return build_help_text()

    if not action_obj.get("attempted"):
        return f"Fehler: {_friendly_error(action_obj.get('detail'))}"

    if not action_obj.get("ok"):
        return f"Fehler: {_friendly_error(action_obj.get('detail'))}"

    if command == "status":
        state = action_obj.get("detail")
        if state == "on":
            return REPLY_ON
        if state == "off":
            return REPLY_OFF
        if isinstance(state, str) and state:
            return f"Home Office hat den Zustand: {state}."
        return "Fehler: Der Schalterzustand ist unbekannt."

    if command == "on":
        return REPLY_ON
    if command == "off":
        return REPLY_OFF
    return None


def _build_send_request(
    rpc_url: str,
    recipient: str,
    text: str,
) -> urllib.request.Request:
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "send",
        "params": {"recipient": [recipient], "message": text},
    }
    data = json.dumps(payload).encode("utf-8")
    return urllib.request.Request(
        rpc_url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )


def _post(request: urllib.request.Request, timeout: int) -> tuple[str | None, str | None]:
    """Fuehrt die Anfrage aus. Gibt (body, fehler) zurueck."""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return None, f"Verbindung fehlgeschlagen: {exc.reason}"
    except TimeoutError:
        return None, "Zeitueberschreitung"
    except OSError as exc:
        return None, f"Netzwerkfehler: {exc.strerror or exc}"


def _check_delivery_results(result: Any) -> str | None:
    """Prueft die Zustellergebnisse. Gibt einen Fehlertext oder None zurueck."""
    if not isinstance(result, dict):
        return None
    results = cast(dict[str, Any], result).get("results")
    if not isinstance(results, list):
        return None
    for item in cast(list[Any], results):
        if not isinstance(item, dict):
            continue
        kind = cast(dict[str, Any], item).get("type")
        if kind not in (None, "SUCCESS"):
            return f"Zustellung: {kind}"
    return None


def _parse_send_response(body: str) -> tuple[bool, str | None]:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return False, "Antwort ist kein gueltiges JSON"
    if not isinstance(parsed, dict):
        return False, "Antwort ist kein Objekt"

    parsed_obj = cast(dict[str, Any], parsed)
    if parsed_obj.get("error"):
        return False, "JSON-RPC-Fehler"

    delivery_error = _check_delivery_results(parsed_obj.get("result"))
    if delivery_error is not None:
        return False, delivery_error
    return True, None


def send_message(
    rpc_url: str,
    recipient: str,
    text: str,
    timeout: int,
) -> tuple[bool, str | None]:
    """Sendet eine Nachricht ueber JSON-RPC. Gibt (ok, detail) zurueck."""
    request = _build_send_request(rpc_url, recipient, text)
    body, error = _post(request, timeout)
    if error is not None:
        return False, error
    return _parse_send_response(body or "")


def send_reply(
    command: str | None,
    action: Any,
    recipient: str | None,
    rpc_url: str,
    timeout: int,
    enabled: bool,
) -> ReplyResult:
    """Sendet die Antwort, wenn es etwas zu antworten gibt."""
    if not enabled:
        return ReplyResult(attempted=False, ok=None, detail="Antworten deaktiviert")

    text = build_reply(command, action)
    if text is None:
        return ReplyResult(attempted=False, ok=None, detail="keine Antwort vorgesehen")

    if not recipient:
        return ReplyResult(attempted=False, ok=None, detail="kein Empfaenger bekannt")

    ok, detail = send_message(rpc_url, recipient, text, timeout)
    return ReplyResult(attempted=True, ok=ok, detail=detail)
