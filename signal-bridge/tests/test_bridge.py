# pyright: basic
"""Tests fuer die Signal-Bridge (HAD-0002)."""

from __future__ import annotations

import contextlib
import http.server
import io
import json
import queue
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bridge  # noqa: E402
import command_parser  # noqa: E402
import ha_client  # noqa: E402
import signal_client  # noqa: E402

UUID_A = "0929926d-1816-4157-9e5f-f57862547f66"
UUID_B = "4081e291-bf9c-4bca-8eff-ab2466783e53"
NUMBER_A = "+491700000001"
NUMBER_B = "+491700000002"
SAMPLE_MS = 1794820723054


def config_data(**overrides):
    data = {
        "events_url": "http://127.0.0.1:8080/api/v1/events",
        "log_path": "/tmp/messages.jsonl",
        "retention_days": 30,
        "timezone": "UTC",
        "allowlist": [
            {"label": "Matthias", "number": NUMBER_A, "uuid": UUID_A, "enabled": True}
        ],
    }
    data.update(overrides)
    return data


def envelope(**overrides):
    data = {
        "sourceNumber": NUMBER_A,
        "sourceUuid": UUID_A,
        "sourceName": "Matthias",
        "timestamp": SAMPLE_MS,
        "dataMessage": {"timestamp": SAMPLE_MS, "message": "Test Had"},
    }
    data.update(overrides)
    return data


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, data):
        path = self.tmp / "config.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_defaults(self):
        config = bridge.load_config(self.write({}))
        self.assertEqual(config.events_url, bridge.DEFAULT_EVENTS_URL)
        self.assertEqual(config.retention_days, bridge.DEFAULT_RETENTION_DAYS)
        self.assertEqual(config.allowlist, ())
        self.assertEqual(getattr(config.timezone, "key", None), bridge.DEFAULT_TIMEZONE)

    def test_allowlist_entry(self):
        config = bridge.load_config(self.write(config_data()))
        self.assertEqual(len(config.allowlist), 1)
        entry = config.allowlist[0]
        self.assertEqual(entry.label, "Matthias")
        self.assertEqual(entry.uuid, UUID_A)
        self.assertEqual(entry.number, NUMBER_A)
        self.assertTrue(entry.enabled)

    def test_missing_label_rejected(self):
        path = self.write(config_data(allowlist=[{"uuid": UUID_A}]))
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_entry_without_identifier_rejected(self):
        path = self.write(config_data(allowlist=[{"label": "X"}]))
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_unknown_timezone_rejected(self):
        path = self.write(config_data(timezone="Mars/Olympus"))
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_retention_must_be_positive(self):
        path = self.write(config_data(retention_days=0))
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_invalid_json_rejected(self):
        path = self.tmp / "broken.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_missing_file_rejected(self):
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(self.tmp / "fehlt.json")


class AllowlistTests(unittest.TestCase):
    def entry(self, **overrides):
        data = {"label": "Matthias", "number": NUMBER_A, "uuid": UUID_A, "enabled": True}
        data.update(overrides)
        return bridge.AllowEntry(**data)

    def test_match_by_uuid(self):
        entry, reason = bridge.match_sender((self.entry(),), NUMBER_A, UUID_A)
        self.assertIsNotNone(entry)
        self.assertEqual(reason, "allowlist")

    def test_uuid_wins_over_number(self):
        entry, _ = bridge.match_sender((self.entry(),), NUMBER_B, UUID_A)
        self.assertIsNotNone(entry)

    def test_reassigned_number_is_blocked(self):
        entry, reason = bridge.match_sender((self.entry(),), NUMBER_A, UUID_B)
        self.assertIsNone(entry)
        self.assertEqual(reason, "not_in_allowlist")

    def test_missing_uuid_is_blocked_when_uuid_configured(self):
        entry, reason = bridge.match_sender((self.entry(),), NUMBER_A, None)
        self.assertIsNone(entry)
        self.assertEqual(reason, "not_in_allowlist")

    def test_number_only_entry(self):
        entry, reason = bridge.match_sender((self.entry(uuid=None),), NUMBER_A, None)
        self.assertIsNotNone(entry)
        self.assertEqual(reason, "allowlist")

    def test_disabled_entry(self):
        entry, reason = bridge.match_sender((self.entry(enabled=False),), NUMBER_A, UUID_A)
        self.assertIsNone(entry)
        self.assertEqual(reason, "sender_disabled")

    def test_unknown_sender(self):
        entry, reason = bridge.match_sender((self.entry(),), NUMBER_B, UUID_B)
        self.assertIsNone(entry)
        self.assertEqual(reason, "not_in_allowlist")

    def test_empty_allowlist(self):
        entry, reason = bridge.match_sender((), NUMBER_A, UUID_A)
        self.assertIsNone(entry)
        self.assertEqual(reason, "not_in_allowlist")


