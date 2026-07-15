"""Проверка живости — единственный публичный эндпоинт без авторизации."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
@router.get("/api/health")
def health() -> dict:
    return {"ok": True}
