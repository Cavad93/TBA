from __future__ import annotations

from app.config import (
    AppConfig,
    CarConfig,
    DefaultsConfig,
    FinanceConfig,
    GeoConfig,
    LocationApiConfig,
    RouteConfig,
    RoutingConfig,
)
from app.db import connect, init_db
from app.services.mobile_api_service import MobileApiService
from app.services.settings_service import (
    SettingsService,
    allowed_clinics,
    allowed_telemed_clinics,
)
from app.repositories import SettingsRepository
from app.services.base_zones_service import parse_base_zones


# Клиники сеедятся init_db из config.geo (дефолт config.py).
SEEDED_CLINICS = ["Династия", "ПСК", "ВИТАМЕД", "ДНД"]
SEEDED_TELEMED_CLINICS = ["ПСК", "ДНД"]




def _field(result: dict, key: str) -> dict:
    for section in result["sections"]:
        for field in section["fields"]:
            if field["key"] == key:
                return field
    raise AssertionError(f"field {key} not found")


def test_read_returns_defaults_on_empty_db(config) -> None:
    with connect(config) as connection:
        result = SettingsService(connection).read()

    assert result["ok"] is True
    assert _field(result, "min_hourly_income")["value"] == 600
    assert _field(result, "workload_tracking_enabled")["value"] is True
    # clinics/telemed_clinics сеедятся init_db из config.geo
    assert _field(result, "clinics")["value"] == SEEDED_CLINICS
    # Зоны обслуживания пользователь задаёт сам — никаких зашитых районов.
    assert _field(result, "base_zones")["value"] == "[]"
    # Каждое поле объясняет себя одним предложением.
    assert _field(result, "min_hourly_income")["hint"]
    # Технические параметры (OSRM, коэффициенты, запасной расчёт) пользователю не показываем.
    keys = {field["key"] for section in result["sections"] for field in section["fields"]}
    assert "osrm_url" not in keys
    assert "routing_fallback_to_estimate" not in keys
    assert "straight_line_factor" not in keys
    # Стоимость километра выводится из цены литра и расхода, а не спрашивается отдельно.
    assert "car_cost_per_km" not in keys
    assert "home_address" not in keys


def test_update_writes_all_types_and_reads_back(config) -> None:
    with connect(config) as connection:
        service = SettingsService(connection)
        result = service.update(
            {
                "min_hourly_income": 750,
                "fuel_price_per_liter": 62.5,
                "workload_tracking_enabled": False,
                "default_start_address": "  Мой дом  ",
                "base_zones": [
                    {"region": "Ленинградская область", "city": "Санкт-Петербург", "districts": ["Приморский"]},
                    {"region": "Московская область", "city": "Москва", "districts": ["Ленинский", "Советский"]},
                ],
                "clinics": "ПСК, ДНД, Династия",
            }
        )

    assert set(result["updated"]) == {
        "min_hourly_income",
        "fuel_price_per_liter",
        "workload_tracking_enabled",
        "default_start_address",
        "base_zones",
        "clinics",
    }
    assert _field(result, "min_hourly_income")["value"] == 750
    assert _field(result, "fuel_price_per_liter")["value"] == 62.5
    assert _field(result, "workload_tracking_enabled")["value"] is False
    assert _field(result, "default_start_address")["value"] == "Мой дом"
    assert _field(result, "clinics")["value"] == ["ПСК", "ДНД", "Династия"]

    zones = parse_base_zones(_field(result, "base_zones")["value"])
    assert [zone.city for zone in zones] == ["Санкт-Петербург", "Москва"]
    assert zones[1].districts == ("Ленинский", "Советский")


def test_update_accepts_values_wrapper_and_ignores_unknown(config) -> None:
    with connect(config) as connection:
        result = SettingsService(connection).update(
            {"values": {"fuel_price_per_liter": 72, "totally_unknown": 5}}
        )

    assert result["updated"] == ["fuel_price_per_liter"]
    assert result["ignored"] == ["totally_unknown"]
    assert _field(result, "fuel_price_per_liter")["value"] == 72


