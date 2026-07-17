"""Подсказки адреса: слои геокодинга за нашим прокси (Фаза 2).

Ключ DaData живёт на сервере, поэтому подсказки идёт спрашивать сюда, а не в DaData
напрямую из приложения. Ответ — либо уверенный resolved-адрес, либо 0..3 кандидата,
из которых человек выбирает одним тапом (сервер молча ничего не подставляет).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, parse_json, raw_body
from app.repositories import SettingsRepository
from app.services.address_suggest_service import reverse_city, suggest
from app.services.batch_parser import parse_order_lines

router = APIRouter()


@router.post("/api/orders/batch-parse")
def batch_parse(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    """Пакет заказов из текста/шаринга (Ф15.2): разбить на строки-адреса + доход и
    прогнать каждую слоёным геокодингом. Каждый заказ = {address, income} + resolved|
    candidates: клиент красит зелёным (resolved) / жёлтым (candidates) / красным (не понято).
    """
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    text = str(payload.get("text") or "")
    lat = _optional_float(payload.get("lat"))
    lon = _optional_float(payload.get("lon"))
    settings = SettingsRepository(auth.db)
    orders = []
    for order in parse_order_lines(text):
        geo = suggest(order.address, auth.db, settings, auth.user_id, lat=lat, lon=lon)
        orders.append({"address": order.address, "income": order.income, **geo})
    return {"orders": orders}


@router.post("/api/address/suggest")
def suggest_address(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    query = str(payload.get("query") or "").strip()
    if not query:
        raise ApiError(400, {"error": "bad_request", "detail": "пустой запрос"})
    # Текущее местоположение (по GPS), если клиент прислал: им разрешаем неоднозначные
    # адреса по близости — «понять, где человек», не спрашивая город.
    lat = _optional_float(payload.get("lat"))
    lon = _optional_float(payload.get("lon"))
    try:
        return suggest(query, auth.db, SettingsRepository(auth.db), auth.user_id, lat=lat, lon=lon)
    except (ValueError, TypeError) as error:
        raise ApiError(400, {"error": "bad_request", "detail": str(error)})


@router.post("/api/address/city")
def city_by_gps(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    """Город по координатам GPS — для предзаполнения поля «Город» в настройках.

    Всегда 200: {"city": "..."} или {"city": null}. null — честное «не определили»,
    поле останется пустым, а не подставит выдуманный город.
    """
    payload = parse_json(body, {"error": "bad_request"}, with_detail=True)
    lat = _optional_float(payload.get("lat"))
    lon = _optional_float(payload.get("lon"))
    if lat is None or lon is None:
        raise ApiError(400, {"error": "bad_request", "detail": "нужны lat и lon"})
    return {"city": reverse_city(lat, lon, auth.db, auth.user_id)}


def _optional_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
