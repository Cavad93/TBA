"""Оклад: подтверждение месяца одной кнопкой."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import Authed, authed
from app.repositories import SettingsRepository
from app.services.income_service import confirm_month

router = APIRouter()


@router.post("/api/income/confirm")
def income_confirm(auth: Authed = Depends(authed)) -> dict:
    confirm_month(SettingsRepository(auth.db))
    return {"ok": True, "reason": "income_confirmed"}
