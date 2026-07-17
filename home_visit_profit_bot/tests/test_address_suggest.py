"""Оркестратор слоёв геокодинга и прокси DaData (Фаза 2).

Проверяем главный принцип: уверенный адрес отдаём resolved, неуверенный — кандидатами,
и ни в одном сценарии не подставляем адрес молча. Сеть (Nominatim, DaData) мокаем.
"""
from __future__ import annotations

import pytest

from app.database import connect, current_user_id
from app.repositories import SettingsRepository
from app.repositories_dadata_usage import DadataUsageRepository
from app.repositories_osm_streets import OsmStreetRepository
from app.services import address_suggest_service as orch
from app.services import dadata_service
from app.services.dadata_service import DadataLimitError, DadataSuggestion
from app.services.geocoding_service import GeocodingResult


def _uid() -> int:
    return int(current_user_id.get())


def _suggest(config, query):
    with connect(config) as conn:
        conn.set_user(_uid())
        return orch.suggest(query, conn, SettingsRepository(conn), _uid())


def _seed_streets(config, streets):
    with connect(config) as conn:
        OsmStreetRepository(conn).replace_region("Санкт-Петербург", streets)


_SPB_STREETS = [
    {"city": "Санкт-Петербург", "street": "улица Ленина", "lat": 59.96, "lon": 30.29},
    {"city": "Санкт-Петербург", "street": "проспект Испытателей", "lat": 60.0, "lon": 30.29},
]


def test_confident_nominatim_resolves(config, monkeypatch):
    def fake_geocode(text, *a, **k):
        return GeocodingResult(
            input_text=text, normalized_address="улица Ленина, 40, Санкт-Петербург",
            district="Выборгский", lat=59.96, lon=30.29, confidence=0.7, source="nominatim",
        )
    monkeypatch.setattr(orch, "geocode_address", fake_geocode)
    monkeypatch.setattr(orch, "dadata_token", lambda: None)

    result = _suggest(config, "улица Ленина, 40")
    assert "resolved" in result
    assert result["resolved"]["source"] == "nominatim"
    assert result["resolved"]["lat"] == 59.96


def test_weak_nominatim_becomes_candidate(config, monkeypatch):
    """Слабое совпадение Nominatim (низкий importance) не резолвится молча — в кандидаты."""
    def fake_geocode(text, *a, **k):
        return GeocodingResult(
            input_text=text, normalized_address="что-то похожее",
            district=None, lat=59.9, lon=30.1, confidence=0.1, source="nominatim",
        )
    monkeypatch.setattr(orch, "geocode_address", fake_geocode)
    monkeypatch.setattr(orch, "dadata_token", lambda: None)

    result = _suggest(config, "улица Ленина, 40")
    assert "candidates" in result
    assert result["candidates"] and result["candidates"][0]["source"] == "nominatim"


def test_dadata_typo_gives_candidates(config, monkeypatch):
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "test-key")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)

    def fake_suggest(query, *, token, city=None, count=3, timeout_seconds=5.0):
        assert token == "test-key"
        return [DadataSuggestion(value="улица Ленина, 40", lat=59.96, lon=30.29,
                                 city="Санкт-Петербург", street="улица Ленина")]
    monkeypatch.setattr(dadata_service, "suggest_addresses", fake_suggest)

    result = _suggest(config, "Ленена")  # опечатка, DaData прощает
    assert "candidates" in result
    assert result["candidates"][0]["source"] == "dadata"
    assert result["candidates"][0]["lat"] == 59.96


def test_dadata_limit_falls_to_pg_trgm(config, monkeypatch):
    """Исчерпан лимит DaData (403) → офлайн-слой pg_trgm подхватывает кандидатов."""
    _seed_streets(config, _SPB_STREETS)
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "test-key")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)

    def boom(*a, **k):
        raise DadataLimitError("лимит")
    monkeypatch.setattr(dadata_service, "suggest_addresses", boom)

    result = _suggest(config, "Ленена")
    assert "candidates" in result
    assert any(c["source"] == "osm" for c in result["candidates"])


def test_daily_limit_skips_dadata(config, monkeypatch):
    """Когда лимит пользователя исчерпан, DaData вообще не дёргаем."""
    _seed_streets(config, _SPB_STREETS)
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "test-key")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 0)  # выключено

    called = {"n": 0}
    def spy(*a, **k):
        called["n"] += 1
        return []
    monkeypatch.setattr(dadata_service, "suggest_addresses", spy)

    result = _suggest(config, "Ленена")
    assert called["n"] == 0
    assert "candidates" in result


def test_usage_counter_increments(config, monkeypatch):
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "test-key")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)
    monkeypatch.setattr(dadata_service, "suggest_addresses",
                        lambda *a, **k: [DadataSuggestion("ул. X, 1", 59.9, 30.3, "СПб", "ул. X")])

    _suggest(config, "икс")
    with connect(config) as conn:
        conn.set_user(_uid())
        assert DadataUsageRepository(conn).count_today(_uid()) == 1


def test_coordinates_resolve_directly(config):
    result = _suggest(config, "59.96, 30.29")
    assert result["resolved"]["source"] == "manual_coordinates"


