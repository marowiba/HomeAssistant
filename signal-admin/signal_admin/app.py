# pyright: basic
"""HAD-0008: HTTP-Anwendung der Signal-Administration."""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import socketserver
import sys
import time
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import auth, config_store, events as events_mod, status as status_mod, templates
from .audit import AuditLog
from .store import Store

SESSION_COOKIE = "signal_admin_session"
PAGE_SIZE = 25
COMMAND_SORT_KEYS = ("text", "entity")
AUDIT_SORT_KEYS = ("id", "ts", "actor", "action", "target", "detail", "hash")
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self'; script-src 'self'; "
        "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'"
    ),
}
LOGIN_PATH = "/login"
DASHBOARD_PATH = "/dashboard"
ALLOWLIST_PATH = "/allowlist"
COMMANDS_PATH = "/commands"
NOT_FOUND_MESSAGE = "Seite nicht gefunden"
DEFAULT_RPC_URL = "http" + "://127.0.0.1:8080/api/v1/rpc"
LOG = logging.getLogger("signal-admin")


@dataclass
class Response:
    status: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)


def _html(status: int, text: str) -> Response:
    return Response(
        status, text.encode("utf-8"), {"Content-Type": "text/html; charset=utf-8"}
    )


def _redirect(location: str, extra: dict[str, str] | None = None) -> Response:
    headers = {"Location": location}
    if extra:
        headers.update(extra)
    return Response(303, b"", headers)


def _error_text(exc: Exception) -> str:
    if isinstance(exc, OSError):
        return "Die Konfiguration konnte nicht gespeichert werden (Schreibfehler)."
    return str(exc)


def _float_field(form: dict[str, list[str]], key: str) -> float | None:
    values = form.get(key)
    raw = (values[0] if values else "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _sort_commands(
    commands: list[dict[str, Any]], sort_key: str, direction: str
) -> list[dict[str, Any]]:
    if sort_key not in COMMAND_SORT_KEYS:
        return commands
    field = "text" if sort_key == "text" else "entity_id"
    return sorted(
        commands,
        key=lambda item: str(item.get(field) or "").casefold(),
        reverse=direction == "desc",
    )


def _sort_audit(
    entries: list[dict[str, Any]], sort_key: str, direction: str
) -> list[dict[str, Any]]:
    key = sort_key if sort_key in AUDIT_SORT_KEYS else "ts"

    def value(entry: dict[str, Any]) -> Any:
        if key in ("id", "ts"):
            return int(entry.get(key) or 0)
        if key == "hash":
            return str(entry.get("entry_hash") or "")
        return str(entry.get(key) or "").casefold()

    return sorted(entries, key=value, reverse=direction == "desc")


