"""Профиль пользователя."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import Authed, authed, current_nickname
from app.services.profile_service import ProfileService

router = APIRouter()


@router.get("/api/profile")
def profile(auth: Authed = Depends(authed)) -> dict:
    return ProfileService(auth.db).snapshot(current_nickname(auth.db))
