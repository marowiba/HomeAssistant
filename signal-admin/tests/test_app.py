# pyright: basic
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlencode

from signal_admin import app as app_module
from signal_admin import auth, config_store
from signal_admin.app import AdminApp, _RequestHandler
from signal_admin.events import event_id as compute_event_id


def base_config():
    return {
        "events_url": "http://127.0.0.1:8080/api/v1/events",
        "log_path": "/tmp/messages.jsonl",
        "retention_days": 30,
        "timezone": "UTC",
        "allowlist": [
            {
                "label": "Matthias",
                "number": "+491700000001",
                "uuid": "uuid-a",
                "enabled": True,
            }
        ],
        "signal": {"enabled": True, "rpc_url": "http://127.0.0.1:8080/api/v1/rpc"},
        "home_assistant": {
            "enabled": False,
            "actions": {"on": "http://127.0.0.1/a", "off": "http://127.0.0.1/b"},
        },
    }


def event(**overrides):
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
        "action": {"attempted": True, "ok": True, "detail": None},
        "reply": {"attempted": True, "ok": True, "detail": None},
    }
    data.update(overrides)
    return data


class AppTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.config_path = self.tmp / "config.json"
        self.config_path.write_text(json.dumps(base_config()), encoding="utf-8")
        self.log_path = self.tmp / "messages.jsonl"
        self.log_path.write_text(json.dumps(event()) + "\n", encoding="utf-8")
        self.db_path = self.tmp / "admin.db"
        self.app = AdminApp(
            self.config_path,
            self.log_path,
            self.db_path,
            "secret",
            now=lambda: 1000.0,
        )
        self.app.store.create_user("admin", auth.hash_password("pw", iterations=1000))
        self.token = "session-token"
        self.app.store.create_session(
            auth.hash_token(self.token), "admin", 999999, now=1000.0
        )
        self.cookie = {"Cookie": f"signal_admin_session={self.token}"}
        self.csrf = auth.csrf_token(self.token, "secret")

    def tearDown(self):
        self._tmp.cleanup()

    def get(self, path, headers=None):
        return self.app.handle("GET", path, headers or self.cookie)

    def post(self, path, form, headers=None):
        body = urlencode(form, doseq=True)
        hdrs = dict(headers or self.cookie)
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        return self.app.handle("POST", path, hdrs, body.encode("utf-8"))


class AuthFlowTests(AppTestBase):
    def test_login_page(self):
        self.assertEqual(self.app.handle("GET", "/login", {}).status, 200)

    def test_login_wrong(self):
        response = self.app.handle(
            "POST",
            "/login",
            {"Content-Type": "application/x-www-form-urlencoded"},
            b"username=admin&password=falsch",
        )
        self.assertEqual(response.status, 401)

    def test_login_unknown_user(self):
        response = self.app.handle(
            "POST",
            "/login",
            {"Content-Type": "application/x-www-form-urlencoded"},
            b"username=fehlt&password=x",
        )
        self.assertEqual(response.status, 401)

    def test_login_success(self):
        response = self.app.handle(
            "POST",
            "/login",
            {"Content-Type": "application/x-www-form-urlencoded"},
            b"username=admin&password=pw",
        )
        self.assertEqual(response.status, 303)
        self.assertIn("Set-Cookie", response.headers)

    def test_login_rate_limited(self):
        for _ in range(5):
            self.app.handle(
                "POST",
                "/login",
                {"Content-Type": "application/x-www-form-urlencoded"},
                b"username=admin&password=falsch",
            )
        response = self.app.handle(
            "POST",
            "/login",
            {"Content-Type": "application/x-www-form-urlencoded"},
            b"username=admin&password=pw",
        )
        self.assertEqual(response.status, 429)

    def test_login_method_not_allowed(self):
        self.assertEqual(self.app.handle("PUT", "/login", {}).status, 405)

    def test_requires_session_get(self):
        response = self.app.handle("GET", "/dashboard", {})
        self.assertEqual(response.status, 303)
        self.assertEqual(response.headers["Location"], "/login")

    def test_requires_session_post(self):
        self.assertEqual(self.app.handle("POST", "/allowlist/add", {}, b"").status, 403)

    def test_invalid_cookie(self):
        self.assertEqual(
            self.app.handle("GET", "/dashboard", {"Cookie": "kaputt"}).status, 303
        )

    def test_malformed_cookie(self):
        with mock.patch.object(
            app_module.SimpleCookie, "load", side_effect=Exception("x")
        ):
            self.assertEqual(
                self.app.handle("GET", "/dashboard", {"Cookie": "x"}).status, 303
            )

    def test_expired_session(self):
        self.app.store.create_session(auth.hash_token("old"), "admin", 500, now=1000.0)
        response = self.app.handle(
            "GET", "/dashboard", {"Cookie": "signal_admin_session=old"}
        )
        self.assertEqual(response.status, 303)

    def test_logout(self):
        response = self.post("/logout", {"csrf": self.csrf})
        self.assertEqual(response.status, 303)
        self.assertIsNone(
            self.app.store.get_session(auth.hash_token(self.token), now=1000.0)
        )


