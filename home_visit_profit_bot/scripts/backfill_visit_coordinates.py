"""Разовый бэкфилл координат у старых «ручных» заказов (предложение P1).

Заказы, заведённые до правок с ручными км, лежат без координат: они не участвуют в
автомаршруте и не показываются на карте. Здесь прогоняем их адреса через слоёный
геокодер (Nominatim → learned-кеш → DaData) и дозаполняем точку.

ЗАПУСКАТЬ ВРУЧНУЮ, ОТДЕЛЬНО ОТ ДЕПЛОЯ:

    python3 home_visit_profit_bot/scripts/backfill_visit_coordinates.py --dry-run
    python3 home_visit_profit_bot/scripts/backfill_visit_coordinates.py --limit 200

Почему не при открытии дня и не в деплое:

* RLS. Данные изолированы по пользователю, и проход обязан идти ПОД КАЖДЫМ
  пользователем отдельно. Глобальный проход просто ничего не увидит.
* Квота DaData. Она считается по пользователям; массовый прогон её сжигает, поэтому
  здесь есть --limit и пауза между запросами.
* История. Бэкфилл меняет только координаты и НЕ пересчитывает daily_stats: заново
  посчитанные километры молча переписали бы закрытые смены. Каждая тронутая строка
  помечается coords_backfilled_at — чтобы потом было видно, что правил скрипт, а не
  человек.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_config
from app.db import connect
from app.repositories import VisitRepository, now_iso
from app.services.mobile_visit_service import MobileVisitService

# Пауза между обращениями к геокодеру: массовый прогон не должен выглядеть атакой
# и не должен сжигать квоту залпом.
THROTTLE_SECONDS = 0.35


def _users(connection) -> list[int]:
    rows = connection.execute("SELECT id FROM users ORDER BY id").fetchall()
    return [int(row["id"]) for row in rows]


def _backfill_user(connection, user_id: int, limit: int, dry_run: bool) -> tuple[int, int]:
    """Вернуть (сколько нашли без координат, скольким проставили точку)."""
    connection.set_user(user_id)
    visits = VisitRepository(connection)
    service = MobileVisitService(connection)

    pending = visits.list_missing_coordinates(limit=limit)
    filled = 0
    for visit in pending:
        if not (visit.address or "").strip():
            continue
        geo = service._geocode_layered(visit.address)
        if geo is None or geo.lat is None or geo.lon is None:
            continue
        if not dry_run:
            visits.backfill_coordinates(
                visit.id,
                lat=geo.lat,
                lon=geo.lon,
                normalized_address=geo.normalized_address or visit.address,
                backfilled_at=now_iso(),
            )
        filled += 1
        time.sleep(THROTTLE_SECONDS)
    return len(pending), filled


def main() -> int:
    parser = argparse.ArgumentParser(description="Бэкфилл координат старых заказов")
    parser.add_argument("--limit", type=int, default=100, help="сколько заказов на пользователя за прогон")
    parser.add_argument("--dry-run", action="store_true", help="только показать, ничего не писать")
    args = parser.parse_args()

    config = load_config()
    total_pending = 0
    total_filled = 0
    with connect(config) as connection:
        for user_id in _users(connection):
            pending, filled = _backfill_user(connection, user_id, args.limit, args.dry_run)
            total_pending += pending
            total_filled += filled
            if pending:
                print(f"пользователь {user_id}: без координат {pending}, распознано {filled}")

    verb = "нашлось бы" if args.dry_run else "проставлено"
    print(f"итого: без координат {total_pending}, {verb} {total_filled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
