#!/usr/bin/env python3
"""HAD-0002: Signal-Empfangsdienst mit Absender-Allowlist und Chat-Log.

Liest den Ereignisstrom des signal-cli-Daemons, entscheidet anhand einer
expliziten Allowlist, ob ein Absender freigegeben ist, und schreibt jede
eingegangene Nachricht in ein JSON-Lines-Protokoll.

Es wird nichts ausgewertet und nichts an Home Assistant weitergeleitet.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import queue
import signal
import sys
import threading
import time
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Iterable, Iterator, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from command_parser import parse_command
from ha_client import perform_action
from signal_client import DEFAULT_RPC_URL, send_reply

LOG = logging.getLogger("signal-bridge")

DEFAULT_EVENTS_URL = "http://127.0.0.1:8080/api/v1/events"
DEFAULT_LOG_PATH = "/var/lib/signal-bridge/messages.jsonl"
DEFAULT_RETENTION_DAYS = 30
DEFAULT_TIMEZONE = "Europe/Berlin"
DEFAULT_READ_TIMEOUT = 300
DEFAULT_RECONNECT_DELAY = 5
DEFAULT_PRUNE_INTERVAL = 3600

LOG_FILE_MODE = 0o640

_ALLOWED_URL_SCHEMES = frozenset({"http", "https"})
FIXED_COMMAND_IDS = ("on", "off", "status", "help")


def _empty_commands() -> dict[str, bool]:
    return {}


def _is_http_url(value: str) -> bool:
    """Prueft, ob der Wert eine absolute http(s)-URL ist."""
    parsed = urlparse(value)
    return parsed.scheme in _ALLOWED_URL_SCHEMES and bool(parsed.netloc)


class ConfigError(Exception):
    """Ungueltige oder unvollstaendige Konfiguration."""


@dataclass(frozen=True)
class AllowEntry:
    label: str
    number: str | None = None
    uuid: str | None = None
    enabled: bool = True


@dataclass(frozen=True)
class SignalConfig:
    enabled: bool = True
    rpc_url: str = DEFAULT_RPC_URL
    timeout: int = 10


@dataclass(frozen=True)
class HomeAssistantConfig:
    enabled: bool
    timeout: int
    actions: dict[str, str]
    status_url: str | None = None
    status_token: str | None = None


@dataclass(frozen=True)
class Config:
    events_url: str
    log_path: Path
    retention_days: int
    timezone: tzinfo
    read_timeout: int
    reconnect_delay: int
    prune_interval: int
    allowlist: tuple[AllowEntry, ...]
    home_assistant: HomeAssistantConfig = field(
        default_factory=lambda: HomeAssistantConfig(enabled=False, timeout=10, actions={})
    )
    signal: SignalConfig = field(default_factory=SignalConfig)
    commands: dict[str, bool] = field(default_factory=_empty_commands)


@dataclass(frozen=True)
class IncomingMessage:
    received_ms: int
    sender_number: str | None
    sender_uuid: str | None
    sender_name: str | None
    text: str | None
    attachments: int


def _positive_int(raw: dict[str, Any], key: str, default: int) -> int:
    value = raw.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{key} muss eine positive Ganzzahl sein")
    return value


def _parse_entry(item: Any, index: int) -> AllowEntry:
    if not isinstance(item, dict):
        raise ConfigError(f"allowlist[{index}] muss ein Objekt sein")

    entry_raw = cast(dict[str, Any], item)
    label = entry_raw.get("label")
    if not isinstance(label, str) or not label.strip():
        raise ConfigError(f"allowlist[{index}].label fehlt oder ist leer")

    number = entry_raw.get("number")
    uuid = entry_raw.get("uuid")
    if number is not None and not isinstance(number, str):
        raise ConfigError(f"allowlist[{index}].number muss Text sein")
    if uuid is not None and not isinstance(uuid, str):
        raise ConfigError(f"allowlist[{index}].uuid muss Text sein")
    if not number and not uuid:
        raise ConfigError(f"allowlist[{index}] braucht number oder uuid")

    enabled = entry_raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigError(f"allowlist[{index}].enabled muss true oder false sein")

    return AllowEntry(
        label=label.strip(),
        number=number or None,
        uuid=uuid or None,
        enabled=enabled,
    )


def _parse_signal(raw_obj: dict[str, Any]) -> SignalConfig:
    section = raw_obj.get("signal")
    if section is None:
        return SignalConfig()
    if not isinstance(section, dict):
        raise ConfigError("signal muss ein Objekt sein")

    section_obj = cast(dict[str, Any], section)
    enabled = section_obj.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigError("signal.enabled muss true oder false sein")

    rpc_url = section_obj.get("rpc_url", DEFAULT_RPC_URL)
    if not isinstance(rpc_url, str) or not _is_http_url(rpc_url):
        raise ConfigError("signal.rpc_url muss eine http(s)-URL sein")

    timeout = _positive_int(section_obj, "timeout_seconds", 10)
    return SignalConfig(enabled=enabled, rpc_url=rpc_url, timeout=timeout)


def _parse_commands(raw_obj: dict[str, Any]) -> dict[str, bool]:
    section = raw_obj.get("commands")
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ConfigError("commands muss ein Objekt sein")

    section_obj = cast(dict[str, Any], section)
    result: dict[str, bool] = {}
    for key, value in section_obj.items():
        if key not in FIXED_COMMAND_IDS:
            raise ConfigError(f"commands.{key} ist kein festes Kommando")
        if not isinstance(value, bool):
            raise ConfigError(f"commands.{key} muss true oder false sein")
        result[key] = value
    return result


def _parse_actions(section_obj: dict[str, Any], enabled: bool) -> dict[str, str]:
    actions_raw = section_obj.get("actions", {})
    if not isinstance(actions_raw, dict):
        raise ConfigError("home_assistant.actions muss ein Objekt sein")

    actions_obj = cast(dict[str, Any], actions_raw)
    actions: dict[str, str] = {}
    for key in ("on", "off"):
        value = actions_obj.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not _is_http_url(value):
            raise ConfigError(f"home_assistant.actions.{key} muss eine http(s)-URL sein")
        actions[key] = value

    if enabled:
        missing = [key for key in ("on", "off") if key not in actions]
        if missing:
            raise ConfigError("home_assistant.actions fehlen: " + ", ".join(missing))
    return actions


def _parse_status(section_obj: dict[str, Any]) -> tuple[str | None, str | None]:
    status_raw = section_obj.get("status")
    if status_raw is None:
        return None, None
    if not isinstance(status_raw, dict):
        raise ConfigError("home_assistant.status muss ein Objekt sein")

    status_obj = cast(dict[str, Any], status_raw)
    url_value = status_obj.get("url")
    token_value = status_obj.get("token")
    if not isinstance(url_value, str) or not _is_http_url(url_value):
        raise ConfigError("home_assistant.status.url muss eine http(s)-URL sein")
    if not isinstance(token_value, str) or not token_value:
        raise ConfigError("home_assistant.status.token fehlt")
    return url_value, token_value


def _parse_home_assistant(raw_obj: dict[str, Any]) -> HomeAssistantConfig:
    section = raw_obj.get("home_assistant")
    if section is None:
        return HomeAssistantConfig(enabled=False, timeout=10, actions={})
    if not isinstance(section, dict):
        raise ConfigError("home_assistant muss ein Objekt sein")

    section_obj = cast(dict[str, Any], section)
    enabled = section_obj.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigError("home_assistant.enabled muss true oder false sein")

    timeout = _positive_int(section_obj, "timeout_seconds", 10)
    actions = _parse_actions(section_obj, enabled)
    status_url, status_token = _parse_status(section_obj)

    return HomeAssistantConfig(
        enabled=enabled,
        timeout=timeout,
        actions=actions,
        status_url=status_url,
        status_token=status_token,
    )


def load_config(path: Path) -> Config:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Konfiguration nicht gefunden: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Konfiguration ist kein gueltiges JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Konfiguration muss ein JSON-Objekt sein")

    raw_obj = cast(dict[str, Any], raw)
    tz_name = raw_obj.get("timezone", DEFAULT_TIMEZONE)
    if not isinstance(tz_name, str):
        raise ConfigError("timezone muss Text sein")
    if tz_name.upper() in {"UTC", "Z"}:
        tz: tzinfo = timezone.utc
    else:
        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ConfigError(f"Unbekannte Zeitzone: {tz_name}") from exc

    events_url = raw_obj.get("events_url", DEFAULT_EVENTS_URL)
    if not isinstance(events_url, str) or not _is_http_url(events_url):
        raise ConfigError("events_url muss eine http(s)-URL sein")

    log_path = raw_obj.get("log_path", DEFAULT_LOG_PATH)
    if not isinstance(log_path, str) or not log_path:
        raise ConfigError("log_path muss ein Pfad sein")

    allowlist_value = raw_obj.get("allowlist", [])
    if not isinstance(allowlist_value, list):
        raise ConfigError("allowlist muss eine Liste sein")
    allowlist_raw = cast(list[Any], allowlist_value)

    entries = tuple(_parse_entry(item, index) for index, item in enumerate(allowlist_raw))

    return Config(
        events_url=events_url,
        log_path=Path(log_path),
        retention_days=_positive_int(raw_obj, "retention_days", DEFAULT_RETENTION_DAYS),
        timezone=tz,
        read_timeout=_positive_int(raw_obj, "read_timeout_seconds", DEFAULT_READ_TIMEOUT),
        reconnect_delay=_positive_int(raw_obj, "reconnect_delay_seconds", DEFAULT_RECONNECT_DELAY),
        prune_interval=_positive_int(raw_obj, "prune_interval_seconds", DEFAULT_PRUNE_INTERVAL),
        allowlist=entries,
        home_assistant=_parse_home_assistant(raw_obj),
        signal=_parse_signal(raw_obj),
        commands=_parse_commands(raw_obj),
    )


def _entry_identifies(entry: AllowEntry, number: str | None, uuid: str | None) -> bool:
    """Lockere Zuordnung, auch fuer deaktivierte Eintraege."""
    if entry.uuid and uuid:
        return entry.uuid == uuid
    if entry.number and number:
        return entry.number == number
    return False


def _entry_matches(entry: AllowEntry, number: str | None, uuid: str | None) -> bool:
    """Strenge Zuordnung: eine gesetzte UUID muss uebereinstimmen."""
    if entry.uuid:
        return bool(uuid) and entry.uuid == uuid
    if entry.number:
        return bool(number) and entry.number == number
    return False


def match_sender(
    allowlist: tuple[AllowEntry, ...],
    number: str | None,
    uuid: str | None,
) -> tuple[AllowEntry | None, str]:
    """Gibt den passenden Eintrag und den Grund zurueck."""
    for entry in allowlist:
        if not entry.enabled:
            if _entry_identifies(entry, number, uuid):
                return None, "sender_disabled"
            continue
        if _entry_matches(entry, number, uuid):
            return entry, "allowlist"
    return None, "not_in_allowlist"


def extract_envelope(payload: Any) -> dict[str, Any] | None:
    """Holt den Envelope aus einer JSON-RPC-Nachricht oder einem Rohobjekt."""
    if not isinstance(payload, dict):
        return None
    payload_obj = cast(dict[str, Any], payload)
    params = payload_obj.get("params")
    if isinstance(params, dict):
        params_obj = cast(dict[str, Any], params)
        envelope = params_obj.get("envelope")
        if isinstance(envelope, dict):
            return cast(dict[str, Any], envelope)
    envelope = payload_obj.get("envelope")
    if isinstance(envelope, dict):
        return cast(dict[str, Any], envelope)
    return None


def parse_envelope(envelope: dict[str, Any]) -> IncomingMessage | None:
    """Wandelt einen Envelope in eine Nachricht um. None bei Nicht-Nachrichten."""
    data = envelope.get("dataMessage")
    if not isinstance(data, dict):
        return None

    data_obj = cast(dict[str, Any], data)
    timestamp = data_obj.get("timestamp")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        timestamp = envelope.get("timestamp")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        return None

    attachments = data_obj.get("attachments")
    attachment_count = len(cast(list[Any], attachments)) if isinstance(attachments, list) else 0

    text = data_obj.get("message")
    if not isinstance(text, str):
        text = None

    number = envelope.get("sourceNumber") or envelope.get("source")
    uuid = envelope.get("sourceUuid")
    name = envelope.get("sourceName")

    return IncomingMessage(
        received_ms=timestamp,
        sender_number=number if isinstance(number, str) else None,
        sender_uuid=uuid if isinstance(uuid, str) else None,
        sender_name=name if isinstance(name, str) else None,
        text=text,
        attachments=attachment_count,
    )


def format_timestamp(ms: int, tz: tzinfo) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=tz).isoformat(timespec="seconds")


def build_record(message: IncomingMessage, config: Config) -> dict[str, Any]:
    entry, reason = match_sender(config.allowlist, message.sender_number, message.sender_uuid)
    allowed = entry is not None
    command = parse_command(message.text)
    if command is not None and not config.commands.get(command, True):
        command = None
    return {
        "ts": format_timestamp(message.received_ms, config.timezone),
        "received_ms": message.received_ms,
        "sender_number": message.sender_number,
        "sender_uuid": message.sender_uuid,
        "sender_name": message.sender_name,
        "text": message.text,
        "attachments": message.attachments,
        "decision": "allowed" if allowed else "blocked",
        "reason": reason,
        "matched_label": entry.label if entry is not None else None,
        "command": command,
        "actionable": allowed and command is not None,
        "action": None,
        "reply": None,
    }


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, LOG_FILE_MODE)
    try:
        os.write(descriptor, line.encode("utf-8"))
    finally:
        os.close(descriptor)


def prune_log(
    path: Path,
    retention_days: int,
    now: datetime | None = None,
) -> tuple[int, int]:
    """Entfernt Eintraege ausserhalb der Frist. Gibt (behalten, verworfen) zurueck."""
    if not path.exists():
        return 0, 0

    reference = now or datetime.now(timezone.utc)
    cutoff_ms = int((reference - timedelta(days=retention_days)).timestamp() * 1000)

    kept: list[str] = []
    dropped = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                dropped += 1
                continue
            if not isinstance(record, dict):
                dropped += 1
                continue
            record_obj = cast(dict[str, Any], record)
            received = record_obj.get("received_ms")
            if not isinstance(received, int) or isinstance(received, bool) or received < cutoff_ms:
                dropped += 1
                continue
            kept.append(stripped)

    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for line in kept:
            handle.write(line + "\n")
    os.chmod(temporary, LOG_FILE_MODE)
    os.replace(temporary, path)
    return len(kept), dropped


def parse_sse_stream(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Wandelt SSE-Zeilen in JSON-Objekte um."""
    data: list[str] = []

    def flush() -> Iterator[dict[str, Any]]:
        if not data:
            return
        payload = "\n".join(data)
        data.clear()
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            LOG.warning("Ungueltiges JSON im Ereignisstrom, Ereignis verworfen")
            return
        if isinstance(parsed, dict):
            yield parsed

    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line:
            yield from flush()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data.append(line[5:].lstrip())

    yield from flush()


