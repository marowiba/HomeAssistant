# pyright: basic
import tempfile
import unittest
from pathlib import Path

from signal_admin.audit import AuditLog
from signal_admin.store import Store


class AuditTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "admin.db")
        self.audit = AuditLog(self.store)

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_and_verify(self):
        first = self.audit.append("admin", "login", "session", now=100)
        second = self.audit.append("admin", "allowlist.add", "Matthias", "ok", now=101)
        self.assertEqual(first["prev_hash"], "")
        self.assertEqual(second["prev_hash"], first["entry_hash"])
        ok, bad = self.audit.verify()
        self.assertTrue(ok)
        self.assertIsNone(bad)
        self.assertEqual(len(self.audit.list()), 2)

    def test_tamper_detected(self):
        self.audit.append("admin", "login", "session", now=100)
        self.audit.append("admin", "login", "session", now=101)
        with self.store._db() as conn:
            conn.execute("UPDATE audit SET detail='manipuliert' WHERE id=1")
        ok, bad = self.audit.verify()
        self.assertFalse(ok)
        self.assertEqual(bad, 1)