class EnvelopeTests(unittest.TestCase):
    def test_extract_from_params(self):
        payload = {"jsonrpc": "2.0", "method": "receive", "params": {"envelope": envelope()}}
        self.assertEqual(bridge.extract_envelope(payload), envelope())

    def test_extract_from_top_level(self):
        self.assertEqual(bridge.extract_envelope({"envelope": envelope()}), envelope())

    def test_extract_returns_none(self):
        self.assertIsNone(bridge.extract_envelope({"foo": "bar"}))
        self.assertIsNone(bridge.extract_envelope("text"))
        self.assertIsNone(bridge.extract_envelope(None))

    def test_parse_data_message(self):
        message = bridge.parse_envelope(envelope())
        self.assertIsNotNone(message)
        assert message is not None
        self.assertEqual(message.sender_number, NUMBER_A)
        self.assertEqual(message.sender_uuid, UUID_A)
        self.assertEqual(message.sender_name, "Matthias")
        self.assertEqual(message.text, "Test Had")
        self.assertEqual(message.received_ms, SAMPLE_MS)
        self.assertEqual(message.attachments, 0)

    def test_parse_ignores_typing(self):
        self.assertIsNone(bridge.parse_envelope({"sourceUuid": UUID_A, "typingMessage": {}}))

    def test_parse_attachment_only(self):
        env = envelope(dataMessage={"timestamp": 1, "attachments": [{"id": "a"}, {"id": "b"}]})
        message = bridge.parse_envelope(env)
        assert message is not None
        self.assertIsNone(message.text)
        self.assertEqual(message.attachments, 2)

    def test_parse_without_timestamp(self):
        env = envelope(timestamp=None, dataMessage={"message": "x"})
        self.assertIsNone(bridge.parse_envelope(env))


class RecordTests(unittest.TestCase):
    def config(self, commands=None):
        return bridge.Config(
            events_url="http://127.0.0.1:8080/api/v1/events",
            log_path=Path("/tmp/x.jsonl"),
            retention_days=30,
            timezone=timezone.utc,
            read_timeout=300,
            reconnect_delay=5,
            prune_interval=3600,
            allowlist=(bridge.AllowEntry(label="Matthias", number=NUMBER_A, uuid=UUID_A),),
            commands=commands or {},
        )

    def message(self, **overrides):
        data = {
            "received_ms": SAMPLE_MS,
            "sender_number": NUMBER_A,
            "sender_uuid": UUID_A,
            "sender_name": "Matthias",
            "text": "Test Had",
            "attachments": 0,
        }
        data.update(overrides)
        return bridge.IncomingMessage(**data)

    def test_allowed_record(self):
        record = bridge.build_record(self.message(), self.config())
        self.assertEqual(record["decision"], "allowed")
        self.assertEqual(record["reason"], "allowlist")
        self.assertEqual(record["matched_label"], "Matthias")
        self.assertEqual(record["ts"], "2026-11-16T09:18:43+00:00")

    def test_blocked_record(self):
        record = bridge.build_record(
            self.message(sender_number=NUMBER_B, sender_uuid=UUID_B), self.config()
        )
        self.assertEqual(record["decision"], "blocked")
        self.assertEqual(record["reason"], "not_in_allowlist")
        self.assertIsNone(record["matched_label"])

    def test_timestamp_is_readable(self):
        self.assertEqual(
            bridge.format_timestamp(SAMPLE_MS, timezone.utc),
            "2026-11-16T09:18:43+00:00",
        )

    def test_allowed_command_is_actionable(self):
        record = bridge.build_record(self.message(text="HO M an"), self.config())
        self.assertEqual(record["command"], "on")
        self.assertTrue(record["actionable"])

    def test_blocked_command_is_not_actionable(self):
        record = bridge.build_record(
            self.message(sender_number=NUMBER_B, sender_uuid=UUID_B, text="HO M an"),
            self.config(),
        )
        self.assertEqual(record["command"], "on")
        self.assertFalse(record["actionable"])

    def test_allowed_unknown_text_is_not_actionable(self):
        record = bridge.build_record(self.message(text="Hallo"), self.config())
        self.assertIsNone(record["command"])
        self.assertFalse(record["actionable"])

    def test_disabled_command_is_not_actionable(self):
        record = bridge.build_record(
            self.message(text="HO M an"), self.config(commands={"on": False})
        )
        self.assertIsNone(record["command"])
        self.assertFalse(record["actionable"])

    def test_attachment_only_is_not_actionable(self):
        record = bridge.build_record(self.message(text=None), self.config())
        self.assertIsNone(record["command"])
        self.assertFalse(record["actionable"])


