"""Криптографические и вспомогательные функции авторизации.

Пароли хранятся как PBKDF2-HMAC-SHA256 (stdlib, без внешних зависимостей),
токены сессий и коды подтверждения — только в виде SHA-256 хеша, поэтому утечка
БД не раскрывает ни паролей, ни действующих токенов/кодов.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

_PBKDF2_ITERATIONS = 200_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---- время (UTC, ISO-строки для колонок TEXT) ----

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def now_iso_utc() -> str:
    return iso(now_utc())


def in_minutes(minutes: int) -> str:
    return iso(now_utc() + timedelta(minutes=minutes))


def is_expired(expires_at: str | None) -> bool:
    if not expires_at:
        return True
    try:
        return now_utc() > datetime.fromisoformat(expires_at)
    except ValueError:
        return True


# ---- пароли ----

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        _PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(dk).decode("ascii"),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


# ---- токены и коды ----

def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def new_numeric_code(digits: int = 6) -> str:
    return f"{secrets.randbelow(10 ** digits):0{digits}d}"


def hash_secret(value: str) -> str:
    """SHA-256 для хранения токенов/кодов (высокоэнтропийных или коротко живущих)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def code_matches(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_secret(code), code_hash)


# ---- нормализация/валидация ----

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email or ""))
