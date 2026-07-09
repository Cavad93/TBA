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


def _config(tmp_path) -> AppConfig:
    return AppConfig(
        project_dir=tmp_path,
        database_path=tmp_path / "data.sqlite3",
        finance=FinanceConfig(min_hourly_income=600, currency="RUB"),
        car=CarConfig(car_cost_per_km=17.05, amortization_factor=0.8, fuel_price_per_liter=70, fuel_consumption_l_per_100km=10),
        defaults=DefaultsConfig(avg_speed_kmh=30, service_minutes=20, telemed_minutes=3, route_time_factor=1),
        route=RouteConfig(always_return_to_finish=True, optimize_after_each_accept=True),
        geo=GeoConfig(default_city="СПб", default_region="ЛО", base_districts=[], nominatim_url="", user_agent="test"),
        routing=RoutingConfig(osrm_url="", request_timeout_seconds=1, fallback_to_estimate=True, straight_line_factor=1.35),
        location_api=LocationApiConfig(enabled=True, host="127.0.0.1", port=8088, api_key="test", geofence_radius_m=120, dwell_minutes=12, notification_cooldown_minutes=60),
    )


@pytest.fixture
def codes(monkeypatch):
    """Перехватываем отправку кода (в dev нет SMTP) — сохраняем последний код по e-mail."""
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        auth_service_module, "send_code",
        lambda config, to_email, code, purpose: captured.__setitem__(to_email, code),
    )
    return captured


def test_register_verify_login_me_flow(tmp_path, codes) -> None:
    config = _config(tmp_path)
    init_db(config)
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


def test_wrong_code_rejected_and_counts_attempts(tmp_path, codes) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config) as connection:
        service = AuthService(connection, config)
        service.register("a@b.com", "supersecret", "Ник")
        with pytest.raises(AuthError):
            service.verify_email("a@b.com", "000000")
        record = service.verifications.latest_active(1)
        assert record["attempts"] == 1


def test_short_password_and_bad_email_rejected(tmp_path, codes) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config) as connection:
        service = AuthService(connection, config)
        with pytest.raises(AuthError):
            service.register("a@b.com", "short", "Ник")
        with pytest.raises(AuthError):
            service.register("not-an-email", "supersecret", "Ник")


def test_duplicate_verified_email_rejected(tmp_path, codes) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config) as connection:
        service = AuthService(connection, config)
        service.register("dup@b.com", "supersecret", "Ник")
        service.verify_email("dup@b.com", codes["dup@b.com"])
        with pytest.raises(AuthError) as exc:
            service.register("dup@b.com", "supersecret", "Ник")
        assert exc.value.status == 409


def test_password_reset_revokes_sessions(tmp_path, codes) -> None:
    config = _config(tmp_path)
    init_db(config)
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


def test_logout_and_delete_account(tmp_path, codes) -> None:
    config = _config(tmp_path)
    init_db(config)
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


def test_authenticate_rejects_garbage_token(tmp_path, codes) -> None:
    config = _config(tmp_path)
    init_db(config)
    with connect(config) as connection:
        service = AuthService(connection, config)
        assert service.authenticate(None) is None
        assert service.authenticate("nonsense") is None
