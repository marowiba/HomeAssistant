# pyright: basic
import subprocess
import unittest
import urllib.error
from email.message import Message
from unittest import mock

from signal_admin import status


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SignalTests(unittest.TestCase):
    def test_success(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", return_value=FakeResponse(b'{"result":{}}')
        ):
            self.assertTrue(status.check_signal("http://x")["ok"])

    def test_jsonrpc_error(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", return_value=FakeResponse(b'{"error":{}}')
        ):
            self.assertFalse(status.check_signal("http://x")["ok"])

    def test_invalid_json(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", return_value=FakeResponse(b"x")
        ):
            self.assertEqual(
                status.check_signal("http://x")["detail"],
                "Antwort ist kein gueltiges JSON",
            )

    def test_http_error(self):
        error = urllib.error.HTTPError("http://x", 500, "err", Message(), None)
        with mock.patch.object(status.urllib.request, "urlopen", side_effect=error):
            self.assertEqual(status.check_signal("http://x")["detail"], "HTTP 500")

    def test_url_error(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", side_effect=urllib.error.URLError("weg")
        ):
            self.assertIn(
                "Verbindung fehlgeschlagen", status.check_signal("http://x")["detail"]
            )

    def test_timeout(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", side_effect=TimeoutError()
        ):
            self.assertEqual(
                status.check_signal("http://x")["detail"], "Zeitueberschreitung"
            )

    def test_oserror(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", side_effect=OSError("kaputt")
        ):
            self.assertIn("Netzwerkfehler", status.check_signal("http://x")["detail"])

    def test_unknown_error(self):
        self.assertEqual(
            status._http_error_detail(Exception()), "Unbekannter Fehler"
        )


class HomeAssistantTests(unittest.TestCase):
    def test_not_configured(self):
        self.assertEqual(
            status.check_home_assistant(None, None)["detail"], "nicht konfiguriert"
        )

    def test_success(self):
        with mock.patch.object(
            status.urllib.request,
            "urlopen",
            return_value=FakeResponse(b'{"state":"on"}'),
        ):
            result = status.check_home_assistant("http://x", "t")
        self.assertTrue(result["ok"])
        self.assertEqual(result["detail"], "on")

    def test_invalid_json(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", return_value=FakeResponse(b"x")
        ):
            self.assertEqual(
                status.check_home_assistant("http://x", "t")["detail"],
                "Antwort ist kein gueltiges JSON",
            )

    def test_not_object(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", return_value=FakeResponse(b"[]")
        ):
            self.assertEqual(
                status.check_home_assistant("http://x", "t")["detail"],
                "Antwort ist kein Objekt",
            )

    def test_missing_state(self):
        with mock.patch.object(
            status.urllib.request, "urlopen", return_value=FakeResponse(b"{}")
        ):
            self.assertEqual(
                status.check_home_assistant("http://x", "t")["detail"], "kein Zustand"
            )

    def test_http_error(self):
        error = urllib.error.HTTPError("http://x", 401, "err", Message(), None)
        with mock.patch.object(status.urllib.request, "urlopen", side_effect=error):
            self.assertEqual(
                status.check_home_assistant("http://x", "t")["detail"], "HTTP 401"
            )


class ServiceTests(unittest.TestCase):
    def test_active(self):
        runner = mock.Mock(return_value=mock.Mock(stdout="active\n"))
        self.assertTrue(status.check_service("unit", runner)["ok"])

    def test_inactive(self):
        runner = mock.Mock(return_value=mock.Mock(stdout="inactive\n"))
        self.assertFalse(status.check_service("unit", runner)["ok"])

    def test_empty(self):
        runner = mock.Mock(return_value=mock.Mock(stdout=""))
        self.assertEqual(status.check_service("unit", runner)["detail"], "unbekannt")

    def test_oserror(self):
        runner = mock.Mock(side_effect=OSError("x"))
        self.assertIn(
            "Pruefung fehlgeschlagen", status.check_service("unit", runner)["detail"]
        )

    def test_subprocess_error(self):
        runner = mock.Mock(side_effect=subprocess.SubprocessError("x"))
        self.assertIn(
            "Pruefung fehlgeschlagen", status.check_service("unit", runner)["detail"]
        )


class RecentErrorsTests(unittest.TestCase):
    def test_action_failure(self):
        events = [{"action": {"attempted": True, "ok": False}, "reply": None}]
        self.assertEqual(len(status.recent_errors(events)), 1)

    def test_reply_failure(self):
        events = [{"action": None, "reply": {"attempted": True, "ok": False}}]
        self.assertEqual(len(status.recent_errors(events)), 1)

    def test_no_errors(self):
        events = [
            {
                "action": {"attempted": True, "ok": True},
                "reply": {"attempted": True, "ok": True},
            }
        ]
        self.assertEqual(status.recent_errors(events), [])

    def test_limit(self):
        events = [{"action": {"attempted": True, "ok": False}} for _ in range(5)]
        self.assertEqual(len(status.recent_errors(events, limit=2)), 2)
