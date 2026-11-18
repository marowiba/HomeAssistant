# pyright: basic
"""HAD-0008: Status von Dienst, Signal und Home Assistant."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import Any, Callable


def _http_error_detail(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"Verbindung fehlgeschlagen: {exc.reason}"
    if isinstance(exc, TimeoutError):
        return "Zeitüberschreitung"
    if isinstance(exc, OSError):
        return f"Netzwerkfehler: {exc.strerror or exc}"
    return "Unbekannter Fehler"


def _fetch(request: urllib.request.Request, timeout: int) -> tuple[str | None, str | None]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace"), None
    except OSError as exc:
        return None, _http_error_detail(exc)


def check_signal(rpc_url: str, timeout: int = 5) -> dict[str, Any]:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "version"}).encode("utf-8")
    request = urllib.request.Request(
        rpc_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    body, error = _fetch(request, timeout)
    if error is not None:
        return {"ok": False, "detail": error}
    try:
        parsed = json.loads(body or "")
    except json.JSONDecodeError:
        return {"ok": False, "detail": "Antwort ist kein gültiges JSON"}
    if isinstance(parsed, dict) and "error" in parsed:
        return {"ok": False, "detail": "JSON-RPC-Fehler"}
    return {"ok": True, "detail": "erreichbar"}


def check_home_assistant(
    base_url: str | None, token: str | None, timeout: int = 5
) -> dict[str, Any]:
    """Prüft die Home-Assistant-API über ``/api/``.

    Die Startseite von Home Assistant liefert HTML. Der Endpunkt ``/api/``
    antwortet mit JSON und prueft zugleich den Token.
    """
    if not base_url or not token:
        return {"ok": False, "detail": "nicht konfiguriert"}
    url = base_url.rstrip("/") + "/api/"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    body, error = _fetch(request, timeout)
    if error is not None:
        return {"ok": False, "detail": error}
    try:
        parsed = json.loads(body or "")
    except json.JSONDecodeError:
        return {"ok": False, "detail": "Antwort ist kein gültiges JSON"}
    if not isinstance(parsed, dict):
        return {"ok": False, "detail": "Antwort ist kein Objekt"}
    if parsed.get("message") != "API running.":
        return {"ok": False, "detail": "unerwartete Antwort"}
    return {"ok": True, "detail": "erreichbar"}


def check_service(
    unit: str, runner: Callable[..., Any] | None = None
) -> dict[str, Any]:
    run = runner or subprocess.run
    try:
        result = run(
            ["systemctl", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "detail": f"Prüfung fehlgeschlagen: {exc}"}
    state = (result.stdout or "").strip() or "unbekannt"
    return {"ok": state == "active", "detail": state}


def recent_errors(
    events: list[dict[str, Any]], limit: int = 10
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for event in events:
        action = event.get("action")
        reply = event.get("reply")
        action_failed = (
            isinstance(action, dict)
            and action.get("attempted")
            and not action.get("ok")
        )
        reply_failed = (
            isinstance(reply, dict)
            and reply.get("attempted")
            and not reply.get("ok")
        )
        if action_failed or reply_failed:
            errors.append(event)
    return errors[-limit:][::-1]
