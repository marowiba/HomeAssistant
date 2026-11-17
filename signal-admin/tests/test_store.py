# pyright: basic
import tempfile
import unittest
from pathlib import Path

from signal_admin.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "admin.db")

    def tearDown(self):
        self._tmp.cleanup()

    def test_users(self):
        self.store.create_user("admin", "hash", now=100)
        user = self.store.get_user("admin")
        assert user is not None
        self.assertEqual(user["password_hash"], "hash")
        self.assertEqual(user["created_at"], 100)
        self.assertIsNone(self.store.get_user("fehlt"))
        self.assertEqual([u["username"] for u in self.store.list_users()], ["admin"])
        self.store.set_password("admin", "neu")
        updated = self.store.get_user("admin")
        assert updated is not None
        self.assertEqual(updated["password_hash"], "neu")
        with self.assertRaises(KeyError):
            self.store.set_password("fehlt", "x")
        self.store.delete_user("admin")
        self.assertIsNone(self.store.get_user("admin"))

    def test_sessions(self):
        self.store.create_session("th", "admin", 200, now=100)
        session = self.store.get_session("th", now=150)
        assert session is not None
        self.assertEqual(session["username"], "admin")
        self.assertIsNone(self.store.get_session("fehlt", now=150))
        self.assertIsNone(self.store.get_session("th", now=200))
        self.assertIsNone(self.store.get_session("th", now=150))

    def test_purge_sessions(self):
        self.store.create_session("a", "admin", 100, now=50)
        self.store.create_session("b", "admin", 300, now=50)
        self.assertEqual(self.store.purge_expired_sessions(now=150), 1)
        self.assertIsNone(self.store.get_session("a", now=150))
        self.assertIsNotNone(self.store.get_session("b", now=150))

    def test_settings(self):
        self.assertIsNone(self.store.get_setting("x"))
        self.assertEqual(self.store.get_setting("x", "d"), "d")
        self.store.set_setting("x", "1")
        self.assertEqual(self.store.get_setting("x"), "1")
        self.store.set_setting("x", "2")
        self.assertEqual(self.store.get_setting("x"), "2")

    def test_audit(self):
        self.assertEqual(self.store.last_audit_hash(), "")
        entry_id = self.store.append_audit(1, "a", "act", "t", "d", "", "h1")
        self.assertEqual(entry_id, 1)
        self.assertEqual(self.store.last_audit_hash(), "h1")
        self.store.append_audit(2, "b", "act2", "t2", "d2", "h1", "h2")
        listed = self.store.list_audit()
        self.assertEqual([e["id"] for e in listed], [2, 1])
        ascending = self.store.all_audit_ascending()
        self.assertEqual([e["id"] for e in ascending], [1, 2])