class PageTests(AppTestBase):
    def test_root_redirect(self):
        response = self.get("/")
        self.assertEqual(response.status, 303)
        self.assertEqual(response.headers["Location"], "/dashboard")

    def test_dashboard(self):
        response = self.get("/dashboard")
        self.assertEqual(response.status, 200)
        self.assertIn(b"Dashboard", response.body)

    def test_dashboard_without_sections(self):
        self.config_path.write_text(json.dumps({"retention_days": 30}), encoding="utf-8")
        self.assertEqual(self.get("/dashboard").status, 200)

    def test_allowlist(self):
        response = self.get("/allowlist")
        self.assertEqual(response.status, 200)
        self.assertIn(b"Matthias", response.body)

    def test_allowlist_not_list(self):
        self.config_path.write_text(json.dumps({"allowlist": {}}), encoding="utf-8")
        self.assertEqual(self.get("/allowlist").status, 200)

    def test_commands(self):
        response = self.get("/commands")
        self.assertEqual(response.status, 200)
        self.assertIn(b"HO M an", response.body)

    def test_events(self):
        response = self.get("/events?q=HO&decision=allowed&command=on&page=1")
        self.assertEqual(response.status, 200)

    def test_events_invalid_page(self):
        self.assertEqual(self.get("/events?page=abc").status, 200)

    def test_events_page_too_high(self):
        self.assertEqual(self.get("/events?page=99").status, 200)

    def test_event_detail(self):
        record = json.loads(self.log_path.read_text(encoding="utf-8").splitlines()[0])
        response = self.get(f"/events/detail?id={compute_event_id(record)}")
        self.assertEqual(response.status, 200)

    def test_event_detail_missing(self):
        self.assertEqual(self.get("/events/detail?id=fehlt").status, 404)

    def test_audit(self):
        self.assertEqual(self.get("/audit").status, 200)

    def test_status(self):
        self.assertEqual(self.get("/status").status, 200)

    def test_settings(self):
        self.assertEqual(self.get("/settings").status, 200)

    def test_backup(self):
        response = self.get("/backup")
        self.assertEqual(response.status, 200)
        self.assertIn("attachment", response.headers["Content-Disposition"])

    def test_not_found(self):
        self.assertEqual(self.get("/gibtsnicht").status, 404)

    def test_post_not_found(self):
        self.assertEqual(self.post("/gibtsnicht", {"csrf": self.csrf}).status, 404)

    def test_method_not_allowed_route(self):
        self.assertEqual(
            self.app.handle("PUT", "/dashboard", self.cookie).status, 404
        )

    def test_static_css(self):
        response = self.get("/static/admin.css")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers["Content-Type"], "text/css; charset=utf-8")

    def test_static_missing(self):
        self.assertEqual(self.get("/static/fehlt.css").status, 404)

    def test_static_traversal(self):
        self.assertEqual(self.get("/static/../app.py").status, 404)

    def test_static_dotfile(self):
        self.assertEqual(self.get("/static/.hidden").status, 404)

    def test_static_other_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "x.txt").write_text("hi", encoding="utf-8")
            with mock.patch.object(app_module, "STATIC_DIR", Path(tmp)):
                response = self.get("/static/x.txt")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers["Content-Type"], "application/octet-stream")