def iter_events(url: str, timeout: int) -> Iterator[dict[str, Any]]:
    request = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        decoded = (line.decode("utf-8", errors="replace") for line in response)
        yield from parse_sse_stream(decoded)


def _read_events(
    config: Config,
    stop: threading.Event,
    events: "queue.Queue[dict[str, Any]]",
) -> None:
    """Liest den Ereignisstrom in einem Hintergrundthread.

    Der Thread ist ein Daemon, damit ein blockierender Socket-Read den
    Prozess beim Beenden nicht aufhaelt.
    """
    while not stop.is_set():
        try:
            for payload in iter_events(config.events_url, config.read_timeout):
                if stop.is_set():
                    return
                events.put(payload)
        except OSError as exc:
            if stop.is_set():
                return
            LOG.warning("Ereignisstrom unterbrochen: %s", exc)
            stop.wait(config.reconnect_delay)


def _describe_reply(reply: Any) -> str:
    if not isinstance(reply, dict):
        return "keine"
    reply_obj = cast(dict[str, Any], reply)
    if not reply_obj.get("attempted"):
        return f"nicht gesendet ({reply_obj.get('detail')})"
    return "ok" if reply_obj.get("ok") else f"fehlgeschlagen ({reply_obj.get('detail')})"


def _describe_action(action: Any) -> str:
    if not isinstance(action, dict):
        return "keine"
    action_obj = cast(dict[str, Any], action)
    if not action_obj.get("attempted"):
        return f"nicht ausgefuehrt ({action_obj.get('detail')})"
    return "ok" if action_obj.get("ok") else f"fehlgeschlagen ({action_obj.get('detail')})"


