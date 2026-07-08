from __future__ import annotations

import re


def parse_float(value: str) -> float:
    cleaned = value.strip().replace(",", ".")
    return float(cleaned)


def parse_amount_command(text: str) -> tuple[float, str | None]:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        raise ValueError("Не указана сумма")
    amount_and_comment = parts[1].strip()
    match = re.match(r"^([0-9]+(?:[,.][0-9]+)?)(?:\s+(.*))?$", amount_and_comment)
    if not match:
        raise ValueError("Сумма должна быть числом")
    return parse_float(match.group(1)), match.group(2)


def infer_district(address: str, base_districts: list[str]) -> str | None:
    lowered = address.lower()
    for district in base_districts:
        if district.lower().replace(" район", "") in lowered:
            return district
    return None