def test_empty_query_returns_empty_candidates(config):
    assert _suggest(config, "   ") == {"candidates": []}


# --- эндпоинт /api/address/suggest (сквозь HTTP-слой) ----------------------

def test_suggest_endpoint_offline(fresh_db, monkeypatch):
    """Эндпоинт отдаёт кандидатов из офлайн-слоя без внешней сети."""
    from fastapi.testclient import TestClient
    from app.api.app import create_app

    # Никакой реальной сети: Nominatim выключен, DaData без ключа — только pg_trgm.
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: None)
    _seed_streets(fresh_db, _SPB_STREETS)

    current_user_id.set(None)
    app = create_app(fresh_db)
    with TestClient(app) as client:
        client.post("/api/auth/register",
                    json={"email": "a@x.com", "password": "supersecret", "nickname": "Ник"})
        client.post("/api/auth/verify-email", json={"email": "a@x.com", "code": "123456"})
        login = client.post("/api/auth/login", json={"email": "a@x.com", "password": "supersecret"})
        token = login.json()["token"]

        resp = client.post("/api/address/suggest", json={"query": "Ленена"},
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "candidates" in body
    assert any(c["source"] == "osm" for c in body["candidates"])


def test_suggest_endpoint_requires_auth(fresh_db):
    from fastapi.testclient import TestClient
    from app.api.app import create_app

    current_user_id.set(None)
    app = create_app(fresh_db)
    with TestClient(app) as client:
        resp = client.post("/api/address/suggest", json={"query": "Ленина"})
    assert resp.status_code == 401


def test_suggest_endpoint_empty_query(fresh_db):
    from fastapi.testclient import TestClient
    from app.api.app import create_app

    current_user_id.set(None)
    app = create_app(fresh_db)
    with TestClient(app) as client:
        client.post("/api/auth/register",
                    json={"email": "b@x.com", "password": "supersecret", "nickname": "Ник"})
        client.post("/api/auth/verify-email", json={"email": "b@x.com", "code": "123456"})
        login = client.post("/api/auth/login", json={"email": "b@x.com", "password": "supersecret"})
        token = login.json()["token"]
        resp = client.post("/api/address/suggest", json={"query": "  "},
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


# --- точный дом резолвится, неоднозначность — на выбор, GPS разрешает (баг «Авиаконструкторов 33») ---

def _sugg(value, lat, lon, house, city="Санкт-Петербург"):
    return DadataSuggestion(value=value, lat=lat, lon=lon, city=city, street=None, house=house)


def test_dadata_exact_house_resolves(config, monkeypatch):
    """DaData нашла точный дом — резолвим сразу, без ручного ввода (репорт-баг)."""
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "k")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)
    # DaData отдаёт дом и его литеры — одна точка.
    monkeypatch.setattr(dadata_service, "suggest_addresses", lambda *a, **k: [
        _sugg("г Санкт-Петербург, пр-кт Авиаконструкторов, д 33", 60.021055, 30.235708, "33"),
        _sugg("г Санкт-Петербург, пр-кт Авиаконструкторов, д 33 литера А", 60.021055, 30.235708, "33"),
    ])
    result = _suggest(config, "Авиаконструкторов 33")
    assert "resolved" in result
    assert result["resolved"]["source"] == "dadata"
    assert round(result["resolved"]["lat"], 4) == 60.0211


def test_dadata_ambiguous_houses_give_candidates(config, monkeypatch):
    """Один дом в разных городах, GPS нет — не резолвим молча, отдаём на выбор."""
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "k")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)
    monkeypatch.setattr(dadata_service, "suggest_addresses", lambda *a, **k: [
        _sugg("г Москва, ул Ленина, д 40", 55.75, 37.61, "40", city="Москва"),
        _sugg("г Санкт-Петербург, ул Ленина, д 40", 59.96, 30.30, "40"),
    ])
    result = _suggest(config, "Ленина 40")
    assert "candidates" in result
    assert len(result["candidates"]) == 2


def test_gps_disambiguates_to_nearest(config, monkeypatch):
    """Есть GPS — из одинаковых «Ленина 40» берём ближайшую и резолвим (понимаем по GPS)."""
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "k")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)
    monkeypatch.setattr(dadata_service, "suggest_addresses", lambda *a, **k: [
        _sugg("г Москва, ул Ленина, д 40", 55.75, 37.61, "40", city="Москва"),
        _sugg("г Санкт-Петербург, ул Ленина, д 40", 59.96, 30.30, "40"),
    ])
    with connect(config) as conn:
        conn.set_user(_uid())
        # Пользователь физически в Петербурге.
        result = orch.suggest("Ленина 40", conn, SettingsRepository(conn), _uid(),
                              lat=59.95, lon=30.31)
    assert "resolved" in result
    assert result["resolved"]["city"] == "Санкт-Петербург"


