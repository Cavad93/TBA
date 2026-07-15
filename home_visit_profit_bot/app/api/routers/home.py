"""Штурвал: сводка главного экрана."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import Authed, authed, current_nickname
from app.services.home_service import HomeService

router = APIRouter()


@router.get("/api/home")
def home(auth: Authed = Depends(authed)) -> dict:
    return HomeService(auth.db).snapshot(current_nickname(auth.db))
