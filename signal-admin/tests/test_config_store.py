# pyright: basic
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from signal_admin import config_store


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


class LoadSaveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_valid(self):
        path = self.tmp / "config.json"
        path.write_text(json.dumps(base_config()), encoding="utf-8")
        self.assertEqual(config_store.load_config(path)["retention_days"], 30)

    def test_load_missing(self):
        with self.assertRaises(config_store.ConfigError):
            config_store.load_config(self.tmp / "fehlt.json")

    def test_load_invalid_json(self):
        path = self.tmp / "config.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(config_store.ConfigError):
            config_store.load_config(path)

    def test_load_not_object(self):
        path = self.tmp / "config.json"
        path.write_text("[]", encoding="utf-8")
        with self.assertRaises(config_store.ConfigError):
            config_store.load_config(path)

    def test_save_and_reload(self):
        path = self.tmp / "config.json"
        config_store.save_config(path, base_config())
        self.assertEqual(config_store.load_config(path)["retention_days"], 30)

    def test_save_invalid(self):
        path = self.tmp / "config.json"
        with self.assertRaises(config_store.ConfigError):
            config_store.save_config(path, {"retention_days": 0})

    def test_save_cleans_up_on_error(self):
        path = self.tmp / "config.json"
        data = base_config()
        with mock.patch.object(
            config_store.os, "replace", side_effect=OSError("x")
        ), mock.patch.object(config_store.os, "unlink", side_effect=OSError("y")):
            with self.assertRaises(OSError):
                config_store.save_config(path, data)
        self.assertFalse(path.exists())

    def test_backup_and_restore(self):
        path = self.tmp / "config.json"
        config_store.save_config(path, base_config())
        raw = config_store.backup_bytes(base_config())
        restored = config_store.restore_config(path, raw)
        self.assertEqual(restored["retention_days"], 30)

    def test_restore_invalid_json(self):
        with self.assertRaises(config_store.ConfigError):
            config_store.restore_config(self.tmp / "config.json", b"{")

    def test_restore_invalid_utf8(self):
        with self.assertRaises(config_store.ConfigError):
            config_store.restore_config(self.tmp / "config.json", b"\xff\xfe")

    def test_restore_invalid_config(self):
        with self.assertRaises(config_store.ConfigError):
            config_store.restore_config(
                self.tmp / "config.json", b'{"retention_days": 0}'
            )


class ValidateTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(config_store.validate_config(base_config()), [])

    def test_not_object(self):
        self.assertEqual(
            config_store.validate_config([]),
            ["Konfiguration muss ein JSON-Objekt sein"],
        )

    def test_allowlist_not_list(self):
        data = base_config()
        data["allowlist"] = {}
        self.assertIn("allowlist muss eine Liste sein", config_store.validate_config(data))

    def test_entry_not_object(self):
        data = base_config()
        data["allowlist"] = [42]
        self.assertIn(
            "allowlist[0] muss ein Objekt sein", config_store.validate_config(data)
        )

    def test_entry_missing_label(self):
        data = base_config()
        data["allowlist"] = [{"uuid": "x"}]
        self.assertIn(
            "allowlist[0].label fehlt oder ist leer",
            config_store.validate_config(data),
        )

    def test_entry_number_not_text(self):
        data = base_config()
        data["allowlist"] = [{"label": "X", "number": 1}]
        self.assertIn(
            "allowlist[0].number muss Text sein", config_store.validate_config(data)
        )

    def test_entry_uuid_not_text(self):
        data = base_config()
        data["allowlist"] = [{"label": "X", "uuid": 1}]
        self.assertIn(
            "allowlist[0].uuid muss Text sein", config_store.validate_config(data)
        )

    def test_entry_without_identifier(self):
        data = base_config()
        data["allowlist"] = [{"label": "X"}]
        self.assertIn(
            "allowlist[0] braucht number oder uuid", config_store.validate_config(data)
        )

    def test_entry_enabled_not_bool(self):
        data = base_config()
        data["allowlist"] = [{"label": "X", "uuid": "u", "enabled": "yes"}]
        self.assertIn(
            "allowlist[0].enabled muss true oder false sein",
            config_store.validate_config(data),
        )

    def test_retention_invalid(self):
        for value in (0, -1, True, "30"):
            data = base_config()
            data["retention_days"] = value
            self.assertIn(
                "retention_days muss eine positive Ganzzahl sein",
                config_store.validate_config(data),
            )

    def test_commands_not_object(self):
        data = base_config()
        data["commands"] = []
        self.assertIn("commands muss ein Objekt sein", config_store.validate_config(data))

    def test_unknown_command(self):
        data = base_config()
        data["commands"] = {"foo": True}
        self.assertIn(
            "commands.foo ist kein festes Kommando", config_store.validate_config(data)
        )

    def test_command_not_bool(self):
        data = base_config()
        data["commands"] = {"on": "yes"}
        self.assertIn(
            "commands.on muss true oder false sein", config_store.validate_config(data)
        )

    def test_home_assistant_not_object(self):
        data = base_config()
        data["home_assistant"] = []
        self.assertIn(
            "home_assistant muss ein Objekt sein", config_store.validate_config(data)
        )

    def test_home_assistant_enabled_not_bool(self):
        data = base_config()
        data["home_assistant"] = {"enabled": "yes"}
        self.assertIn(
            "home_assistant.enabled muss true oder false sein",
            config_store.validate_config(data),
        )

    def test_actions_not_object(self):
        data = base_config()
        data["home_assistant"] = {"actions": []}
        self.assertIn(
            "home_assistant.actions muss ein Objekt sein",
            config_store.validate_config(data),
        )

    def test_action_invalid_url(self):
        data = base_config()
        data["home_assistant"] = {"actions": {"on": "ftp://x"}}
        self.assertIn(
            "home_assistant.actions.on muss eine http(s)-URL sein",
            config_store.validate_config(data),
        )

    def test_enabled_missing_actions(self):
        data = base_config()
        data["home_assistant"] = {"enabled": True, "actions": {"on": "http://x/a"}}
        self.assertIn(
            "home_assistant.actions fehlen: off", config_store.validate_config(data)
        )

    def test_status_not_object(self):
        data = base_config()
        data["home_assistant"] = {"status": []}
        self.assertIn(
            "home_assistant.status muss ein Objekt sein",
            config_store.validate_config(data),
        )

    def test_status_url_invalid(self):
        data = base_config()
        data["home_assistant"] = {"status": {"url": "ftp://x", "token": "t"}}
        self.assertIn(
            "home_assistant.status.url muss eine http(s)-URL sein",
            config_store.validate_config(data),
        )

    def test_status_token_missing(self):
        data = base_config()
        data["home_assistant"] = {"status": {"url": "http://x/a"}}
        self.assertIn(
            "home_assistant.status.token fehlt", config_store.validate_config(data)
        )

    def test_signal_not_object(self):
        data = base_config()
        data["signal"] = []
        self.assertIn("signal muss ein Objekt sein", config_store.validate_config(data))

    def test_signal_enabled_not_bool(self):
        data = base_config()
        data["signal"] = {"enabled": "yes"}
        self.assertIn(
            "signal.enabled muss true oder false sein",
            config_store.validate_config(data),
        )

    def test_signal_rpc_invalid(self):
        data = base_config()
        data["signal"] = {"rpc_url": "ftp://x"}
        self.assertIn(
            "signal.rpc_url muss eine http(s)-URL sein",
            config_store.validate_config(data),
        )