class CommandParserTests(unittest.TestCase):
    def test_exact_commands(self):
        self.assertEqual(command_parser.parse_command("HO M an"), "on")
        self.assertEqual(command_parser.parse_command("HO M aus"), "off")
        self.assertEqual(command_parser.parse_command("HO M Status"), "status")

    def test_case_insensitive(self):
        for text in ("HO M AN", "ho m an", "Ho M An", "hO m aN"):
            self.assertEqual(command_parser.parse_command(text), "on", text)
        for text in ("HO M AUS", "ho m aus"):
            self.assertEqual(command_parser.parse_command(text), "off", text)
        for text in ("HO M STATUS", "ho m status"):
            self.assertEqual(command_parser.parse_command(text), "status", text)

    def test_extra_whitespace(self):
        self.assertEqual(command_parser.parse_command("  HO   M   an  "), "on")
        self.assertEqual(command_parser.parse_command("HO\tM\nan"), "on")

    def test_unknown_and_ambiguous_texts(self):
        for text in (
            "HO M",
            "HO M an aus",
            "HO M an!",
            "HO M Status bitte",
            "hallo",
            "an",
            "HO M an, bitte",
        ):
            self.assertIsNone(command_parser.parse_command(text), text)

    def test_none_and_empty(self):
        self.assertIsNone(command_parser.parse_command(None))
        self.assertIsNone(command_parser.parse_command(""))
        self.assertIsNone(command_parser.parse_command("   "))

    def test_normalize(self):
        self.assertEqual(command_parser.normalize("  Ho   M  AN "), "ho m an")
        self.assertIsNone(command_parser.normalize(None))
        self.assertIsNone(command_parser.normalize("  "))


class LogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_writes_jsonl(self):
        path = self.tmp / "sub" / "messages.jsonl"
        bridge.append_record(path, {"a": 1})
        bridge.append_record(path, {"a": 2})
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0]), {"a": 1})
        self.assertEqual(json.loads(lines[1]), {"a": 2})

    def test_prune_removes_old_entries(self):
        path = self.tmp / "messages.jsonl"
        now = datetime(2026, 11, 16, tzinfo=timezone.utc)
        old_ms = int((now - timedelta(days=40)).timestamp() * 1000)
        new_ms = int((now - timedelta(days=1)).timestamp() * 1000)
        bridge.append_record(path, {"received_ms": old_ms})
        bridge.append_record(path, {"received_ms": new_ms})

        kept, dropped = bridge.prune_log(path, 30, now=now)

        self.assertEqual((kept, dropped), (1, 1))
        remaining = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(remaining, [{"received_ms": new_ms}])

    def test_prune_drops_invalid_lines(self):
        path = self.tmp / "messages.jsonl"
        path.write_text("kein json\n", encoding="utf-8")
        self.assertEqual(bridge.prune_log(path, 30), (0, 1))

    def test_prune_missing_file(self):
        self.assertEqual(bridge.prune_log(self.tmp / "fehlt.jsonl", 30), (0, 0))


class SseTests(unittest.TestCase):
    def test_parses_data_lines(self):
        lines = [
            "id: 1",
            'data: {"jsonrpc":"2.0","method":"receive"}',
            "",
            ": keepalive",
            'data: {"a":1}',
            "",
        ]
        events = list(bridge.parse_sse_stream(lines))
        self.assertEqual(events, [{"jsonrpc": "2.0", "method": "receive"}, {"a": 1}])

    def test_ignores_invalid_json(self):
        self.assertEqual(list(bridge.parse_sse_stream(["data: {", ""])), [])

    def test_handles_trailing_event_without_blank_line(self):
        self.assertEqual(list(bridge.parse_sse_stream(['data: {"a":1}'])), [{"a": 1}])


class HomeAssistantConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, data):
        path = self.tmp / "config.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_disabled_by_default(self):
        config = bridge.load_config(self.write({}))
        self.assertFalse(config.home_assistant.enabled)
        self.assertEqual(config.home_assistant.actions, {})

    def test_enabled_requires_all_actions(self):
        data = config_data(
            home_assistant={"enabled": True, "actions": {"on": "http://127.0.0.1/a"}}
        )
        path = self.write(data)
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_enabled_with_actions_and_status(self):
        data = config_data(
            home_assistant={
                "enabled": True,
                "actions": {
                    "on": "http://127.0.0.1:8123/api/webhook/a",
                    "off": "http://127.0.0.1:8123/api/webhook/b",
                },
                "status": {
                    "url": "http://127.0.0.1:8123/api/states/switch.x",
                    "token": "geheim",
                },
            }
        )
        config = bridge.load_config(self.write(data))
        self.assertTrue(config.home_assistant.enabled)
        self.assertEqual(sorted(config.home_assistant.actions), ["off", "on"])
        self.assertEqual(
            config.home_assistant.status_url,
            "http://127.0.0.1:8123/api/states/switch.x",
        )
        self.assertEqual(config.home_assistant.status_token, "geheim")

    def test_status_without_token_rejected(self):
        data = config_data(
            home_assistant={
                "enabled": False,
                "status": {"url": "http://127.0.0.1:8123/api/states/switch.x"},
            }
        )
        path = self.write(data)
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_invalid_url_rejected(self):
        data = config_data(
            home_assistant={"enabled": False, "actions": {"on": "ftp://127.0.0.1/a"}}
        )
        path = self.write(data)
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)