def test_start_and_finish_may_stay_empty(config) -> None:
    """«Дом» больше не подставляется: пока пользователь не завёл шаблоны, старт пуст."""
    with connect(config) as connection:
        result = SettingsService(connection).read()
        assert _field(result, "default_start_address")["value"] == ""

        updated = SettingsService(connection).update({"default_start_address": "  "})
        assert _field(updated, "default_start_address")["value"] == ""


def test_update_reports_invalid_values_without_raising(config) -> None:
    """Кривое значение не роняет запрос: оно возвращается в rejected с причиной.

    Старый контракт «первый ValueError отвергает всё» превращал одну кривую дату
    в потерю всего батча и вечный ретрай события. Теперь отказ — поключевой.
    """
    with connect(config) as connection:
        service = SettingsService(connection)

        result = service.update({"min_hourly_income": "не число"})
        assert result["updated"] == []
        assert [item["key"] for item in result["rejected"]] == ["min_hourly_income"]
        assert result["rejected"][0]["reason"]
        assert result["rejected"][0]["label"]

        result = service.update({"fuel_price_per_liter": -1})
        assert [item["key"] for item in result["rejected"]] == ["fuel_price_per_liter"]

        # inf проходит float(), но int(inf) дал бы OverflowError → 500 → зомби.
        result = service.update({"min_hourly_income": "Infinity"})
        assert [item["key"] for item in result["rejected"]] == ["min_hourly_income"]
        result = service.update({"min_hourly_income": float("nan")})
        assert [item["key"] for item in result["rejected"]] == ["min_hourly_income"]

        result = service.update({"address_templates": "   "})
        assert [item["key"] for item in result["rejected"]] == ["address_templates"]

        # Батч из одних неизвестных ключей — не ошибка: 400 на такое событие
        # означал бы вечный ретрай зомби из очереди старого клиента.
        result = service.update({"only_unknown_key": 1})
        assert result["updated"] == []
        assert result["rejected"] == []
        assert result["ignored"] == ["only_unknown_key"]


def test_one_bad_value_does_not_sink_the_batch(config) -> None:
    """Сценарий жалобы: дата ОСАГО кривая, а адреса и переключатели — валидные.

    Раньше гибло всё нажатие «Сохранить» разом; человек видел «Настройки
    сохранены» и пустые поля. Теперь валидное применяется, кривое — в rejected.
    """
    with connect(config) as connection:
        service = SettingsService(connection)
        result = service.update(
            {
                "default_start_address": "Комендантский 17к1",
                "default_finish_address": "Невский 1",
                "auto_open_navigator": True,
                "count_personal_trips": True,
                "osago_expires_at": "когда-нибудь",
            }
        )

        assert set(result["updated"]) == {
            "default_start_address",
            "default_finish_address",
            "auto_open_navigator",
            "count_personal_trips",
        }
        assert [item["key"] for item in result["rejected"]] == ["osago_expires_at"]

        settings = SettingsRepository(connection)
        assert settings.get("default_start_address") == "Комендантский 17к1"
        assert settings.get_bool("auto_open_navigator", False) is True
        assert settings.get_bool("count_personal_trips", False) is True
        assert settings.get("osago_expires_at") in (None, "")


def test_human_date_formats_are_accepted_and_normalized(config) -> None:
    """«16.07.2027» — естественный русский ввод; хранится всегда ISO."""
    with connect(config) as connection:
        service = SettingsService(connection)
        settings = SettingsRepository(connection)
        for raw in ("2027-07-16", "16.07.2027", "16/07/2027", "16-07-2027"):
            result = service.update({"osago_expires_at": raw})
            assert result["updated"] == ["osago_expires_at"], raw
            assert settings.get("osago_expires_at") == "2027-07-16", raw


