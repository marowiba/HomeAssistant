# pyright: basic
import unittest

from signal_admin import templates


class TemplateTests(unittest.TestCase):
    def test_login(self):
        self.assertIn("Anmeldung", templates.login_page())
        self.assertIn("falsch", templates.login_page("falsch", "admin"))

    def test_layout_with_user(self):
        html = templates.layout("Titel", "dashboard", "<p>x</p>", "admin", "csrf", "flash")
        self.assertIn("Abmelden", html)
        self.assertIn("flash", html)
        self.assertIn("/static/admin.js", html)

    def test_layout_without_user(self):
        html = templates.layout("Titel", "dashboard", "<p>x</p>")
        self.assertNotIn("Abmelden", html)

    def test_dashboard(self):
        html = templates.dashboard_page(
            [("A", 1)],
            [("signal", {"ok": True, "detail": "ok"})],
            [{"ts": "t", "sender_name": "M", "text": "x", "decision": "allowed"}],
            "admin",
            "csrf",
        )
        self.assertIn("Dashboard", html)
        self.assertIn("M", html)

    def test_dashboard_empty(self):
        html = templates.dashboard_page([], [], [], "admin", "csrf")
        self.assertIn("Keine Ereignisse", html)

    def test_allowlist(self):
        html = templates.allowlist_page(
            [{"label": "M", "number": "+49", "uuid": "u", "enabled": True}],
            "admin",
            "csrf",
        )
        self.assertIn("Allowlist", html)
        self.assertIn("M", html)
        self.assertIn("Löschen", html)

    def test_allowlist_empty(self):
        html = templates.allowlist_page([], "admin", "csrf", "fehler", True)
        self.assertIn("Keine Eintraege", html)
        self.assertIn("fehler", html)

    def test_commands(self):
        html = templates.commands_page(
            [
                {
                    "id": "on",
                    "text": "HO M an",
                    "action": "on",
                    "entity_id": "switch.x",
                    "enabled": True,
                },
                {
                    "id": "t",
                    "text": "HO T {wert}",
                    "action": "set_value",
                    "entity_id": "climate.x",
                    "min": 5.0,
                    "max": 30.0,
                    "unit": "°C",
                    "enabled": False,
                },
            ],
            "admin",
            "csrf",
        )
        self.assertIn("HO M an", html)
        self.assertIn("HO T {wert}", html)
        self.assertIn("5 bis 30 °C", html)
        self.assertIn("Löschen", html)

    def test_commands_empty(self):
        html = templates.commands_page([], "admin", "csrf")
        self.assertIn("Keine Kommandos", html)

    def test_commands_int_range(self):
        html = templates.commands_page(
            [
                {
                    "id": "t",
                    "text": "HO T {wert}",
                    "action": "set_value",
                    "entity_id": "climate.x",
                    "min": 5,
                    "max": 30,
                    "unit": "",
                    "enabled": True,
                }
            ],
            "admin",
            "csrf",
        )
        self.assertIn("5 bis 30", html)

    def test_events(self):
        html = templates.events_page(
            [
                {
                    "_id": "abc",
                    "ts": "t",
                    "sender_name": "M",
                    "text": "x",
                    "decision": "allowed",
                    "command": "on",
                }
            ],
            {
                "q": "x",
                "decision": "allowed",
                "command": "on",
                "from": "",
                "to": "",
                "sort": "ts",
                "dir": "desc",
            },
            [{"id": "on", "text": "HO M an"}],
            "ts",
            "desc",
            "admin",
            "csrf",
            1,
            2,
            30,
        )
        self.assertIn("Ereignislog", html)
        self.assertIn("Weiter", html)
        self.assertIn("data-select-all", html)
        self.assertIn("data-row-select", html)
        self.assertIn("data-select-scope", html)
        self.assertIn("data-select-all-field", html)
        self.assertIn("data-confirm-all", html)
        self.assertIn("sort=sender", html)
        self.assertIn("\u25bc", html)

    def test_events_empty(self):
        html = templates.events_page([], {}, [], "ts", "desc", "admin", "csrf", 1, 1, 0)
        self.assertIn("Keine Ereignisse", html)

    def test_events_sort_asc_indicator(self):
        html = templates.events_page(
            [],
            {"sort": "text", "dir": "asc"},
            [],
            "text",
            "asc",
            "admin",
            "csrf",
            1,
            1,
            0,
        )
        self.assertIn("\u25b2", html)
        self.assertIn("sort=text", html)

    def test_event_detail(self):
        html = templates.event_detail_page({"_id": "abc", "ts": "t"}, "admin", "csrf")
        self.assertIn("Ereignis-Detail", html)

    def test_audit_ok(self):
        html = templates.audit_page(
            [{"id": 1, "entry_hash": "abcdef"}], True, None, "admin", "csrf"
        )
        self.assertIn("Kette unversehrt", html)
        self.assertIn('class="audit"', html)

    def test_audit_broken(self):
        html = templates.audit_page([], False, 3, "admin", "csrf")
        self.assertIn("Kette gebrochen", html)
        self.assertIn("Noch keine Eintraege", html)

    def test_status(self):
        html = templates.status_page(
            [("signal", {"ok": False, "detail": "weg"})],
            [{"ts": "t", "sender_name": "M", "command": "on", "action": {}, "reply": {}}],
            "admin",
            "csrf",
        )
        self.assertIn("weg", html)

    def test_status_empty(self):
        html = templates.status_page([], [], "admin", "csrf")
        self.assertIn("Keine Fehler", html)

    def test_settings(self):
        html = templates.settings_page({"retention_days": 7}, "admin", "csrf")
        self.assertIn("Aufbewahrung", html)
        self.assertIn("7", html)

    def test_error(self):
        html = templates.error_page("kaputt", "admin", "csrf")
        self.assertIn("kaputt", html)
