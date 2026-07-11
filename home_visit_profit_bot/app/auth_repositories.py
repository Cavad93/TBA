"""Репозитории для аккаунтов: пользователи, коды подтверждения, сессии, сброс пароля.

Работают через слой app.database.Database (PostgreSQL). Строки читаются
по имени столбца (psycopg dict_row).
"""
from __future__ import annotations

from typing import Any

from app import auth


class UserRepository:
    def __init__(self, connection: Any):
        self.connection = connection

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM users WHERE email = ?", (auth.normalize_email(email),)
        ).fetchone()
        return dict(row) if row else None

    def get(self, user_id: int) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def create(self, email: str, nickname: str, password_hash: str, occupation: str | None,
               consent_version: str | None) -> int:
        now = auth.now_iso_utc()
        consent_at = now if consent_version else None
        return self.connection.insert(
            """
            INSERT INTO users(email, nickname, password_hash, email_verified, status,
                              occupation, consent_at, consent_version, created_at)
            VALUES (?, ?, ?, 0, 'active', ?, ?, ?, ?)
            """,
            (auth.normalize_email(email), nickname, password_hash, occupation,
             consent_at, consent_version, now),
        )

    def mark_email_verified(self, user_id: int) -> None:
        self.connection.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
        self.connection.commit()

    def set_password_hash(self, user_id: int, password_hash: str) -> None:
        self.connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
        )
        self.connection.commit()

    def delete(self, user_id: int) -> None:
        self.connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.connection.commit()


class EmailVerificationRepository:
    def __init__(self, connection: Any):
        self.connection = connection

    def create(self, user_id: int, code_hash: str, expires_at: str) -> None:
        self.connection.execute(
            """
            INSERT INTO email_verifications(user_id, code_hash, expires_at, attempts, created_at)
            VALUES (?, ?, ?, 0, ?)
            """,
            (user_id, code_hash, expires_at, auth.now_iso_utc()),
        )
        self.connection.commit()

    def latest_active(self, user_id: int) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT * FROM email_verifications
            WHERE user_id = ? AND consumed_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def increment_attempts(self, verification_id: int) -> None:
        self.connection.execute(
            "UPDATE email_verifications SET attempts = attempts + 1 WHERE id = ?", (verification_id,)
        )
        self.connection.commit()

    def consume(self, verification_id: int) -> None:
        self.connection.execute(
            "UPDATE email_verifications SET consumed_at = ? WHERE id = ?",
            (auth.now_iso_utc(), verification_id),
        )
        self.connection.commit()


class SessionRepository:
    def __init__(self, connection: Any):
        self.connection = connection

    def create(self, user_id: int, token_hash: str, expires_at: str) -> None:
        self.connection.execute(
            """
            INSERT INTO sessions(user_id, token_hash, created_at, last_used_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, token_hash, auth.now_iso_utc(), auth.now_iso_utc(), expires_at),
        )
        self.connection.commit()

    def find_active(self, token_hash: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM sessions WHERE token_hash = ? AND revoked_at IS NULL",
            (token_hash,),
        ).fetchone()
        return dict(row) if row else None

    def touch(self, session_id: int) -> None:
        self.connection.execute(
            "UPDATE sessions SET last_used_at = ? WHERE id = ?", (auth.now_iso_utc(), session_id)
        )
        self.connection.commit()

    def revoke(self, token_hash: str) -> None:
        self.connection.execute(
            "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (auth.now_iso_utc(), token_hash),
        )
        self.connection.commit()

    def revoke_all_for_user(self, user_id: int) -> None:
        self.connection.execute(
            "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (auth.now_iso_utc(), user_id),
        )
        self.connection.commit()


class PasswordResetRepository:
    def __init__(self, connection: Any):
        self.connection = connection

    def create(self, user_id: int, code_hash: str, expires_at: str) -> None:
        self.connection.execute(
            """
            INSERT INTO password_resets(user_id, code_hash, expires_at, attempts, created_at)
            VALUES (?, ?, ?, 0, ?)
            """,
            (user_id, code_hash, expires_at, auth.now_iso_utc()),
        )
        self.connection.commit()

    def latest_active(self, user_id: int) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT * FROM password_resets
            WHERE user_id = ? AND consumed_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def increment_attempts(self, reset_id: int) -> None:
        self.connection.execute(
            "UPDATE password_resets SET attempts = attempts + 1 WHERE id = ?", (reset_id,)
        )
        self.connection.commit()

    def consume(self, reset_id: int) -> None:
        self.connection.execute(
            "UPDATE password_resets SET consumed_at = ? WHERE id = ?",
            (auth.now_iso_utc(), reset_id),
        )
        self.connection.commit()
