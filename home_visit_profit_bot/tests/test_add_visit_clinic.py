from __future__ import annotations

from app.telegram_bot.conversations import parse_add_payload


def test_parse_add_payload_accepts_clinic_number_as_third_field() -> None:
    data = parse_add_payload("/add Мурино, Воронцовский 5 | 2500 | 2")

    assert data["address"] == "Мурино, Воронцовский 5"
    assert data["income"] == 2500
    assert data["clinic"] == "ПСК"


def test_parse_add_payload_accepts_clinic_in_full_form() -> None:
    data = parse_add_payload("/add адрес | 2500 | 7 | 20 | Приморский | витамед")

    assert data["route_km"] == 7
    assert data["route_minutes"] == 20
    assert data["district"] == "Приморский"
    assert data["clinic"] == "ВИТАМЕД"
