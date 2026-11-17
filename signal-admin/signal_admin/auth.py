# pyright: basic
"""HAD-0008: Passwoerter, Sitzungs-Token, CSRF und Login-Rate-Limit."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

PBKDF2_ITERATIONS = 200_000
PBKDF2_PREFIX = "pbkdf2_sha256"
SESSION_TTL_SECONDS = 8 * 3600
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300


def hash_password(
    password: str,
    salt: str | None = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> str:
    """Erzeugt einen PBKDF2-Hash im Format prefix$iterations$salt$hash."""
    if not password:
        raise ValueError("Passwort darf nicht leer sein")
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_value.encode("utf-8"), iterations
    )
    return f"{PBKDF2_PREFIX}${iterations}${salt_value}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Prueft ein Passwort gegen einen gespeicherten Hash (zeitkonstant)."""
    try:
        prefix, iterations_text, salt_value, digest_hex = stored.split("$", 3)
        iterations = int(iterations_text)
    except (ValueError, AttributeError):
        return False
    if prefix != PBKDF2_PREFIX or iterations <= 0:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_value.encode("utf-8"), iterations
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_token(session_token: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"), session_token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_csrf(session_token: str, secret: str, token: str | None) -> bool:
    if not token:
        return False
    return hmac.compare_digest(csrf_token(session_token, secret), token)


class LoginRateLimiter:
    """Begrenzt fehlgeschlagene Anmeldeversuche je Schluessel (z. B. IP)."""

    def __init__(
        self,
        max_attempts: int = LOGIN_MAX_ATTEMPTS,
        window: int = LOGIN_WINDOW_SECONDS,
    ):
        self.max_attempts = max_attempts
        self.window = window
        self._attempts: dict[str, list[float]] = {}

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - self.window
        self._attempts[key] = [t for t in self._attempts.get(key, []) if t > cutoff]

    def is_blocked(self, key: str, now: float | None = None) -> bool:
        ts = now if now is not None else time.time()
        self._prune(key, ts)
        return len(self._attempts.get(key, [])) >= self.max_attempts

    def record_failure(self, key: str, now: float | None = None) -> None:
        ts = now if now is not None else time.time()
        self._prune(key, ts)
        self._attempts.setdefault(key, []).append(ts)

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)