class MutationTests(AppTestBase):
    def test_allowlist_add(self):
        response = self.post(
            "/allowlist/add",
            {"csrf": self.csrf, "label": "Neu", "number": "+491700000002", "enabled": "1"},
        )
        self.assertEqual(response.status, 303)
        self.assertEqual(
            len(config_store.load_config(self.config_path)["allowlist"]), 2
        )

    def test_allowlist_add_invalid(self):
        response = self.post("/allowlist/add", {"csrf": self.csrf, "label": ""})
        self.assertEqual(response.status, 200)
        self.assertIn(b"label", response.body)

    def test_allowlist_update(self):
        response = self.post(
            "/allowlist/update",
            {
                "csrf": self.csrf,
                "index": "0",
                "label": "Neu",
                "number": "+49",
                "uuid": "u",
                "enabled": "1",
            },
        )
        self.assertEqual(response.status, 303)

    def test_allowlist_update_invalid_index(self):
        response = self.post(
            "/allowlist/update",
            {"csrf": self.csrf, "index": "9", "label": "X", "number": "+49"},
        )
        self.assertEqual(response.status, 200)

    def test_allowlist_update_bad_index(self):
        response = self.post(
            "/allowlist/update", {"csrf": self.csrf, "index": "abc", "label": "X"}
        )
        self.assertEqual(response.status, 200)

    def test_allowlist_delete(self):
        response = self.post("/allowlist/delete", {"csrf": self.csrf, "index": "0"})
        self.assertEqual(response.status, 303)

    def test_allowlist_delete_invalid(self):
        response = self.post("/allowlist/delete", {"csrf": self.csrf, "index": "9"})
        self.assertEqual(response.status, 200)

    def test_allowlist_delete_bad_index(self):
        response = self.post("/allowlist/delete", {"csrf": self.csrf, "index": "abc"})
        self.assertEqual(response.status, 200)

    def test_commands_toggle(self):
        response = self.post(
            "/commands/toggle", {"csrf": self.csrf, "command": "on", "enabled": "0"}
        )
        self.assertEqual(response.status, 303)
        self.assertFalse(config_store.load_config(self.config_path)["commands"]["on"])

    def test_commands_toggle_invalid(self):
        response = self.post(
            "/commands/toggle", {"csrf": self.csrf, "command": "foo", "enabled": "1"}
        )
        self.assertEqual(response.status, 200)

    def test_events_delete_none(self):
        self.assertEqual(self.post("/events/delete", {"csrf": self.csrf}).status, 200)

    def test_events_delete(self):
        record = json.loads(self.log_path.read_text(encoding="utf-8").splitlines()[0])
        response = self.post(
            "/events/delete", {"csrf": self.csrf, "ids": [compute_event_id(record)]}
        )
        self.assertEqual(response.status, 200)
        self.assertEqual(self.log_path.read_text(encoding="utf-8").strip(), "")

    def test_settings_retention(self):
        response = self.post("/settings/retention", {"csrf": self.csrf, "days": "7"})
        self.assertEqual(response.status, 200)
        self.assertEqual(
            config_store.load_config(self.config_path)["retention_days"], 7
        )

    def test_settings_retention_invalid(self):
        response = self.post("/settings/retention", {"csrf": self.csrf, "days": "0"})
        self.assertEqual(response.status, 200)

    def test_settings_retention_bad(self):
        response = self.post("/settings/retention", {"csrf": self.csrf, "days": "abc"})
        self.assertEqual(response.status, 200)

    def test_settings_cleanup(self):
        self.assertEqual(self.post("/settings/cleanup", {"csrf": self.csrf}).status, 200)

    def test_restore(self):
        response = self.post(
            "/restore", {"csrf": self.csrf, "backup": json.dumps(base_config())}
        )
        self.assertEqual(response.status, 200)

    def test_restore_invalid(self):
        response = self.post("/restore", {"csrf": self.csrf, "backup": "{"})
        self.assertEqual(response.status, 200)

    def test_csrf_invalid(self):
        response = self.post(
            "/allowlist/add", {"csrf": "falsch", "label": "X"}
        )
        self.assertEqual(response.status, 403)


