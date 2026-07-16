"""Сервис аккаунтов: регистрация, подтверждение e-mail, вход, сессии, сброс пароля.

Работает поверх app.database.Database (PostgreSQL). Возвращает готовые для
JSON-ответа словари; ошибки бросает как AuthError со статусом HTTP.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app import auth
from app.auth_repositories import (
    EmailVerificationRepository, PasswordResetRepository, SessionRepository, UserRepository,
)
from app.config import AppConfig
from app.services.email_service import send_code

PASSWORD_MIN_LEN = 8
CODE_TTL_MINUTES = 15
SESSION_TTL_MINUTES = 90 * 24 * 60
MAX_CODE_ATTEMPTS = 5
RESEND_MIN_INTERVAL_SECONDS = 60


class AuthError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def _user_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "nickname": user["nickname"],
        "email_verified": bool(user["email_verified"]),
        "order_source_label": user.get("order_source_label") or "Компания",
        "occupation": user.get("occupation"),
        "created_at": user["created_at"],
    }


def _seconds_since(iso_str: str | None) -> float:
    if not iso_str:
        return 1e9
    try:
        return (auth.now_utc() - datetime.fromisoformat(iso_str)).total_seconds()
    except ValueError:
        return 1e9


class AuthService:
    def __init__(self, connection: Any, config: AppConfig) -> None:
        self.config = config
        self.connection = connection
        self.users = UserRepository(connection)
        self.verifications = EmailVerificationRepository(connection)
        self.sessions = SessionRepository(connection)
        self.resets = PasswordResetRepository(connection)

    # ---- регистрация и подтверждение ----

    def register(self, email: str, password: str, nickname: str,
                 occupation: str | None = None, consent_version: str | None = None) -> dict[str, Any]:
        email = auth.normalize_email(email)
        nickname = (nickname or "").strip()
        if not auth.is_valid_email(email):
            raise AuthError("Некорректный e-mail")
        if len(password or "") < PASSWORD_MIN_LEN:
            raise AuthError(f"Пароль должен быть не короче {PASSWORD_MIN_LEN} символов")
        if not nickname:
            raise AuthError("Укажите ник")

        existing = self.users.get_by_email(email)
        if existing and existing["email_verified"]:
            raise AuthError("Этот e-mail уже зарегистрирован", status=409)

        if existing:
            # Незавершённая регистрация — обновляем и шлём новый код.
            self.users.set_password_hash(existing["id"], auth.hash_password(password))
            user_id = existing["id"]
        else:
            user_id = self.users.create(
                email=email, nickname=nickname,
                password_hash=auth.hash_password(password),
                occupation=occupation, consent_version=consent_version,
            )
        self._seed_user_settings(user_id)
        self._issue_email_code(user_id, email)
        return {"ok": True, "message": "Код подтверждения отправлен на почту"}

    def _seed_user_settings(self, user_id: int) -> None:
        # Настройки по умолчанию для нового пользователя (клиники/цены/авто/гео).
        # user_id берётся из app.user_id (RLS).
        from app.db import seed_default_settings

        self.connection.set_user(user_id)
        seed_default_settings(self.connection, self.config)

    def verify_email(self, email: str, code: str) -> dict[str, Any]:
        user = self._require_user(email)
        if user["email_verified"]:
            return {"ok": True, "message": "E-mail уже подтверждён"}
        record = self.verifications.latest_active(user["id"])
        self._check_code(record, code, self.verifications)
        self.verifications.consume(record["id"])
        self.users.mark_email_verified(user["id"])
        return {"ok": True, "message": "E-mail подтверждён"}

    def resend_code(self, email: str) -> dict[str, Any]:
        user = self.users.get_by_email(auth.normalize_email(email))
        # Анти-энумерация: одинаковый ответ независимо от существования аккаунта.
        if user and not user["email_verified"]:
            last = self.verifications.latest_active(user["id"])
            if last and _seconds_since(last["created_at"]) < RESEND_MIN_INTERVAL_SECONDS:
                raise AuthError("Код уже отправлен, попробуйте через минуту", status=429)
            self._issue_email_code(user["id"], user["email"])
        return {"ok": True, "message": "Если аккаунт не подтверждён, код отправлен повторно"}

    # ---- вход/выход ----

    def login(self, email: str, password: str) -> dict[str, Any]:
        user = self.users.get_by_email(auth.normalize_email(email))
        if not user or not auth.verify_password(password or "", user["password_hash"]):
            raise AuthError("Неверный e-mail или пароль", status=401)
        if user["status"] != "active":
            raise AuthError("Аккаунт заблокирован", status=403)
        if not user["email_verified"]:
            # Честный текст: при логине код НЕ отправляется (он ушёл при регистрации
            # и мог истечь) — человеку нужно запросить повторную отправку.
            raise AuthError("Подтвердите e-mail: запросите код повторно на экране подтверждения", status=403)
        token = auth.new_session_token()
        self.sessions.create(user["id"], auth.hash_secret(token), auth.in_minutes(SESSION_TTL_MINUTES))
        return {"ok": True, "token": token, "user": _user_payload(user)}

    def logout(self, token: str) -> dict[str, Any]:
        self.sessions.revoke(auth.hash_secret(token or ""))
        return {"ok": True}

    def authenticate(self, token: str | None) -> int | None:
        """Вернуть user_id по токену Bearer или None."""
        if not token:
            return None
        session = self.sessions.find_active(auth.hash_secret(token))
        if not session or auth.is_expired(session["expires_at"]):
            return None
        self.sessions.touch(session["id"])
        return int(session["user_id"])

    def me(self, user_id: int) -> dict[str, Any]:
        user = self.users.get(user_id)
        if not user:
            raise AuthError("Пользователь не найден", status=404)
        return {"ok": True, "user": _user_payload(user)}

    # ---- сброс пароля ----

    def forgot_password(self, email: str) -> dict[str, Any]:
        user = self.users.get_by_email(auth.normalize_email(email))
        if user:
            # Троттлинг МОЛЧАЛИВЫЙ (без 429): иначе разница ответов раскрывала бы,
            # что аккаунт существует. Без паузы можно было заваливать чужую почту
            # письмами сброса безостановочно.
            last = self.resets.latest_active(user["id"])
            if not last or _seconds_since(last["created_at"]) >= RESEND_MIN_INTERVAL_SECONDS:
                code = auth.new_numeric_code()
                self.resets.create(user["id"], auth.hash_secret(code), auth.in_minutes(CODE_TTL_MINUTES))
                send_code(self.config, user["email"], code, "сброса пароля")
        return {"ok": True, "message": "Если аккаунт существует, код для сброса отправлен"}

    def reset_password(self, email: str, code: str, new_password: str) -> dict[str, Any]:
        if len(new_password or "") < PASSWORD_MIN_LEN:
            raise AuthError(f"Пароль должен быть не короче {PASSWORD_MIN_LEN} символов")
        user = self._require_user(email)
        record = self.resets.latest_active(user["id"])
        self._check_code(record, code, self.resets)
        self.resets.consume(record["id"])
        self.users.set_password_hash(user["id"], auth.hash_password(new_password))
        self.sessions.revoke_all_for_user(user["id"])  # разлогин везде
        return {"ok": True, "message": "Пароль изменён"}

    def delete_account(self, user_id: int) -> dict[str, Any]:
        self.users.delete(user_id)  # каскадно удаляет коды/сессии/сбросы
        return {"ok": True, "message": "Аккаунт и данные удалены"}

    # ---- внутреннее ----

    def _issue_email_code(self, user_id: int, email: str) -> None:
        code = auth.new_numeric_code()
        self.verifications.create(user_id, auth.hash_secret(code), auth.in_minutes(CODE_TTL_MINUTES))
        send_code(self.config, email, code, "подтверждения e-mail")

    def _require_user(self, email: str) -> dict[str, Any]:
        user = self.users.get_by_email(auth.normalize_email(email))
        if not user:
            raise AuthError("Аккаунт не найден", status=404)
        return user

    def _check_code(self, record: dict[str, Any] | None, code: str, repo: Any) -> None:
        if not record:
            raise AuthError("Код не запрашивался или уже использован", status=400)
        if auth.is_expired(record["expires_at"]):
            raise AuthError("Срок действия кода истёк", status=400)
        if int(record["attempts"]) >= MAX_CODE_ATTEMPTS:
            raise AuthError("Слишком много попыток, запросите новый код", status=429)
        if not auth.code_matches((code or "").strip(), record["code_hash"]):
            repo.increment_attempts(record["id"])
            raise AuthError("Неверный код", status=400)
