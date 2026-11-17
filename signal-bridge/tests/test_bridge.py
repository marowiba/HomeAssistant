# pyright: basic
"""Tests fuer die Signal-Bridge (HAD-0002)."""

from __future__ import annotations

import http.server
import json
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bridge  # noqa: E402

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
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(self.write(config_data(allowlist=[{"uuid": UUID_A}])))

    def test_entry_without_identifier_rejected(self):
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(self.write(config_data(allowlist=[{"label": "X"}])))

    def test_unknown_timezone_rejected(self):
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(self.write(config_data(timezone="Mars/Olympus")))

    def test_retention_must_be_positive(self):
        with self.assertRaises(bridge.ConfigError):
            bridge.load_config(self.write(config_data(retention_days=0)))

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
    def config(self):
        return bridge.Config(
            events_url="http://127.0.0.1:8080/api/v1/events",
            log_path=Path("/tmp/x.jsonl"),
            retention_days=30,
            timezone=timezone.utc,
            read_timeout=300,
            reconnect_delay=5,
            prune_interval=3600,
            allowlist=(bridge.AllowEntry(label="Matthias", number=NUMBER_A, uuid=UUID_A),),
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


if __name__ == "__main__":
    unittest.main()