def _apply_action_and_reply(record: dict[str, Any], config: Config) -> None:
    result = perform_action(
        record["command"],
        config.home_assistant.actions,
        config.home_assistant.status_url,
        config.home_assistant.status_token,
        config.home_assistant.timeout,
        config.home_assistant.enabled,
    )
    record["action"] = result.as_dict()

    reply = send_reply(
        record["command"],
        record["action"],
        record["sender_number"],
        config.signal.rpc_url,
        config.signal.timeout,
        config.signal.enabled,
    )
    record["reply"] = reply.as_dict()


def _log_record(record: dict[str, Any]) -> None:
    LOG.info(
        "Nachricht von %s: %s (%s), Kommando: %s, Aktion: %s, Antwort: %s",
        record["sender_uuid"] or record["sender_number"] or "unbekannt",
        record["decision"],
        record["reason"],
        record["command"] or "keins",
        _describe_action(record.get("action")),
        _describe_reply(record.get("reply")),
    )


def _process_payload(payload: dict[str, Any], config: Config, dry_run: bool) -> None:
    envelope = extract_envelope(payload)
    if envelope is None:
        return
    message = parse_envelope(envelope)
    if message is None:
        return

    record = build_record(message, config)
    if record["actionable"]:
        _apply_action_and_reply(record, config)

    if dry_run:
        print(json.dumps(record, ensure_ascii=False))
    else:
        append_record(config.log_path, record)

    _log_record(record)