class WebhookTests(unittest.TestCase):
    def start_server(self, handler_cls):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def test_success_without_response(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        port = self.start_server(Handler)
        ok, detail = ha_client.call_webhook(f"http://127.0.0.1:{port}/api/webhook/x", 5)
        self.assertTrue(ok)
        self.assertIsNone(detail)

    def test_read_state(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({"state": "on"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        port = self.start_server(Handler)
        ok, detail = ha_client.read_state(
            f"http://127.0.0.1:{port}/api/states/x", "token", 5
        )
        self.assertTrue(ok)
        self.assertEqual(detail, "on")

    def test_http_error(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(404)
                self.end_headers()

            def log_message(self, *args):
                pass

        port = self.start_server(Handler)
        ok, detail = ha_client.call_webhook(f"http://127.0.0.1:{port}/api/webhook/x", 5)
        self.assertFalse(ok)
        self.assertEqual(detail, "HTTP 404")

    def test_read_state_invalid_json(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"kein json"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        port = self.start_server(Handler)
        ok, detail = ha_client.read_state(
            f"http://127.0.0.1:{port}/api/states/x", "token", 5
        )
        self.assertFalse(ok)
        self.assertEqual(detail, "Antwort ist kein gueltiges JSON")

    def test_connection_refused(self):
        ok, detail = ha_client.call_webhook("http://127.0.0.1:1/api/webhook/x", 2)
        self.assertFalse(ok)
        self.assertIn("Verbindung fehlgeschlagen", detail or "")

    def test_detail_contains_no_webhook_id(self):
        ok, detail = ha_client.call_webhook("http://127.0.0.1:1/api/webhook/geheim", 2)
        self.assertFalse(ok)
        self.assertNotIn("geheim", detail or "")

    def test_detail_contains_no_token(self):
        ok, detail = ha_client.read_state("http://127.0.0.1:1/api/states/x", "geheim", 2)
        self.assertFalse(ok)
        self.assertNotIn("geheim", detail or "")


class PerformActionTests(unittest.TestCase):
    def test_no_command(self):
        result = ha_client.perform_action(None, {}, None, None, 5, True)
        self.assertFalse(result.attempted)
        self.assertIsNone(result.ok)

    def test_disabled(self):
        result = ha_client.perform_action(
            "on", {"on": "http://127.0.0.1/a"}, None, None, 5, False
        )
        self.assertFalse(result.attempted)
        self.assertEqual(result.detail, "Anbindung deaktiviert")

    def test_missing_webhook(self):
        result = ha_client.perform_action("on", {}, None, None, 5, True)
        self.assertFalse(result.attempted)
        self.assertIn("kein Webhook", result.detail or "")

    def test_status_not_configured(self):
        result = ha_client.perform_action("status", {}, None, None, 5, True)
        self.assertFalse(result.attempted)
        self.assertEqual(result.detail, "Statusabfrage nicht konfiguriert")

    def test_success(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        port = server.server_address[1]

        result = ha_client.perform_action(
            "on", {"on": f"http://127.0.0.1:{port}/api/webhook/x"}, None, None, 5, True
        )
        self.assertTrue(result.attempted)
        self.assertTrue(result.ok)
        self.assertIsNone(result.detail)


class CliTests(unittest.TestCase):
    def test_prune_now(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "messages.jsonl"
            log.write_text(
                json.dumps({"received_ms": 1}) + "\n"
                + json.dumps({"received_ms": int(time.time() * 1000)}) + "\n",
                encoding="utf-8",
            )
            config = Path(tmp) / "config.json"
            config.write_text(
                json.dumps({"log_path": str(log), "retention_days": 30}),
                encoding="utf-8",
            )

            code = bridge.main(["--config", str(config), "--prune-now"])

            self.assertEqual(code, 0)
            self.assertEqual(len(log.read_text(encoding="utf-8").splitlines()), 1)


class ShutdownTests(unittest.TestCase):
    def test_run_stops_promptly(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                while True:
                    time.sleep(0.1)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()

        try:
            with tempfile.TemporaryDirectory() as tmp:
                config = bridge.Config(
                    events_url=f"http://127.0.0.1:{port}/api/v1/events",
                    log_path=Path(tmp) / "messages.jsonl",
                    retention_days=30,
                    timezone=timezone.utc,
                    read_timeout=300,
                    reconnect_delay=1,
                    prune_interval=3600,
                    allowlist=(),
                )
                stop = threading.Event()
                worker = threading.Thread(target=bridge.run, args=(config, stop), daemon=True)
                worker.start()
                time.sleep(0.5)
                stop.set()
                worker.join(timeout=3)
                self.assertFalse(worker.is_alive(), "run() hat nicht zeitnah beendet")
        finally:
            server.shutdown()


class SignalReplyTests(unittest.TestCase):
    def test_on_success(self):
        self.assertEqual(
            signal_client.build_reply("on", {"attempted": True, "ok": True, "detail": None}),
            "Home Office ist eingeschaltet.",
        )

    def test_off_success(self):
        self.assertEqual(
            signal_client.build_reply("off", {"attempted": True, "ok": True, "detail": None}),
            "Home Office ist ausgeschaltet.",
        )

    def test_status_on(self):
        self.assertEqual(
            signal_client.build_reply("status", {"attempted": True, "ok": True, "detail": "on"}),
            "Home Office ist eingeschaltet.",
        )

    def test_status_off(self):
        self.assertEqual(
            signal_client.build_reply("status", {"attempted": True, "ok": True, "detail": "off"}),
            "Home Office ist ausgeschaltet.",
        )

    def test_status_unknown(self):
        reply = signal_client.build_reply(
            "status", {"attempted": True, "ok": True, "detail": "unavailable"}
        )
        self.assertIn("unavailable", reply or "")

    def test_error_unreachable(self):
        reply = signal_client.build_reply(
            "on", {"attempted": True, "ok": False, "detail": "Verbindung fehlgeschlagen: x"}
        )
        self.assertEqual(reply, "Fehler: Home Assistant ist nicht erreichbar.")

    def test_error_unauthorized(self):
        reply = signal_client.build_reply(
            "on", {"attempted": True, "ok": False, "detail": "HTTP 401"}
        )
        self.assertEqual(reply, "Fehler: Home Assistant hat den Zugriff abgelehnt.")

    def test_not_attempted(self):
        reply = signal_client.build_reply(
            "on", {"attempted": False, "ok": None, "detail": "Anbindung deaktiviert"}
        )
        self.assertEqual(reply, "Fehler: Die Home-Assistant-Anbindung ist deaktiviert.")

    def test_no_command(self):
        self.assertIsNone(signal_client.build_reply(None, {"attempted": True, "ok": True}))

    def test_no_action(self):
        self.assertIsNone(signal_client.build_reply("on", None))


class SendMessageTests(unittest.TestCase):
    def start_server(self, handler_cls):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        time.sleep(0.05)
        return server.server_address[1]

    def respond(self, payload):
        body = json.dumps(payload).encode()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        return self.start_server(Handler)

    def test_success(self):
        port = self.respond(
            {"jsonrpc": "2.0", "id": 1, "result": {"results": [{"type": "SUCCESS"}]}}
        )
        ok, detail = signal_client.send_message(
            f"http://127.0.0.1:{port}/api/v1/rpc", "+491700000001", "Test", 5
        )
        self.assertTrue(ok)
        self.assertIsNone(detail)

    def test_jsonrpc_error(self):
        port = self.respond({"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "x"}})
        ok, detail = signal_client.send_message(
            f"http://127.0.0.1:{port}/api/v1/rpc", "+491700000001", "Test", 5
        )
        self.assertFalse(ok)
        self.assertEqual(detail, "JSON-RPC-Fehler")

    def test_delivery_failure(self):
        port = self.respond(
            {"jsonrpc": "2.0", "id": 1, "result": {"results": [{"type": "NETWORK_FAILURE"}]}}
        )
        ok, detail = signal_client.send_message(
            f"http://127.0.0.1:{port}/api/v1/rpc", "+491700000001", "Test", 5
        )
        self.assertFalse(ok)
        self.assertIn("NETWORK_FAILURE", detail or "")


class SendReplyTests(unittest.TestCase):
    def test_disabled(self):
        result = signal_client.send_reply(
            "on", {"attempted": True, "ok": True}, "+49", "http://127.0.0.1:1", 2, False
        )
        self.assertFalse(result.attempted)
        self.assertEqual(result.detail, "Antworten deaktiviert")

    def test_no_recipient(self):
        result = signal_client.send_reply(
            "on", {"attempted": True, "ok": True}, None, "http://127.0.0.1:1", 2, True
        )
        self.assertFalse(result.attempted)
        self.assertEqual(result.detail, "kein Empfaenger bekannt")

    def test_no_reply_for_unknown_command(self):
        result = signal_client.send_reply(
            None, {"attempted": True, "ok": True}, "+49", "http://127.0.0.1:1", 2, True
        )
        self.assertFalse(result.attempted)
        self.assertEqual(result.detail, "keine Antwort vorgesehen")


class ConfigEdgeCaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, data):
        path = self.tmp / "config.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def assert_config_error(self, data):
        path = self.write(data)
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_allowlist_item_not_object(self):
        self.assert_config_error(config_data(allowlist=[42]))

    def test_allowlist_number_not_text(self):
        self.assert_config_error(config_data(allowlist=[{"label": "X", "number": 123}]))

    def test_allowlist_uuid_not_text(self):
        self.assert_config_error(config_data(allowlist=[{"label": "X", "uuid": 123}]))

    def test_allowlist_enabled_not_bool(self):
        self.assert_config_error(
            config_data(allowlist=[{"label": "X", "uuid": UUID_A, "enabled": "yes"}])
        )

    def test_signal_section_valid(self):
        config = bridge.load_config(
            self.write(
                config_data(
                    signal={
                        "enabled": False,
                        "rpc_url": "http://127.0.0.1:9/rpc",
                        "timeout_seconds": 3,
                    }
                )
            )
        )
        self.assertFalse(config.signal.enabled)
        self.assertEqual(config.signal.rpc_url, "http://127.0.0.1:9/rpc")
        self.assertEqual(config.signal.timeout, 3)

    def test_signal_section_not_object(self):
        self.assert_config_error(config_data(signal=[]))

    def test_signal_enabled_not_bool(self):
        self.assert_config_error(config_data(signal={"enabled": "yes"}))

    def test_signal_rpc_url_invalid(self):
        self.assert_config_error(config_data(signal={"rpc_url": "ftp://x"}))

    def test_commands_valid(self):
        config = bridge.load_config(self.write(config_data(commands={"on": False})))
        self.assertFalse(config.commands["on"])

    def test_commands_not_object(self):
        self.assert_config_error(config_data(commands=[]))

    def test_commands_unknown(self):
        self.assert_config_error(config_data(commands={"foo": True}))

    def test_commands_not_bool(self):
        self.assert_config_error(config_data(commands={"on": "yes"}))

    def test_actions_not_object(self):
        self.assert_config_error(config_data(home_assistant={"actions": []}))

    def test_home_assistant_not_object(self):
        self.assert_config_error(config_data(home_assistant=[]))

    def test_home_assistant_enabled_not_bool(self):
        self.assert_config_error(config_data(home_assistant={"enabled": "yes"}))

    def test_status_not_object(self):
        self.assert_config_error(config_data(home_assistant={"status": []}))

    def test_status_url_invalid(self):
        self.assert_config_error(
            config_data(home_assistant={"status": {"url": "ftp://x", "token": "t"}})
        )

    def test_enabled_without_status(self):
        config = bridge.load_config(
            self.write(
                config_data(
                    home_assistant={
                        "enabled": True,
                        "actions": {
                            "on": "http://127.0.0.1:8123/api/webhook/a",
                            "off": "http://127.0.0.1:8123/api/webhook/b",
                        },
                    }
                )
            )
        )
        self.assertIsNone(config.home_assistant.status_url)
        self.assertIsNone(config.home_assistant.status_token)

    def test_config_not_object(self):
        path = self.tmp / "config.json"
        path.write_text("[]", encoding="utf-8")
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(path)

    def test_timezone_not_text(self):
        self.assert_config_error(config_data(timezone=123))

    def test_events_url_invalid(self):
        self.assert_config_error(config_data(events_url="ftp://x"))

    def test_log_path_invalid(self):
        self.assert_config_error(config_data(log_path=""))

    def test_allowlist_not_list(self):
        self.assert_config_error(config_data(allowlist={}))


class AllowlistEdgeCaseTests(unittest.TestCase):
    def entry(self, **overrides):
        data = {"label": "Matthias", "number": NUMBER_A, "uuid": UUID_A, "enabled": True}
        data.update(overrides)
        return bridge.AllowEntry(**data)

    def test_disabled_entry_matched_by_number(self):
        entry, reason = bridge.match_sender(
            (self.entry(uuid=None, enabled=False),), NUMBER_A, None
        )
        self.assertIsNone(entry)
        self.assertEqual(reason, "sender_disabled")

    def test_disabled_entry_not_matching_continues(self):
        entry, reason = bridge.match_sender(
            (self.entry(uuid=None, enabled=False),), NUMBER_B, None
        )
        self.assertIsNone(entry)
        self.assertEqual(reason, "not_in_allowlist")

    def test_entry_without_identifier_never_matches(self):
        entry, reason = bridge.match_sender(
            (bridge.AllowEntry(label="X"),), NUMBER_A, UUID_A
        )
        self.assertIsNone(entry)
        self.assertEqual(reason, "not_in_allowlist")

    def test_disabled_entry_then_enabled_match(self):
        disabled = self.entry(uuid=None, number=NUMBER_B, enabled=False)
        entry, reason = bridge.match_sender((disabled, self.entry()), NUMBER_A, UUID_A)
        self.assertIsNotNone(entry)
        self.assertEqual(reason, "allowlist")

    def test_disabled_entry_without_identifier(self):
        entry, reason = bridge.match_sender(
            (bridge.AllowEntry(label="X", enabled=False),), NUMBER_A, UUID_A
        )
        self.assertIsNone(entry)
        self.assertEqual(reason, "not_in_allowlist")


class PruneEdgeCaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_prune_skips_blank_lines(self):
        path = self.tmp / "messages.jsonl"
        now = datetime(2026, 11, 16, tzinfo=timezone.utc)
        new_ms = int((now - timedelta(days=1)).timestamp() * 1000)
        path.write_text("\n" + json.dumps({"received_ms": new_ms}) + "\n", encoding="utf-8")
        self.assertEqual(bridge.prune_log(path, 30, now=now), (1, 0))

    def test_prune_drops_non_object_records(self):
        path = self.tmp / "messages.jsonl"
        path.write_text("[]\n", encoding="utf-8")
        self.assertEqual(bridge.prune_log(path, 30), (0, 1))


class ReadEventsTests(unittest.TestCase):
    def config(self, reconnect_delay=0):
        return bridge.Config(
            events_url="http://127.0.0.1:1/api/v1/events",
            log_path=Path("/tmp/x.jsonl"),
            retention_days=30,
            timezone=timezone.utc,
            read_timeout=1,
            reconnect_delay=reconnect_delay,
            prune_interval=3600,
            allowlist=(),
        )

    def test_stops_when_stop_set_during_iteration(self):
        stop = threading.Event()
        events: "queue.Queue[dict]" = queue.Queue()

        def fake_iter(url, timeout):
            stop.set()
            yield {"a": 1}

        with mock.patch.object(bridge, "iter_events", fake_iter):
            bridge._read_events(self.config(), stop, events)
        self.assertTrue(stop.is_set())
        self.assertTrue(events.empty())

    def test_reconnects_after_oserror(self):
        stop = threading.Event()
        events: "queue.Queue[dict]" = queue.Queue()
        calls = {"n": 0}

        def fake_iter(url, timeout):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("boom")
            stop.set()
            return iter(())

        with mock.patch.object(bridge, "iter_events", fake_iter):
            bridge._read_events(self.config(reconnect_delay=0), stop, events)
        self.assertEqual(calls["n"], 2)


class DescribeTests(unittest.TestCase):
    def test_describe_reply_not_attempted(self):
        self.assertEqual(
            bridge._describe_reply({"attempted": False, "detail": "x"}),
            "nicht gesendet (x)",
        )

    def test_describe_action_not_attempted(self):
        self.assertEqual(
            bridge._describe_action({"attempted": False, "detail": "y"}),
            "nicht ausgefuehrt (y)",
        )


class ProcessPayloadTests(unittest.TestCase):
    def config(self, log_path):
        return bridge.Config(
            events_url="http://127.0.0.1:1/api/v1/events",
            log_path=log_path,
            retention_days=30,
            timezone=timezone.utc,
            read_timeout=1,
            reconnect_delay=1,
            prune_interval=3600,
            allowlist=(bridge.AllowEntry(label="Matthias", number=NUMBER_A, uuid=UUID_A),),
        )

    def test_ignores_payload_without_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "messages.jsonl"
            bridge._process_payload({"foo": "bar"}, self.config(log), False)
            self.assertFalse(log.exists())

    def test_ignores_non_message_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "messages.jsonl"
            payload = {"envelope": {"sourceUuid": UUID_A, "typingMessage": {}}}
            bridge._process_payload(payload, self.config(log), False)
            self.assertFalse(log.exists())

    def test_dry_run_prints_instead_of_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "messages.jsonl"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                bridge._process_payload({"envelope": envelope()}, self.config(log), True)
            self.assertFalse(log.exists())
            self.assertIn("Test Had", buffer.getvalue())


class MaybePruneTests(unittest.TestCase):
    def test_prunes_when_interval_elapsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "messages.jsonl"
            log.write_text("", encoding="utf-8")
            config = bridge.Config(
                events_url="http://127.0.0.1:1/api/v1/events",
                log_path=log,
                retention_days=30,
                timezone=timezone.utc,
                read_timeout=1,
                reconnect_delay=1,
                prune_interval=0,
                allowlist=(),
            )
            self.assertGreaterEqual(bridge._maybe_prune(config, 0.0), 0.0)


class MainTests(unittest.TestCase):
    def test_invalid_config_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "fehlt.json"
            self.assertEqual(bridge.main(["--config", str(missing)]), 2)

    def test_check_config_returns_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(
                json.dumps({"log_path": str(Path(tmp) / "m.jsonl")}), encoding="utf-8"
            )
            self.assertEqual(
                bridge.main(["--config", str(config), "--check-config"]), 0
            )

    def test_run_path_registers_signal_handlers(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(
                json.dumps({"log_path": str(Path(tmp) / "m.jsonl")}), encoding="utf-8"
            )
            captured = {}

            def fake_signal(signum, handler):
                captured[signum] = handler

            with mock.patch.object(bridge.signal, "signal", fake_signal), mock.patch.object(
                bridge, "run", lambda *a, **k: None
            ):
                code = bridge.main(["--config", str(config)])

            self.assertEqual(code, 0)
            self.assertIn(bridge.signal.SIGTERM, captured)
            captured[bridge.signal.SIGTERM](15, None)


class HaClientErrorTests(unittest.TestCase):
    def test_timeout(self):
        with mock.patch.object(
            ha_client.urllib.request, "urlopen", side_effect=TimeoutError()
        ):
            ok, detail = ha_client.call_webhook("http://127.0.0.1/x", 1)
        self.assertFalse(ok)
        self.assertEqual(detail, "Zeitueberschreitung")

    def test_oserror(self):
        with mock.patch.object(
            ha_client.urllib.request, "urlopen", side_effect=OSError("kaputt")
        ):
            ok, detail = ha_client.call_webhook("http://127.0.0.1/x", 1)
        self.assertFalse(ok)
        self.assertIn("Netzwerkfehler", detail or "")

    def read_state_with_body(self, body):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        return ha_client.read_state(f"http://127.0.0.1:{port}/api/states/x", "t", 5)

    def test_read_state_empty_body(self):
        ok, detail = self.read_state_with_body(b"")
        self.assertFalse(ok)
        self.assertEqual(detail, "Leere Antwort")

    def test_read_state_not_object(self):
        ok, detail = self.read_state_with_body(b"[]")
        self.assertFalse(ok)
        self.assertEqual(detail, "Antwort ist kein Objekt")

    def test_read_state_missing_state(self):
        ok, detail = self.read_state_with_body(b"{}")
        self.assertFalse(ok)
        self.assertEqual(detail, "Antwort enthaelt keinen Zustand")


class FriendlyErrorTests(unittest.TestCase):
    def test_missing_detail(self):
        reply = signal_client.build_reply(
            "on", {"attempted": False, "ok": None, "detail": None}
        )
        self.assertEqual(reply, "Fehler: Die Aktion ist fehlgeschlagen.")

    def test_timeout(self):
        reply = signal_client.build_reply(
            "on", {"attempted": True, "ok": False, "detail": "Zeitueberschreitung"}
        )
        self.assertEqual(reply, "Fehler: Home Assistant antwortet nicht.")

    def test_status_not_configured(self):
        reply = signal_client.build_reply(
            "status",
            {"attempted": False, "ok": None, "detail": "Statusabfrage nicht konfiguriert"},
        )
        self.assertEqual(reply, "Fehler: Die Statusabfrage ist nicht eingerichtet.")

    def test_unknown_detail(self):
        reply = signal_client.build_reply(
            "on", {"attempted": True, "ok": False, "detail": "irgendwas"}
        )
        self.assertEqual(reply, "Fehler: Die Aktion ist fehlgeschlagen (irgendwas).")

    def test_status_unknown_state(self):
        reply = signal_client.build_reply(
            "status", {"attempted": True, "ok": True, "detail": None}
        )
        self.assertEqual(reply, "Fehler: Der Schalterzustand ist unbekannt.")

    def test_unknown_command_returns_none(self):
        self.assertIsNone(
            signal_client.build_reply(
                "unbekannt", {"attempted": True, "ok": True, "detail": None}
            )
        )


class SendMessageErrorTests(unittest.TestCase):
    def respond_raw(self, body):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def send(self, port):
        return signal_client.send_message(
            f"http://127.0.0.1:{port}/api/v1/rpc", "+491700000001", "Test", 5
        )

    def test_http_error(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(500)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        ok, detail = self.send(server.server_address[1])
        self.assertFalse(ok)
        self.assertEqual(detail, "HTTP 500")

    def test_url_error(self):
        with mock.patch.object(
            signal_client.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("weg"),
        ):
            ok, detail = signal_client.send_message("http://x", "+49", "t", 1)
        self.assertFalse(ok)
        self.assertIn("Verbindung fehlgeschlagen", detail or "")

    def test_timeout(self):
        with mock.patch.object(
            signal_client.urllib.request, "urlopen", side_effect=TimeoutError()
        ):
            ok, detail = signal_client.send_message("http://x", "+49", "t", 1)
        self.assertFalse(ok)
        self.assertEqual(detail, "Zeitueberschreitung")

    def test_oserror(self):
        with mock.patch.object(
            signal_client.urllib.request, "urlopen", side_effect=OSError("kaputt")
        ):
            ok, detail = signal_client.send_message("http://x", "+49", "t", 1)
        self.assertFalse(ok)
        self.assertIn("Netzwerkfehler", detail or "")

    def test_invalid_json_response(self):
        ok, detail = self.send(self.respond_raw(b"kein json"))
        self.assertFalse(ok)
        self.assertEqual(detail, "Antwort ist kein gueltiges JSON")

    def test_non_object_response(self):
        ok, detail = self.send(self.respond_raw(b"[]"))
        self.assertFalse(ok)
        self.assertEqual(detail, "Antwort ist kein Objekt")

    def test_result_not_object(self):
        ok, detail = self.send(self.respond_raw(json.dumps({"result": 5}).encode()))
        self.assertTrue(ok)
        self.assertIsNone(detail)

    def test_results_not_list(self):
        ok, detail = self.send(
            self.respond_raw(json.dumps({"result": {"results": "x"}}).encode())
        )
        self.assertTrue(ok)
        self.assertIsNone(detail)

    def test_result_item_not_object(self):
        ok, detail = self.send(
            self.respond_raw(json.dumps({"result": {"results": [5]}}).encode())
        )
        self.assertTrue(ok)
        self.assertIsNone(detail)


if __name__ == "__main__":
    unittest.main()
