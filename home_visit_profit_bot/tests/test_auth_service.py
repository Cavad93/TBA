from __future__ import annotations

from pathlib import Path

import pytest

from app import auth
from app.config import (
    AppConfig, CarConfig, DefaultsConfig, FinanceConfig, GeoConfig,
    LocationApiConfig, RouteConfig, RoutingConfig,
)
from app.db import connect, init_db
from app.services import auth_service as auth_service_module
from app.services.auth_service import AuthError, AuthService


@pytest.fixture
def codes(monkeypatch):
    """Перехватываем отправку кода (в dev нет SMTP) — сохраняем последний код по e-mail."""
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        auth_service_module, "send_code",
        lambda config, to_email, code, purpose: captured.__setitem__(to_email, code),
    )
    return captured


def test_forgot_password_is_throttled_silently(fresh_db, monkeypatch) -> None:
    """Повторный запрос сброса в течение минуты не шлёт второе письмо.

    Троттлинг молчаливый: ответ одинаковый (не 429), иначе разница ответов
    раскрывала бы существование аккаунта. Без паузы чужую почту можно было
    заваливать письмами сброса безостановочно.
    """
    config = fresh_db
    sent: list[str] = []
    monkeypatch.setattr(
        auth_service_module, "send_code",
        lambda cfg, to_email, code, purpose: sent.append(code),
    )
    with connect(config) as connection:
        service = AuthService(connection, config)
        service.register("throttle@example.com", "supersecret", "Иван")
        service.verify_email("throttle@example.com", sent[-1])

        first = service.forgot_password("throttle@example.com")
        second = service.forgot_password("throttle@example.com")

    assert first == second  # ответы неразличимы
    # register + verify-код (1) + первый сброс (2); второй сброс письмо НЕ отправил.
    assert len(sent) == 2


def test_register_verify_login_me_flow(fresh_db, codes) -> None:
    config = fresh_db
    with connect(config) as connection:
        service = AuthService(connection, config)

        result = service.register("User@Example.com", "supersecret", "Иван", occupation="taxi")
        assert result["ok"] is True
        code = codes["user@example.com"]  # e-mail нормализован в нижний регистр

        # вход до подтверждения запрещён
        with pytest.raises(AuthError) as exc:
            service.login("user@example.com", "supersecret")
        assert exc.value.status == 403

        assert service.verify_email("user@example.com", code)["ok"] is True

        login = service.login("user@example.com", "supersecret")
        assert login["ok"] is True
        token = login["token"]
        assert login["user"]["email"] == "user@example.com"
        assert login["user"]["email_verified"] is True

        user_id = service.authenticate(token)
        assert user_id == login["user"]["id"]
        assert service.me(user_id)["user"]["nickname"] == "Иван"


def test_wrong_code_rejected_and_counts_attempts(fresh_db, codes) -> None:
    config = fresh_db
    with connect(config) as connection:
        service = AuthService(connection, config)
        service.register("a@b.com", "supersecret", "Ник")
        with pytest.raises(AuthError):
            service.verify_email("a@b.com", "000000")
        record = service.verifications.latest_active(1)
        assert record["attempts"] == 1


def test_short_password_and_bad_email_rejected(fresh_db, codes) -> None:
    config = fresh_db
    with connect(config) as connection:
        service = AuthService(connection, config)
        with pytest.raises(AuthError):
            service.register("a@b.com", "short", "Ник")
        with pytest.raises(AuthError):
            service.register("not-an-email", "supersecret", "Ник")


def test_duplicate_verified_email_rejected(fresh_db, codes) -> None:
    config = fresh_db
    with connect(config) as connection:
        service = AuthService(connection, config)
        service.register("dup@b.com", "supersecret", "Ник")
        service.verify_email("dup@b.com", codes["dup@b.com"])
        with pytest.raises(AuthError) as exc:
            service.register("dup@b.com", "supersecret", "Ник")
        assert exc.value.status == 409


def test_password_reset_revokes_sessions(fresh_db, codes) -> None:
    config = fresh_db
    with connect(config) as connection:
        service = AuthService(connection, config)
        service.register("r@b.com", "oldpassword", "Ник")
        service.verify_email("r@b.com", codes["r@b.com"])
        old_token = service.login("r@b.com", "oldpassword")["token"]

        service.forgot_password("r@b.com")
        reset_code = codes["r@b.com"]
        service.reset_password("r@b.com", reset_code, "newpassword")

        # старая сессия отозвана, старый пароль не работает, новый — работает
        assert service.authenticate(old_token) is None
        with pytest.raises(AuthError):
            service.login("r@b.com", "oldpassword")
        assert service.login("r@b.com", "newpassword")["ok"] is True


def test_logout_and_delete_account(fresh_db, codes) -> None:
    config = fresh_db
    with connect(config) as connection:
        service = AuthService(connection, config)
        service.register("d@b.com", "supersecret", "Ник")
        service.verify_email("d@b.com", codes["d@b.com"])
        token = service.login("d@b.com", "supersecret")["token"]

        service.logout(token)
        assert service.authenticate(token) is None

        token2 = service.login("d@b.com", "supersecret")["token"]
        user_id = service.authenticate(token2)
        service.delete_account(user_id)
        assert service.authenticate(token2) is None
        assert service.users.get_by_email("d@b.com") is None


def test_reset_and_verify_do_not_reveal_account_existence(fresh_db, codes) -> None:
    """Чужой e-mail и «код не запрашивался» должны быть НЕОТЛИЧИМЫ.

    forgot_password нарочно отвечает одинаково для любого адреса, но
    reset/verify с 404 «Аккаунт не найден» позволяли перечислять
    зарегистрированные e-mail разницей ответов — дыра закрыта.
    """
    config = fresh_db
    with connect(config) as connection:
        service = AuthService(connection, config)
        service.register("real@b.com", "supersecret", "Ник")
        service.verify_email("real@b.com", codes["real@b.com"])

        # знакомый e-mail, но код сброса не запрашивался
        with pytest.raises(AuthError) as known:
            service.reset_password("real@b.com", "000000", "newpassword")
        # незнакомый e-mail
        with pytest.raises(AuthError) as unknown:
            service.reset_password("ghost@b.com", "000000", "newpassword")

        assert known.value.status == unknown.value.status == 400
        assert known.value.message == unknown.value.message

        # та же пара для подтверждения e-mail
        with pytest.raises(AuthError) as verify_unknown:
            service.verify_email("ghost@b.com", "000000")
        assert verify_unknown.value.status == 400
        assert verify_unknown.value.message == known.value.message


def test_authenticate_rejects_garbage_token(fresh_db, codes) -> None:
    config = fresh_db
    with connect(config) as connection:
        service = AuthService(connection, config)
        assert service.authenticate(None) is None
        assert service.authenticate("nonsense") is None