def _maybe_prune(config: Config, last_prune: float) -> float:
    now = time.monotonic()
    if now - last_prune < config.prune_interval:
        return last_prune
    kept, dropped = prune_log(config.log_path, config.retention_days)
    LOG.info("Aufbewahrung: %d behalten, %d entfernt", kept, dropped)
    return now


def run(config: Config, stop: threading.Event, dry_run: bool = False) -> None:
    last_prune = 0.0
    if not dry_run:
        kept, dropped = prune_log(config.log_path, config.retention_days)
        LOG.info("Aufbewahrung beim Start: %d behalten, %d entfernt", kept, dropped)
        last_prune = time.monotonic()

    events: "queue.Queue[dict[str, Any]]" = queue.Queue()
    reader = threading.Thread(
        target=_read_events,
        args=(config, stop, events),
        name="sse-reader",
        daemon=True,
    )
    reader.start()

    while not stop.is_set():
        try:
            payload = events.get(timeout=1.0)
        except queue.Empty:
            continue

        _process_payload(payload, config, dry_run)

        if not dry_run:
            last_prune = _maybe_prune(config, last_prune)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Signal-Bridge: Absender-Allowlist und Chat-Log (HAD-0002)"
    )
    parser.add_argument("--config", required=True, type=Path, help="Pfad zur Konfiguration")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Konfiguration pruefen und beenden",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Eintraege auf stdout ausgeben statt in die Logdatei schreiben",
    )
    parser.add_argument(
        "--prune-now",
        action="store_true",
        help="Aufbewahrung sofort anwenden und beenden",
    )
    parser.add_argument("--log-level", default="INFO", help="Logstufe, Standard INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(levelname)s %(name)s - %(message)s",
    )

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        LOG.exception("Konfiguration ungueltig: %s", exc)
        return 2

    if args.check_config:
        print(
            f"Konfiguration gueltig: {len(config.allowlist)} Allowlist-Eintraege, "
            f"Aufbewahrung {config.retention_days} Tage, Log {config.log_path}"
        )
        return 0

    if args.prune_now:
        kept, dropped = prune_log(config.log_path, config.retention_days)
        print(f"Aufbewahrung: {kept} behalten, {dropped} entfernt")
        return 0

    stop = threading.Event()

    def handle_signal(signum: int, _frame: Any) -> None:
        LOG.info("Signal %s empfangen, beende", signum)
        stop.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    run(config, stop, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