def test_round_trip_every_catalog_key(config) -> None:
    """Каждый ключ каталога: сохранил → перечитал → значение то же.

    До этого round-trip покрывал 6 ключей из 43 — ровно в непокрытых жила
    жалоба «не сохраняется». Теперь выпадение любого ключа из цикла
    сохранения ловится здесь, а не человеком на телефоне.
    """
    from app.services.settings_service import SETTINGS_CATALOG

    zones_value = [
        {"region": "Ленинградская область", "city": "Санкт-Петербург", "districts": ["Приморский"]}
    ]
    with connect(config) as connection:
        service = SettingsService(connection)
        for field in SETTINGS_CATALOG:
            if field.type == "number":
                value = field.min if field.min is not None else 1
                expected = float(value)
            elif field.type == "bool":
                value = not bool(field.default)
                expected = value
            elif field.type == "list":
                value = ["Альфа", "Бета"]
                expected = ["Альфа", "Бета"]
            elif field.type == "choice":
                value = field.options[-1][0]
                expected = value
            elif field.type == "date":
                value = "16.07.2027"
                expected = "2027-07-16"
            elif field.type == "zones":
                value = zones_value
                expected = None  # сверяется отдельно, через парсер
            else:  # text
                value = f"проверка {field.key}"
                expected = value

            result = service.update({field.key: value})
            assert result["updated"] == [field.key], f"{field.key} не применился"
            read_back = _field(service.read(), field.key)["value"]
            if field.type == "zones":
                assert [z.city for z in parse_base_zones(read_back)] == ["Санкт-Петербург"]
            else:
                assert read_back == expected, f"{field.key}: {read_back!r} != {expected!r}"


def test_clinic_helpers_follow_settings(config) -> None:
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        assert allowed_clinics(settings) == set(SEEDED_CLINICS)
        assert allowed_telemed_clinics(settings) == set(SEEDED_TELEMED_CLINICS)

        SettingsService(connection).update(
            {"clinics": ["Альфа", "Бета"], "telemed_clinics": ["Альфа"]}
        )
        assert allowed_clinics(settings) == {"Альфа", "Бета"}
        assert allowed_telemed_clinics(settings) == {"Альфа"}


def test_settings_saved_sync_event_applies_and_is_idempotent(config) -> None:
    event = {
        "event_id": "settings-1",
        "event_type": "settings_saved",
        "entity_type": "settings",
        "entity_id": "settings",
        "payload": {"values": {"min_hourly_income": 900}},
    }
    with connect(config) as connection:
        service = MobileApiService(connection)
        first = service.process_sync_event(event)
        second = service.process_sync_event(event)
        stored = SettingsRepository(connection).get_float("min_hourly_income", 0)

    assert first.ok
    assert second.duplicate
    assert stored == 900


def test_sync_event_reports_rejected_and_does_not_fail_forever(config) -> None:
    """Событие с кривой датой: валидное применяется, отказ — в ответе, не в 400.

    Старое поведение — 400 на весь батч — делало событие вечным зомби: клиент
    ретраил его каждые 15 минут до скончания века, а человек ничего не знал.
    """
    event = {
        "event_id": "settings-poison-1",
        "event_type": "settings_saved",
        "entity_type": "settings",
        "entity_id": "settings",
        "payload": {
            "values": {
                "auto_open_navigator": True,
                "osago_expires_at": "не дата вовсе",
            }
        },
    }
    with connect(config) as connection:
        result = MobileApiService(connection).process_sync_event(event)
        stored_navigator = SettingsRepository(connection).get_bool("auto_open_navigator", False)
        status = connection.execute(
            "SELECT status FROM mobile_sync_events WHERE client_event_id = ?",
            ("settings-poison-1",),
        ).fetchone()["status"]

    assert result.ok, "событие обязано пройти, а не зависнуть зомби в очереди"
    assert status == "processed"
    assert stored_navigator is True
    assert result.settings is not None
    assert result.settings["updated"] == ["auto_open_navigator"]
    assert [item["key"] for item in result.settings["rejected"]] == ["osago_expires_at"]
    assert result.settings["rejected"][0]["reason"]
