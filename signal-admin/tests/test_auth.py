# pyright: basic
import unittest

from signal_admin import auth


class PasswordTests(unittest.TestCase):
    def test_hash_and_verify(self):
        stored = auth.hash_password("geheim", salt="abc", iterations=1000)
        self.assertTrue(stored.startswith("pbkdf2_sha256$1000$abc$"))
        self.assertTrue(auth.verify_password("geheim", stored))
        self.assertFalse(auth.verify_password("falsch", stored))

    def test_hash_generates_salt(self):
        first = auth.hash_password("geheim", iterations=1000)
        second = auth.hash_password("geheim", iterations=1000)
        self.assertNotEqual(first, second)

    def test_empty_password_rejected(self):
        with self.assertRaises(ValueError):
            auth.hash_password("")

    def test_verify_malformed(self):
        self.assertFalse(auth.verify_password("x", "kein-format"))
        self.assertFalse(auth.verify_password("x", "md5$1$a$b"))
        self.assertFalse(auth.verify_password("x", "pbkdf2_sha256$0$a$b"))
        self.assertFalse(auth.verify_password("x", "pbkdf2_sha256$abc$a$b"))
        self.assertFalse(auth.verify_password("x", None))  # type: ignore[arg-type]


class TokenTests(unittest.TestCase):
    def test_new_token_unique(self):
        first = auth.new_session_token()
        second = auth.new_session_token()
        self.assertNotEqual(first, second)

    def test_hash_token_stable(self):
        first = auth.hash_token("abc")
        second = auth.hash_token("abc")
        self.assertEqual(first, second)
        self.assertNotEqual(auth.hash_token("abc"), auth.hash_token("abd"))

    def test_csrf(self):
        token = auth.csrf_token("session", "secret")
        self.assertTrue(auth.verify_csrf("session", "secret", token))
        self.assertFalse(auth.verify_csrf("session", "secret", "falsch"))
        self.assertFalse(auth.verify_csrf("session", "secret", None))
        self.assertFalse(auth.verify_csrf("andere", "secret", token))


class RateLimiterTests(unittest.TestCase):
    def test_blocks_after_max(self):
        limiter = auth.LoginRateLimiter(max_attempts=2, window=60)
        self.assertFalse(limiter.is_blocked("ip", now=100))
        limiter.record_failure("ip", now=100)
        self.assertFalse(limiter.is_blocked("ip", now=100))
        limiter.record_failure("ip", now=101)
        self.assertTrue(limiter.is_blocked("ip", now=101))

    def test_window_expires(self):
        limiter = auth.LoginRateLimiter(max_attempts=1, window=10)
        limiter.record_failure("ip", now=100)
        self.assertTrue(limiter.is_blocked("ip", now=105))
        self.assertFalse(limiter.is_blocked("ip", now=111))

    def test_reset(self):
        limiter = auth.LoginRateLimiter(max_attempts=1, window=10)
        limiter.record_failure("ip", now=100)
        limiter.reset("ip")
        self.assertFalse(limiter.is_blocked("ip", now=100))

    def test_default_now(self):
        limiter = auth.LoginRateLimiter(max_attempts=1, window=10)
        limiter.record_failure("ip")
        self.assertTrue(limiter.is_blocked("ip"))
