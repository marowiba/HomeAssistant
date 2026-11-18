# pyright: basic
"""HAD-0006/HAD-0010: Integrationstest der gesamten Kette.

Der Test ersetzt Signal und Home Assistant durch lokale HTTP-Server und prueft
den Weg vom Ereignisstrom ueber Allowlist, Aktion und Antwort bis ins
Protokoll. Geprueft werden freigegebene und nicht freigegebene Absender, die
Kommandos, abweichende Schreibweise, mehrdeutige Nachricht, unbekannter
Zustand und Verbindungsfehler.
"""

from __future__ import annotations

import http.server
import json
import sys
import tempfile
import threading
import time
import unittest
from datetime import timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bridge  # noqa: E402
import command_parser  # noqa: E402

UUID_ALLOWED = "0929926d-1816-4157-9e5f-f57862547f66"
UUID_OTHER = "4081e291-bf9c-4bca-8eff-ab2466783e53"
NUMBER_ALLOWED = "+491700000001"
NUMBER_OTHER = "+491700000002"

REPLY_ON = "Eingeschaltet."


def envelope(number, uuid, text, timestamp):
    return {
        "sourceNumber": number,
        "sourceUuid": uuid,
        "sourceName": "Test",
        "timestamp": timestamp,
        "dataMessage": {"timestamp": timestamp, "message": text},
    }


EVENTS = [
    envelope(NUMBER_ALLOWED, UUID_ALLOWED, "HO M an", 1000),
    envelope(NUMBER_ALLOWED, UUID_ALLOWED, "ho m status", 2000),
    envelope(NUMBER_ALLOWED, UUID_ALLOWED, "HO M an aus", 3000),
    envelope(NUMBER_OTHER, UUID_OTHER, "HO M an", 4000),
]


class FakeHomeAssistant(http.server.BaseHTTPRequestHandler):
    """Beantwortet Ereignisstrom, Dienste, Statusabfrage und JSON-RPC."""

    calls: list[str] = []
    rpc_payloads: list[dict] = []

    def do_GET(self):
        if self.path.startswith("/api/v1/events"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for env in EVENTS:
                payload = json.dumps(
                    {"jsonrpc": "2.0", "method": "receive", "params": {"envelope": env}}
                )
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
            try:
                while True:
                    time.sleep(0.2)
            except Exception:
                return
        elif self.path.startswith("/api/states/"):
            if self.path.endswith("fehlt"):
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps({"state": "on"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        FakeHomeAssistant.calls.append(self.path)

        if self.path.startswith("/api/v1/rpc"):
            try:
                FakeHomeAssistant.rpc_payloads.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
            body = json.dumps(
                {"jsonrpc": "2.0", "id": 1, "result": {"results": [{"type": "SUCCESS"}]}}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(200)
            self.end_headers()

    def log_message(self, *args):
        pass


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        FakeHomeAssistant.calls = []
        FakeHomeAssistant.rpc_payloads = []
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeHomeAssistant)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.log_path = Path(self._tmp.name) / "messages.jsonl"

    def config(self, base_url=None, entity_id="switch.x"):
        return bridge.Config(
            events_url=f"http://127.0.0.1:{self.port}/api/v1/events",
            log_path=self.log_path,
            retention_days=30,
            timezone=timezone.utc,
            read_timeout=5,
            reconnect_delay=1,
            prune_interval=3600,
            allowlist=(
                bridge.AllowEntry(label="Matthias", number=NUMBER_ALLOWED, uuid=UUID_ALLOWED),
            ),
            home_assistant=bridge.HomeAssistantConfig(
                enabled=True,
                timeout=5,
                base_url=base_url or f"http://127.0.0.1:{self.port}",
                token="token",
            ),
            signal=bridge.SignalConfig(
                enabled=True,
                rpc_url=f"http://127.0.0.1:{self.port}/api/v1/rpc",
                timeout=5,
            ),
            commands=(
                command_parser.Command("on", "HO M an", "on", entity_id),
                command_parser.Command("off", "HO M aus", "off", entity_id),
                command_parser.Command("status", "HO M Status", "status", entity_id),
                command_parser.Command("help", "Hilfe", "help"),
                command_parser.Command("help_q", "?", "help"),
            ),
        )

    def run_bridge(self, config, expected=4, timeout=15):
        stop = threading.Event()
        worker = threading.Thread(target=bridge.run, args=(config, stop), daemon=True)
        worker.start()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.log_path.exists():
                lines = self.log_path.read_text(encoding="utf-8").splitlines()
                if len(lines) >= expected:
                    break
            time.sleep(0.1)

        stop.set()
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive(), "Bridge hat nicht zeitnah beendet")

        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
        ]

    def messages(self):
        return [
            payload["params"]["message"]
            for payload in FakeHomeAssistant.rpc_payloads
            if isinstance(payload.get("params"), dict)
        ]

    def test_full_chain(self):
        records = self.run_bridge(self.config())
        self.assertEqual(len(records), 4)

        allowed_on, allowed_status, ambiguous, blocked = records

        self.assertEqual(allowed_on["decision"], "allowed")
        self.assertEqual(allowed_on["command"], "on")
        self.assertTrue(allowed_on["actionable"])
        self.assertTrue(allowed_on["action"]["ok"])
        self.assertTrue(allowed_on["reply"]["ok"])

        self.assertEqual(allowed_status["command"], "status")
        self.assertEqual(allowed_status["action"]["detail"], "on")
        self.assertTrue(allowed_status["reply"]["ok"])

        self.assertIsNone(ambiguous["command"])
        self.assertFalse(ambiguous["actionable"])
        self.assertIsNone(ambiguous["action"])
        self.assertIsNone(ambiguous["reply"])

        self.assertEqual(blocked["decision"], "blocked")
        self.assertEqual(blocked["reason"], "not_in_allowlist")
        self.assertEqual(blocked["command"], "on")
        self.assertFalse(blocked["actionable"])
        self.assertIsNone(blocked["action"])
        self.assertIsNone(blocked["reply"])

    def test_reply_texts(self):
        self.run_bridge(self.config())
        self.assertEqual(self.messages(), [REPLY_ON, REPLY_ON])

    def test_blocked_sender_triggers_no_service_call(self):
        self.run_bridge(self.config())
        services = [
            call for call in FakeHomeAssistant.calls if call.startswith("/api/services/")
        ]
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0], "/api/services/switch/turn_on")

    def test_unknown_state_is_reported(self):
        records = self.run_bridge(self.config(entity_id="switch.fehlt"))
        status_record = records[1]
        self.assertEqual(status_record["command"], "status")
        self.assertFalse(status_record["action"]["ok"])
        self.assertEqual(status_record["action"]["detail"], "HTTP 404")
        self.assertTrue(status_record["reply"]["ok"])

        messages = self.messages()
        self.assertTrue(messages[1].startswith("Fehler:"), messages[1])

    def test_unreachable_home_assistant_is_reported(self):
        records = self.run_bridge(self.config(base_url="http://127.0.0.1:9"))
        on_record = records[0]
        self.assertFalse(on_record["action"]["ok"])
        self.assertIn("Verbindung fehlgeschlagen", on_record["action"]["detail"] or "")
        self.assertTrue(on_record["reply"]["ok"])

        self.assertEqual(
            self.messages()[0], "Fehler: Home Assistant ist nicht erreichbar."
        )


if __name__ == "__main__":
    unittest.main()