def test_dadata_wrong_city_setting_still_resolves(config, monkeypatch):
    """Город в настройках не тот — фолбэк без фильтра всё равно находит дом."""
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "k")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)
    calls = []
    def fake(query, *, token, city=None, count=7, timeout_seconds=5.0):
        calls.append(city)
        if city:  # с «неправильным» городом DaData ничего не нашла
            return []
        return [_sugg("г Санкт-Петербург, пр-кт Авиаконструкторов, д 33", 60.021, 30.235, "33")]
    monkeypatch.setattr(dadata_service, "suggest_addresses", fake)
    result = _suggest(config, "Авиаконструкторов 33")
    assert "resolved" in result
    # Было два вызова: с городом (пусто) и без города (нашёл).
    assert calls[0] is not None and calls[-1] is None


# --- отчёт 3 из Telegram: город отдельно, улица+дом без города, reverse по GPS ---

def test_dadata_candidate_carries_street_house(config, monkeypatch):
    """Кандидат несёт улицу и дом БЕЗ города, с корпусом.

    Клиент показывает street_house — номер дома виден целиком, а не съеден
    префиксом «г Санкт-Петербург», как было (обрезка maxLines=1 на подсказке).
    """
    monkeypatch.setattr(orch, "geocode_address", lambda *a, **k: None)
    monkeypatch.setattr(orch, "dadata_token", lambda: "k")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)
    monkeypatch.setattr(dadata_service, "suggest_addresses", lambda *a, **k: [
        DadataSuggestion("г Москва, ул Ленина, д 40", 55.75, 37.61, "Москва", "ул Ленина", "40"),
        DadataSuggestion("г СПб, ул Ленина, д 40 к 2", 59.96, 30.30, "Санкт-Петербург", "ул Ленина", "40"),
    ])
    result = _suggest(config, "Ленина 40")
    assert "candidates" in result
    houses = {c["street_house"] for c in result["candidates"]}
    # Город отрезан, но корпус сохранён — ровно то, чего человек не видел.
    assert "ул Ленина, д 40" in houses
    assert "ул Ленина, д 40 к 2" in houses
    assert all(c["city"] for c in result["candidates"])


def test_weak_nominatim_candidate_has_no_invented_city(config, monkeypatch):
    """Слабый Nominatim-кандидат НЕ выдумывает город из настроек — city честно None.

    Иначе клиент, предзаполняя поле «Город» этим значением, соврал бы: показал бы
    город настроек для точки, чей город на деле неизвестен.
    """
    monkeypatch.setattr(orch, "geocode_address", lambda text, *a, **k: GeocodingResult(
        input_text=text, normalized_address="что-то похожее", district=None,
        lat=59.9, lon=30.1, confidence=0.1, source="nominatim"))
    monkeypatch.setattr(orch, "dadata_token", lambda: None)
    result = _suggest(config, "улица Ленина, 40")
    nominatim = next(c for c in result["candidates"] if c["source"] == "nominatim")
    assert nominatim["city"] is None


def test_reverse_city_returns_city(config, monkeypatch):
    monkeypatch.setattr(orch, "dadata_token", lambda: "k")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)
    monkeypatch.setattr(dadata_service, "geolocate_city",
                        lambda lat, lon, *, token, timeout_seconds=5.0: "Казань")
    with connect(config) as conn:
        conn.set_user(_uid())
        assert orch.reverse_city(55.79, 49.12, conn, _uid()) == "Казань"


def test_reverse_city_none_without_token(config, monkeypatch):
    """Нет ключа DaData — честный None, а не выдуманный город."""
    monkeypatch.setattr(orch, "dadata_token", lambda: None)
    with connect(config) as conn:
        conn.set_user(_uid())
        assert orch.reverse_city(55.79, 49.12, conn, _uid()) is None


def test_city_endpoint_returns_city(fresh_db, monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.app import create_app

    monkeypatch.setattr(orch, "dadata_token", lambda: "k")
    monkeypatch.setattr(orch, "dadata_daily_limit_per_user", lambda: 300)
    monkeypatch.setattr(dadata_service, "geolocate_city",
                        lambda lat, lon, *, token, timeout_seconds=5.0: "Казань")
    current_user_id.set(None)
    app = create_app(fresh_db)
    with TestClient(app) as client:
        client.post("/api/auth/register",
                    json={"email": "c@x.com", "password": "supersecret", "nickname": "Ник"})
        client.post("/api/auth/verify-email", json={"email": "c@x.com", "code": "123456"})
        token = client.post("/api/auth/login",
                            json={"email": "c@x.com", "password": "supersecret"}).json()["token"]
        resp = client.post("/api/address/city", json={"lat": 55.79, "lon": 49.12},
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["city"] == "Казань"


def test_city_endpoint_requires_coords(fresh_db):
    from fastapi.testclient import TestClient
    from app.api.app import create_app

    current_user_id.set(None)
    app = create_app(fresh_db)
    with TestClient(app) as client:
        client.post("/api/auth/register",
                    json={"email": "d@x.com", "password": "supersecret", "nickname": "Ник"})
        client.post("/api/auth/verify-email", json={"email": "d@x.com", "code": "123456"})
        token = client.post("/api/auth/login",
                            json={"email": "d@x.com", "password": "supersecret"}).json()["token"]
        resp = client.post("/api/address/city", json={},
                           headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