class ClientKeyTests(AppTestBase):
    def test_forwarded(self):
        self.assertEqual(
            AdminApp._client_key({"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}), "1.2.3.4"
        )

    def test_real_ip(self):
        self.assertEqual(AdminApp._client_key({"X-Real-IP": "9.9.9.9"}), "9.9.9.9")

    def test_default(self):
        self.assertEqual(AdminApp._client_key({}), "local")

    def test_statuses_overrides(self):
        app = AdminApp(
            self.config_path,
            self.log_path,
            self.db_path,
            "secret",
            signal_rpc_url="http://x",
            ha_status_url="http://y",
            ha_status_token="t",
            now=lambda: 1000.0,
        )
        with mock.patch.object(
            app_module.status_mod, "check_signal", return_value={"ok": True, "detail": "x"}
        ), mock.patch.object(
            app_module.status_mod,
            "check_home_assistant",
            return_value={"ok": True, "detail": "y"},
        ), mock.patch.object(
            app_module.status_mod,
            "check_service",
            return_value={"ok": True, "detail": "z"},
        ):
            self.assertEqual(len(app._statuses({})), 3)


class ServeMainTests(AppTestBase):
    def test_serve(self):
        fake_server = mock.MagicMock()
        with mock.patch.object(
            app_module, "_AdminServer", return_value=fake_server
        ):
            app_module.serve(self.app, "127.0.0.1", 0)
        fake_server.serve_forever.assert_called_once()
        fake_server.server_close.assert_called_once()

    def test_main_missing_secret(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            code = app_module.main(
                [
                    "--config",
                    str(self.config_path),
                    "--log",
                    str(self.log_path),
                    "--db",
                    str(self.db_path),
                ]
            )
        self.assertEqual(code, 2)

    def test_main_create_user(self):
        env = {"SIGNAL_ADMIN_SECRET": "s", "SIGNAL_ADMIN_PASSWORD": "pw"}
        with mock.patch.dict("os.environ", env, clear=True):
            code = app_module.main(
                [
                    "--config",
                    str(self.config_path),
                    "--log",
                    str(self.log_path),
                    "--db",
                    str(self.db_path),
                    "--create-user",
                    "neu",
                ]
            )
        self.assertEqual(code, 0)
        self.assertIsNotNone(self.app.store.get_user("neu"))

    def test_main_serve(self):
        env = {"SIGNAL_ADMIN_SECRET": "s"}
        with mock.patch.dict("os.environ", env, clear=True), mock.patch.object(
            app_module, "serve"
        ) as fake_serve:
            code = app_module.main(
                [
                    "--config",
                    str(self.config_path),
                    "--log",
                    str(self.log_path),
                    "--db",
                    str(self.db_path),
                ]
            )
        self.assertEqual(code, 0)
        fake_serve.assert_called_once()


class HttpHandlerTests(AppTestBase):
    def test_http_roundtrip(self):
        handler = type("H", (_RequestHandler,), {"app": self.app})
        server = app_module._AdminServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/login")
            response = conn.getresponse()
            response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("X-Frame-Options"), "DENY")
            conn.request(
                "POST",
                "/login",
                body="username=admin&password=pw",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = conn.getresponse()
            response.read()
            self.assertEqual(response.status, 303)
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
