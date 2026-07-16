"""Распознавание заказов со скриншота: прокси на OCR сервера 2 (Фаза 15.4).

Клиент POST'ит картинку (тело запроса) — сервер проксирует на свой OCR по шифрованному
каналу WireGuard, получает текст построчно и прогоняет тем же `parse_order_lines` +
слоёным геокодингом, что и share-target (Ф15.2). Ответ — готовые заказы (зелёный/жёлтый/
красный), как у /api/orders/batch-parse: «списком» и «скриншотом» сходятся в один экран.

Картинка нигде не сохраняется. OCR выключен/недоступен → 503, клиент вводит вручную.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ApiError, Authed, authed, raw_body
from app.repositories import SettingsRepository
from app.services.address_suggest_service import suggest
from app.services.batch_parser import parse_order_lines
from app.services.ocr_service import extract_text
from app.services.server_settings import ocr_token, ocr_url

router = APIRouter()


@router.post("/api/ocr/extract")
def ocr_extract(body: bytes = Depends(raw_body), auth: Authed = Depends(authed)) -> dict:
    if not body:
        raise ApiError(400, {"error": "bad_request", "detail": "пустая картинка"})
    result = extract_text(body, "screenshot.png", ocr_url=ocr_url(), ocr_token=ocr_token())
    if result is None:
        raise ApiError(503, {"error": "ocr_unavailable"})
    # Тот же путь, что и текстовый пакет: строки → заказы + слоёный геокодинг.
    settings = SettingsRepository(auth.db)
    orders = []
    for order in parse_order_lines(result["text"]):
        geo = suggest(order.address, auth.db, settings, auth.user_id)
        orders.append({"address": order.address, "income": order.income, **geo})
    return {"ok": True, "text": result["text"], "orders": orders}
