# pyright: basic
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from signal_admin import events


def record(**overrides):
    data = {
        "ts": "2026-11-16T09:18:43+00:00",
        "received_ms": 1794820723054,
        "sender_number": "+491700000001",
        "sender_name": "Matthias",
        "text": "HO M an",
        "decision": "allowed",
        "command": "on",
        "reason": "allowlist",
        "matched_label": "Matthias",
    }
    data.update(overrides)
    return data


class EventTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, lines):
        path = self.tmp / "messages.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_event_id_stable(self):
        first = events.event_id(record())
        second = events.event_id(record())
        self.assertEqual(first, second)
        self.assertNotEqual(
            events.event_id(record()), events.event_id(record(text="x"))
        )

    def test_read_missing(self):
        self.assertEqual(events.read_events(self.tmp / "fehlt.jsonl"), [])

    def test_read_skips_invalid(self):
        path = self.write(["", "kein json", "[]", json.dumps(record())])
        result = events.read_events(path)
        self.assertEqual(len(result), 1)
        self.assertIn("_id", result[0])

    def test_filter(self):
        items = [record(), record(decision="blocked", command=None, text="Hallo")]
        self.assertEqual(len(events.filter_events(items)), 2)
        self.assertEqual(len(events.filter_events(items, decision="blocked")), 1)
        self.assertEqual(len(events.filter_events(items, command="on")), 1)
        self.assertEqual(len(events.filter_events(items, query="hallo")), 1)
        self.assertEqual(len(events.filter_events(items, date_from="2026-11-17")), 0)
        self.assertEqual(len(events.filter_events(items, date_to="2026-11-15")), 0)
        self.assertEqual(
            len(
                events.filter_events(
                    items, date_from="2026-11-16", date_to="2026-11-16"
                )
            ),
            2,
        )

    def test_prune(self):
        now = 1794820723.054
        old = record(received_ms=int((now - 40 * 86400) * 1000))
        new = record(received_ms=int((now - 1 * 86400) * 1000))
        path = self.write([json.dumps(old), json.dumps(new)])
        self.assertEqual(events.prune_events(path, 30, now=now), 1)
        self.assertEqual(len(events.read_events(path)), 1)

    def test_prune_missing(self):
        self.assertEqual(events.prune_events(self.tmp / "fehlt.jsonl", 30), 0)

    def test_prune_keeps_invalid_and_non_dict(self):
        path = self.write(["kein json", "[]"])
        self.assertEqual(events.prune_events(path, 30, now=0), 0)
        self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)

    def test_prune_skips_blank_lines(self):
        path = self.write(["", json.dumps(record())])
        self.assertEqual(events.prune_events(path, 30, now=0), 0)

    def test_delete(self):
        first = record()
        second = record(text="anders")
        path = self.write([json.dumps(first), json.dumps(second)])
        ids = {events.event_id(first)}
        self.assertEqual(events.delete_events(path, ids), 1)
        remaining = events.read_events(path)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["text"], "anders")

    def test_delete_missing(self):
        self.assertEqual(events.delete_events(self.tmp / "fehlt.jsonl", {"x"}), 0)

    def test_delete_keeps_invalid(self):
        path = self.write(["", "kein json", json.dumps(record())])
        self.assertEqual(events.delete_events(path, {"nope"}), 0)
        self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)

    def test_delete_cleans_up_on_error(self):
        path = self.write([json.dumps(record())])
        with mock.patch.object(
            events.os, "replace", side_effect=OSError("x")
        ), mock.patch.object(events.os, "unlink", side_effect=OSError("y")):
            with self.assertRaises(OSError):
                events.delete_events(path, {"nope"})
