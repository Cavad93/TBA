"""ОСАГО: отсчёт до конца полиса (Фаза 5)."""
from __future__ import annotations

from datetime import date

from app.database import connect
from app.repositories import SettingsRepository
from app.services.osago_service import osago_card


def _card(config, value, today):
    with connect(config) as conn:
        SettingsRepository(conn).set("osago_expires_at", value)
    with connect(config) as conn:
        return osago_card(SettingsRepository(conn), today=today)


def test_no_date_no_card(config):
    with connect(config) as conn:
        assert osago_card(SettingsRepository(conn), today=date(2026, 7, 15)) is None


def test_far_expiry_hidden(config):
    # До конца полиса 30 дней — карточку ещё не показываем.
    card = _card(config, "2026-08-14", date(2026, 7, 15))
    assert card is None


def test_within_14_days_shows(config):
    card = _card(config, "2026-07-25", date(2026, 7, 15))
    assert card is not None
    assert card["days_left"] == 10
    assert card["expired"] is False


def test_expired_policy(config):
    card = _card(config, "2026-07-10", date(2026, 7, 15))
    assert card is not None
    assert card["days_left"] == -5
    assert card["expired"] is True


def test_leap_year_boundary(config):
    # 29 февраля високосного 2028: разница дат считается корректно.
    card = _card(config, "2028-02-29", date(2028, 2, 20))
    assert card is not None
    assert card["days_left"] == 9


def test_exactly_14_days_shows(config):
    card = _card(config, "2026-07-29", date(2026, 7, 15))
    assert card is not None and card["days_left"] == 14


def test_broken_date_ignored(config):
    assert _card(config, "не дата", date(2026, 7, 15)) is None


# --- сохранение через настройки и появление в /api/home ---------------------

def test_saved_via_settings_and_read_back(config):
    from app.services.settings_service import SettingsService
    with connect(config) as conn:
        res = SettingsService(conn).update({"osago_expires_at": "2027-01-15"})
        assert "osago_expires_at" in res["updated"]
    with connect(config) as conn:
        assert SettingsRepository(conn).get("osago_expires_at") == "2027-01-15"


def test_human_date_format_accepted_by_settings(config):
    """«15.01.2027» — не кривая дата, а естественный ввод; хранится в ISO."""
    from app.services.settings_service import SettingsService
    with connect(config) as conn:
        res = SettingsService(conn).update({"osago_expires_at": "15.01.2027"})
        assert "osago_expires_at" in res["updated"]
        assert SettingsRepository(conn).get("osago_expires_at") == "2027-01-15"


def test_broken_date_goes_to_rejected(config):
    """Настоящий мусор не сохраняется и не роняет запрос — уходит в rejected."""
    from app.services.settings_service import SettingsService
    with connect(config) as conn:
        res = SettingsService(conn).update({"osago_expires_at": "не дата"})
        assert res["updated"] == []
        assert [item["key"] for item in res["rejected"]] == ["osago_expires_at"]
        assert SettingsRepository(conn).get("osago_expires_at") in (None, "")


def test_empty_allowed(config):
    from app.services.settings_service import SettingsService
    with connect(config) as conn:
        res = SettingsService(conn).update({"osago_expires_at": ""})
        assert "osago_expires_at" in res["updated"]


def test_home_snapshot_includes_osago(config):
    from app.services.home_service import HomeService
    with connect(config) as conn:
        SettingsRepository(conn).set("osago_expires_at",
                                     (date.today().replace(day=1)).isoformat())
    with connect(config) as conn:
        snap = HomeService(conn).snapshot("Тест")
    assert "osago" in snap