class AdminApp:
    """Testbare Anwendung: handle() nimmt Methode, Pfad, Header und Body."""

    def __init__(
        self,
        config_path: str | Path,
        log_path: str | Path,
        db_path: str | Path,
        secret: str,
        *,
        service_unit: str = "signal-bridge.service",
        signal_rpc_url: str | None = None,
        ha_status_url: str | None = None,
        ha_status_token: str | None = None,
        now: Any = None,
    ):
        self.config_path = Path(config_path)
        self.log_path = Path(log_path)
        self.secret = secret
        self.service_unit = service_unit
        self.signal_rpc_url = signal_rpc_url
        self.ha_status_url = ha_status_url
        self.ha_status_token = ha_status_token
        self.store = Store(db_path)
        self.audit = AuditLog(self.store)
        self.rate_limiter = auth.LoginRateLimiter()
        self._now = now or time.time

    # --- Hilfen ---
    def _now_ts(self) -> float:
        return float(self._now())

    @staticmethod
    def _first(form: dict[str, list[str]], key: str, default: str = "") -> str:
        values = form.get(key)
        return values[0] if values else default

    def _load_config(self) -> dict[str, Any]:
        return config_store.load_config(self.config_path)

    def _session(self, headers: dict[str, str]) -> tuple[str | None, dict[str, Any] | None]:
        cookie = SimpleCookie()
        try:
            cookie.load(headers.get("Cookie", ""))
        except Exception:
            return None, None
        morsel = cookie.get(SESSION_COOKIE)
        if morsel is None:
            return None, None
        token = morsel.value
        session = self.store.get_session(auth.hash_token(token), now=self._now_ts())
        if session is None:
            return None, None
        return token, session

    def _csrf(self, token: str) -> str:
        return auth.csrf_token(token, self.secret)

    @staticmethod
    def _client_key(headers: dict[str, str]) -> str:
        forwarded = headers.get("X-Forwarded-For", "").split(",")[0].strip()
        return forwarded or headers.get("X-Real-IP", "") or "local"

    @staticmethod
    def _parse_form(headers: dict[str, str], body: bytes) -> dict[str, list[str]]:
        return parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)

    # --- Einstieg ---
    def handle(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes = b"",
    ) -> Response:
        parsed = urlparse(path)
        route = parsed.path
        query = parse_qs(parsed.query)
        if route.startswith("/static/"):
            return self._static(route)
        if route == LOGIN_PATH:
            if method == "GET":
                return _html(200, templates.login_page())
            if method == "POST":
                return self._login(headers, body)
            return _html(405, templates.error_page("Methode nicht erlaubt"))
        token, session = self._session(headers)
        if session is None:
            if method == "GET":
                return _redirect(LOGIN_PATH)
            return _html(403, templates.error_page("Nicht angemeldet"))
        assert token is not None
        user = session["username"]
        csrf = self._csrf(token)
        form: dict[str, list[str]] = {}
        if method == "POST":
            form = self._parse_form(headers, body)
            if not auth.verify_csrf(token, self.secret, self._first(form, "csrf")):
                return _html(
                    403, templates.error_page("Ungültiges CSRF-Token", user, csrf)
                )
        return self._route(method, route, query, form, user, csrf, token)

    def _route(
        self,
        method: str,
        route: str,
        query: dict[str, list[str]],
        form: dict[str, list[str]],
        user: str,
        csrf: str,
        token: str,
    ) -> Response:
        if method == "GET":
            return self._route_get(route, query, user, csrf)
        if method == "POST":
            return self._route_post(route, form, user, csrf, token)
        return _html(404, templates.error_page(NOT_FOUND_MESSAGE, user, csrf))

    def _route_get(
        self,
        route: str,
        query: dict[str, list[str]],
        user: str,
        csrf: str,
    ) -> Response:
        if route == "/":
            return _redirect(DASHBOARD_PATH)
        if route == DASHBOARD_PATH:
            return self._dashboard(user, csrf)
        if route == ALLOWLIST_PATH:
            return self._allowlist(user, csrf)
        if route == COMMANDS_PATH:
            return self._commands(user, csrf, query=query)
        if route == "/events":
            return self._events(query, user, csrf)
        if route == "/events/detail":
            return self._event_detail(query, user, csrf)
        if route == "/audit":
            return self._audit(user, csrf, query=query)
        if route == "/status":
            return self._status(user, csrf)
        if route == "/settings":
            return self._settings(user, csrf)
        if route == "/backup":
            return self._backup()
        return _html(404, templates.error_page(NOT_FOUND_MESSAGE, user, csrf))

    def _route_post(
        self,
        route: str,
        form: dict[str, list[str]],
        user: str,
        csrf: str,
        token: str,
    ) -> Response:
        if route == ALLOWLIST_PATH + "/add":
            return self._allowlist_add(form, user, csrf)
        if route == ALLOWLIST_PATH + "/update":
            return self._allowlist_update(form, user, csrf)
        if route == ALLOWLIST_PATH + "/delete":
            return self._allowlist_delete(form, user, csrf)
        if route == COMMANDS_PATH + "/add":
            return self._commands_add(form, user, csrf)
        if route == COMMANDS_PATH + "/update":
            return self._commands_update(form, user, csrf)
        if route == COMMANDS_PATH + "/delete":
            return self._commands_delete(form, user, csrf)
        if route == COMMANDS_PATH + "/toggle":
            return self._commands_toggle(form, user, csrf)
        if route == "/events/delete":
            return self._events_delete(form, user, csrf)
        if route == "/settings/retention":
            return self._settings_retention(form, user, csrf)
        if route == "/settings/cleanup":
            return self._settings_cleanup(user, csrf)
        if route == "/restore":
            return self._restore(form, user, csrf)
        if route == "/logout":
            return self._logout(token)
        return _html(404, templates.error_page(NOT_FOUND_MESSAGE, user, csrf))

    # --- Anmeldung ---
    def _login(self, headers: dict[str, str], body: bytes) -> Response:
        form = self._parse_form(headers, body)
        username = self._first(form, "username").strip()
        password = self._first(form, "password")
        key = self._client_key(headers)
        if self.rate_limiter.is_blocked(key, now=self._now_ts()):
            return _html(
                429,
                templates.login_page(
                    "Zu viele Fehlversuche. Bitte später erneut versuchen.", username
                ),
            )
        user = self.store.get_user(username)
        if user is None or not auth.verify_password(password, user["password_hash"]):
            self.rate_limiter.record_failure(key, now=self._now_ts())
            return _html(
                401,
                templates.login_page("Benutzername oder Passwort falsch.", username),
            )
        self.rate_limiter.reset(key)
        token = auth.new_session_token()
        expires = int(self._now_ts()) + auth.SESSION_TTL_SECONDS
        self.store.create_session(
            auth.hash_token(token), username, expires, now=self._now_ts()
        )
        self.audit.append(username, "login", "session", now=self._now_ts())
        cookie = f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/"
        return _redirect(DASHBOARD_PATH, {"Set-Cookie": cookie})

    def _logout(self, token: str) -> Response:
        self.store.delete_session(auth.hash_token(token))
        cookie = f"{SESSION_COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"
        return _redirect(LOGIN_PATH, {"Set-Cookie": cookie})

    # --- Dashboard / Status ---
    def _statuses(self, config: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        signal_section = config.get("signal")
        signal_cfg = signal_section if isinstance(signal_section, dict) else {}
        rpc_url = (
            self.signal_rpc_url or signal_cfg.get("rpc_url") or DEFAULT_RPC_URL
        )
        ha_section = config.get("home_assistant")
        ha = ha_section if isinstance(ha_section, dict) else {}
        ha_url = self.ha_status_url or ha.get("base_url")
        ha_token = self.ha_status_token or ha.get("token")
        return [
            ("signal-bridge", status_mod.check_service(self.service_unit)),
            ("signal-cli", status_mod.check_signal(rpc_url)),
            ("Home Assistant", status_mod.check_home_assistant(ha_url, ha_token)),
        ]

    def _dashboard(self, user: str, csrf: str) -> Response:
        config = self._load_config()
        all_events = events_mod.read_events(self.log_path)
        stats = [
            ("Allow-List-Einträge", len(config.get("allowlist", []))),
            ("Ereignisse", len(all_events)),
            (
                "Blockiert",
                sum(1 for event in all_events if event.get("decision") == "blocked"),
            ),
            ("Aufbewahrung (Tage)", config.get("retention_days", 30)),
        ]
        recent = all_events[-10:][::-1]
        return _html(
            200,
            templates.dashboard_page(stats, self._statuses(config), recent, user, csrf),
        )

    # --- Allowlist ---
    def _allowlist(
        self,
        user: str,
        csrf: str,
        flash: str | None = None,
        error: bool = False,
    ) -> Response:
        config = self._load_config()
        entries = config.get("allowlist", [])
        if not isinstance(entries, list):
            entries = []
        return _html(
            200, templates.allowlist_page(entries, user, csrf, flash, error)
        )

    def _allowlist_add(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        try:
            config = self._load_config()
            updated = config_store.add_allowlist_entry(
                config,
                self._first(form, "label").strip(),
                self._first(form, "number").strip() or None,
                self._first(form, "uuid").strip() or None,
                self._first(form, "enabled") == "1",
            )
            config_store.save_config(self.config_path, updated)
        except (OSError, config_store.ConfigError) as exc:
            return self._allowlist(user, csrf, _error_text(exc), True)
        self.audit.append(
            user, "allowlist.add", self._first(form, "label"), now=self._now_ts()
        )
        return _redirect(ALLOWLIST_PATH)

    def _allowlist_update(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        try:
            index = int(self._first(form, "index"))
            config = self._load_config()
            updated = config_store.update_allowlist_entry(
                config,
                index,
                self._first(form, "label").strip(),
                self._first(form, "number").strip() or None,
                self._first(form, "uuid").strip() or None,
                self._first(form, "enabled") == "1",
            )
            config_store.save_config(self.config_path, updated)
        except (ValueError, OSError, config_store.ConfigError) as exc:
            return self._allowlist(user, csrf, _error_text(exc), True)
        self.audit.append(user, "allowlist.update", str(index), now=self._now_ts())
        return _redirect(ALLOWLIST_PATH)

    def _allowlist_delete(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        try:
            index = int(self._first(form, "index"))
            config = self._load_config()
            updated = config_store.delete_allowlist_entry(config, index)
            config_store.save_config(self.config_path, updated)
        except (ValueError, OSError, config_store.ConfigError) as exc:
            return self._allowlist(user, csrf, _error_text(exc), True)
        self.audit.append(user, "allowlist.delete", str(index), now=self._now_ts())
        return _redirect(ALLOWLIST_PATH)

    # --- Kommandos ---
    def _commands(
        self,
        user: str,
        csrf: str,
        flash: str | None = None,
        error: bool = False,
        query: dict[str, list[str]] | None = None,
    ) -> Response:
        config = self._load_config()
        commands = config.get("commands", [])
        if not isinstance(commands, list):
            commands = []
        query = query or {}
        sort_key = self._first(query, "sort")
        if sort_key not in COMMAND_SORT_KEYS:
            sort_key = ""
        direction = self._first(query, "dir", "asc")
        if direction not in ("asc", "desc"):
            direction = "asc"
        commands = _sort_commands(commands, sort_key, direction)
        return _html(
            200,
            templates.commands_page(
                commands, user, csrf, flash, error, sort_key, direction
            ),
        )

    def _command_form_args(self, form: dict[str, list[str]]) -> tuple[Any, ...]:
        return (
            self._first(form, "text").strip(),
            self._first(form, "action"),
            self._first(form, "entity_id").strip() or None,
            _float_field(form, "min"),
            _float_field(form, "max"),
            self._first(form, "unit").strip() or None,
            self._first(form, "enabled") == "1",
        )

    def _commands_add(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        try:
            config = self._load_config()
            updated = config_store.add_command(config, *self._command_form_args(form))
            config_store.save_config(self.config_path, updated)
        except (OSError, config_store.ConfigError) as exc:
            return self._commands(user, csrf, _error_text(exc), True)
        self.audit.append(
            user, "command.add", self._first(form, "text"), now=self._now_ts()
        )
        return _redirect(COMMANDS_PATH)

    def _commands_update(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        command_id = self._first(form, "command")
        try:
            config = self._load_config()
            updated = config_store.update_command(
                config, command_id, *self._command_form_args(form)
            )
            config_store.save_config(self.config_path, updated)
        except (OSError, config_store.ConfigError) as exc:
            return self._commands(user, csrf, _error_text(exc), True)
        self.audit.append(user, "command.update", command_id, now=self._now_ts())
        return _redirect(COMMANDS_PATH)

    def _commands_delete(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        command_id = self._first(form, "command")
        try:
            config = self._load_config()
            updated = config_store.delete_command(config, command_id)
            config_store.save_config(self.config_path, updated)
        except (OSError, config_store.ConfigError) as exc:
            return self._commands(user, csrf, _error_text(exc), True)
        self.audit.append(user, "command.delete", command_id, now=self._now_ts())
        return _redirect(COMMANDS_PATH)

    def _commands_toggle(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        command_id = self._first(form, "command")
        enabled = self._first(form, "enabled") == "1"
        try:
            config = self._load_config()
            updated = config_store.set_command_enabled(config, command_id, enabled)
            config_store.save_config(self.config_path, updated)
        except (OSError, config_store.ConfigError) as exc:
            return self._commands(user, csrf, _error_text(exc), True)
        self.audit.append(
            user,
            "command.toggle",
            command_id,
            "enabled" if enabled else "disabled",
            now=self._now_ts(),
        )
        return _redirect(COMMANDS_PATH)

    # --- Ereignisse ---
    def _events(
        self,
        query: dict[str, list[str]],
        user: str,
        csrf: str,
        flash: str | None = None,
        error: bool = False,
    ) -> Response:
        sort_key = self._first(query, "sort", events_mod.DEFAULT_SORT)
        if sort_key not in events_mod.SORT_KEYS:
            sort_key = events_mod.DEFAULT_SORT
        direction = self._first(query, "dir", events_mod.DEFAULT_DIRECTION)
        if direction not in events_mod.SORT_DIRECTIONS:
            direction = events_mod.DEFAULT_DIRECTION
        filters = {
            "q": self._first(query, "q"),
            "decision": self._first(query, "decision"),
            "command": self._first(query, "command"),
            "from": self._first(query, "from"),
            "to": self._first(query, "to"),
            "sort": sort_key,
            "dir": direction,
        }
        try:
            page = max(1, int(self._first(query, "page", "1")))
        except ValueError:
            page = 1
        config = self._load_config()
        commands = config.get("commands", [])
        if not isinstance(commands, list):
            commands = []
        all_events = events_mod.read_events(self.log_path)
        filtered = events_mod.filter_events(
            all_events,
            query=filters["q"],
            decision=filters["decision"],
            command=filters["command"],
            date_from=filters["from"],
            date_to=filters["to"],
        )
        ordered = events_mod.sort_events(filtered, sort_key, direction)
        total = len(ordered)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, total_pages)
        start = (page - 1) * PAGE_SIZE
        page_events = ordered[start : start + PAGE_SIZE]
        return _html(
            200,
            templates.events_page(
                page_events,
                filters,
                commands,
                sort_key,
                direction,
                user,
                csrf,
                page,
                total_pages,
                total,
                flash,
                error,
            ),
        )

    def _event_detail(
        self, query: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        event_id = self._first(query, "id")
        for event in events_mod.read_events(self.log_path):
            if event.get("_id") == event_id:
                return _html(200, templates.event_detail_page(event, user, csrf))
        return _html(404, templates.error_page("Ereignis nicht gefunden", user, csrf))

    def _filtered_ids(self, form: dict[str, list[str]]) -> set[str]:
        filtered = events_mod.filter_events(
            events_mod.read_events(self.log_path),
            query=self._first(form, "q"),
            decision=self._first(form, "decision"),
            command=self._first(form, "command"),
            date_from=self._first(form, "from"),
            date_to=self._first(form, "to"),
        )
        return {str(event.get("_id")) for event in filtered}

    def _events_delete(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        if self._first(form, "select_all") == "1":
            ids = self._filtered_ids(form)
            target = "alle gefilterten"
        else:
            ids = set(form.get("ids", []))
            target = ",".join(sorted(ids))
        if not ids:
            return self._events({}, user, csrf, "Keine Ereignisse ausgewählt.", True)
        removed = events_mod.delete_events(self.log_path, ids)
        self.audit.append(
            user,
            "events.delete",
            target,
            f"{removed} entfernt",
            now=self._now_ts(),
        )
        return self._events({}, user, csrf, f"{removed} Ereignis(se) gelöscht.")

    # --- Audit / Status / Einstellungen ---
    def _audit(
        self,
        user: str,
        csrf: str,
        query: dict[str, list[str]] | None = None,
    ) -> Response:
        query = query or {}
        sort_key = self._first(query, "sort", "ts")
        if sort_key not in AUDIT_SORT_KEYS:
            sort_key = "ts"
        direction = self._first(query, "dir", "desc")
        if direction not in ("asc", "desc"):
            direction = "desc"
        ok, bad_id = self.audit.verify()
        entries = _sort_audit(self.audit.list(), sort_key, direction)
        return _html(
            200,
            templates.audit_page(
                entries, ok, bad_id, user, csrf, sort_key, direction
            ),
        )

    def _status(self, user: str, csrf: str) -> Response:
        config = self._load_config()
        errors = status_mod.recent_errors(events_mod.read_events(self.log_path))
        return _html(
            200, templates.status_page(self._statuses(config), errors, user, csrf)
        )

    def _settings(
        self,
        user: str,
        csrf: str,
        flash: str | None = None,
        error: bool = False,
    ) -> Response:
        return _html(
            200, templates.settings_page(self._load_config(), user, csrf, flash, error)
        )

    def _settings_retention(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        try:
            days = int(self._first(form, "days"))
            config = self._load_config()
            updated = config_store.set_retention(config, days)
            config_store.save_config(self.config_path, updated)
        except (ValueError, OSError, config_store.ConfigError) as exc:
            return self._settings(user, csrf, _error_text(exc), True)
        self.audit.append(
            user, "settings.retention", "retention_days", str(days), now=self._now_ts()
        )
        return self._settings(user, csrf, "Aufbewahrung gespeichert.")

    def _settings_cleanup(self, user: str, csrf: str) -> Response:
        config = self._load_config()
        retention = config.get("retention_days", 30)
        removed = events_mod.prune_events(self.log_path, retention, now=self._now_ts())
        self.audit.append(
            user, "settings.cleanup", "events", f"{removed} entfernt", now=self._now_ts()
        )
        return self._settings(user, csrf, f"{removed} alte Ereignis(se) entfernt.")

    def _backup(self) -> Response:
        data = config_store.backup_bytes(self._load_config())
        return Response(
            200,
            data,
            {
                "Content-Type": "application/json; charset=utf-8",
                "Content-Disposition": 'attachment; filename="signal-bridge-config.json"',
            },
        )

    def _restore(
        self, form: dict[str, list[str]], user: str, csrf: str
    ) -> Response:
        raw = self._first(form, "backup").encode("utf-8")
        try:
            config_store.restore_config(self.config_path, raw)
        except (OSError, config_store.ConfigError) as exc:
            return self._settings(user, csrf, _error_text(exc), True)
        self.audit.append(user, "settings.restore", "config", now=self._now_ts())
        return self._settings(user, csrf, "Konfiguration wiederhergestellt.")

    # --- Statische Dateien ---
    def _static(self, route: str) -> Response:
        name = route[len("/static/") :]
        if not name or "/" in name or "\\" in name or name.startswith("."):
            return _html(404, templates.error_page("Datei nicht gefunden"))
        path = STATIC_DIR / name
        if not path.is_file():
            return _html(404, templates.error_page("Datei nicht gefunden"))
        content_type = STATIC_TYPES.get(path.suffix, "application/octet-stream")
        return Response(200, path.read_bytes(), {"Content-Type": content_type})


class _AdminServer(socketserver.ThreadingTCPServer):
    """Threading-Server für die Weboberfläche."""

    allow_reuse_address = True
    daemon_threads = True

    def server_bind(self) -> None:
        super().server_bind()
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


class _RequestHandler(BaseHTTPRequestHandler):
    app: AdminApp

    def _dispatch(self, method: str) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        try:
            response = self.app.handle(method, self.path, dict(self.headers), body)
        except Exception:
            LOG.exception("Unbehandelter Fehler bei %s %s", method, self.path)
            response = _html(
                500,
                templates.error_page(
                    "Interner Fehler. Bitte den Administrator informieren."
                ),
            )
        self.send_response(response.status)
        for key, value in response.headers.items():
            self.send_header(key, value)
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        if response.body:
            self.wfile.write(response.body)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def log_message(self, *args: Any) -> None:
        return


def serve(app: AdminApp, host: str = "127.0.0.1", port: int = 8090) -> None:
    handler = type("BoundHandler", (_RequestHandler,), {"app": app})
    server = _AdminServer((host, port), handler)
    try:
        # Bewusster HTTP-Server im lokalen Netz; TLS optional via Reverse-Proxy.
        server.serve_forever()  # NOSONAR
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Signal-Administration (HAD-0008)")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument(
        "--host", default=os.environ.get("SIGNAL_ADMIN_HOST", "127.0.0.1")
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("SIGNAL_ADMIN_PORT", "8090"))
    )
    parser.add_argument("--service-unit", default="signal-bridge.service")
    parser.add_argument("--create-user", metavar="USERNAME")
    args = parser.parse_args(argv)

    secret = os.environ.get("SIGNAL_ADMIN_SECRET", "")
    if not secret:
        print("SIGNAL_ADMIN_SECRET fehlt", file=sys.stderr)
        return 2

    app = AdminApp(
        args.config, args.log, args.db, secret, service_unit=args.service_unit
    )
    if args.create_user:
        password = os.environ.get("SIGNAL_ADMIN_PASSWORD") or getpass.getpass(
            "Passwort: "
        )
        app.store.create_user(args.create_user, auth.hash_password(password))
        print(f"Benutzer {args.create_user} angelegt")
        return 0

    serve(app, args.host, args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