class MutationTests(unittest.TestCase):
    def test_add_entry(self):
        updated = config_store.add_allowlist_entry(
            base_config(), "Neu", "+491700000002", None
        )
        self.assertEqual(len(updated["allowlist"]), 2)
        self.assertEqual(updated["allowlist"][1]["label"], "Neu")

    def test_add_entry_with_uuid(self):
        updated = config_store.add_allowlist_entry(
            base_config(), "Neu", None, "uuid-b"
        )
        self.assertEqual(updated["allowlist"][1]["uuid"], "uuid-b")

    def test_add_entry_invalid(self):
        data = base_config()
        with self.assertRaises(config_store.ConfigError):
            config_store.add_allowlist_entry(data, "", None, None)

    def test_add_entry_allowlist_not_list(self):
        data = base_config()
        data["allowlist"] = {}
        with self.assertRaises(config_store.ConfigError):
            config_store.add_allowlist_entry(data, "X", "+49", None)

    def test_update_entry(self):
        updated = config_store.update_allowlist_entry(
            base_config(), 0, "Neu", "+49", "u", False
        )
        self.assertEqual(updated["allowlist"][0]["label"], "Neu")
        self.assertFalse(updated["allowlist"][0]["enabled"])

    def test_update_entry_invalid_index(self):
        data = base_config()
        with self.assertRaises(config_store.ConfigError):
            config_store.update_allowlist_entry(data, 5, "X", "+49", None, True)

    def test_update_entry_allowlist_not_list(self):
        data = base_config()
        data["allowlist"] = {}
        with self.assertRaises(config_store.ConfigError):
            config_store.update_allowlist_entry(data, 0, "X", "+49", None, True)

    def test_delete_entry(self):
        updated = config_store.delete_allowlist_entry(base_config(), 0)
        self.assertEqual(updated["allowlist"], [])

    def test_delete_entry_invalid_index(self):
        data = base_config()
        with self.assertRaises(config_store.ConfigError):
            config_store.delete_allowlist_entry(data, 5)

    def test_delete_entry_allowlist_not_list(self):
        data = base_config()
        data["allowlist"] = {}
        with self.assertRaises(config_store.ConfigError):
            config_store.delete_allowlist_entry(data, 0)

    def test_set_command_enabled(self):
        updated = config_store.set_command_enabled(base_config(), "on", False)
        self.assertFalse(updated["commands"]["on"])

    def test_set_command_unknown(self):
        data = base_config()
        with self.assertRaises(config_store.ConfigError):
            config_store.set_command_enabled(data, "foo", True)

    def test_set_command_commands_not_dict(self):
        data = base_config()
        data["commands"] = []
        with self.assertRaises(config_store.ConfigError):
            config_store.set_command_enabled(data, "on", True)

    def test_command_enabled(self):
        self.assertTrue(config_store.command_enabled(base_config(), "on"))
        data = base_config()
        data["commands"] = {"on": False}
        self.assertFalse(config_store.command_enabled(data, "on"))
        data["commands"] = []
        self.assertTrue(config_store.command_enabled(data, "on"))

    def test_set_retention(self):
        updated = config_store.set_retention(base_config(), 7)
        self.assertEqual(updated["retention_days"], 7)

    def test_set_retention_invalid(self):
        data = base_config()
        with self.assertRaises(config_store.ConfigError):
            config_store.set_retention(data, 0)
