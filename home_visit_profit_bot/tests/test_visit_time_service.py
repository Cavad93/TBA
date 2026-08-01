"""Минуты на адресах — одно число, один способ (отчёт 878).

Дефект: вердикт по заказу считал ВСЕМ визитам плановые 20 минут, включая работу
на точке с приёмом на четыре часа. Минуты дня занижались в разы, средний ₽/час
раздувался, а вердикт сравнивает новый заказ именно со средним (для внезонных —
`max(средний, порог)`). У человека с долгим приёмом планка становилась
непроходимой, и приложение объявляло невыгодным почти всё.
"""
from __future__ import annotations

from app.models import Visit
from app.services.visit_time_service import total_service_minutes, visit_service_minutes


def _visit(visit_id: int, *, kind: str = "field", service_minutes: float = 0.0) -> Visit:
    return Visit(
        id=visit_id,
        work_day_id=1,
        status="accepted",
        order_number=None,
        address=f"Адрес {visit_id}",
        normalized_address=None,
        district=None,
        is_base_district=True,
        lat=55.75,
        lon=37.62,
        income=1500,
        estimated_extra_km=0,
        estimated_extra_minutes=0,
        kind=kind,
        service_minutes=service_minutes,
    )


def test_onsite_counts_its_own_duration_not_the_planned_average() -> None:
    """Приём с 9 до 13 — это 240 минут, а не 20."""
    assert visit_service_minutes(_visit(1, kind="onsite", service_minutes=240), 20.0) == 240.0


def test_field_visit_counts_the_planned_average() -> None:
    """Обычный визит: своей длительности у него нет, берём плановую."""
    assert visit_service_minutes(_visit(2), 20.0) == 20.0


def test_onsite_without_duration_falls_back_to_planned() -> None:
    """Ноль у работы на точке — это НЕЗАПОЛНЕННОЕ поле (значение модели по умолчанию).

    Если поверить нулю буквально, минуты дня снова занизятся — тот же перекос,
    только с другой стороны.
    """
    assert visit_service_minutes(_visit(3, kind="onsite"), 20.0) == 20.0


def test_duration_survives_the_visit_losing_its_anchor() -> None:
    """Правило смотрит на ДЛИТЕЛЬНОСТЬ, а не на вид визита — и это не мелочь.

    Цена фикс-времени строит контрфактический день, где тот же приём идёт без
    жёсткого времени: `replace(v, kind="field", planned_start_at=None)`. Четыре часа
    приёма при этом никуда не деваются, снят только жёсткий старт. Правило по виду
    решило бы, что «свободный» приём длится 20 минут, и карточка объявила бы, что
    фикс-время съедает 2409 ₽/час на ровном месте.
    """
    from dataclasses import replace

    anchor = _visit(4, kind="onsite", service_minutes=240)
    freed = replace(anchor, kind="field", planned_start_at=None, planned_end_at=None)
    assert visit_service_minutes(freed, 20.0) == 240.0
    assert visit_service_minutes(freed, 20.0) == visit_service_minutes(anchor, 20.0)


def test_day_with_long_appointment_no_longer_understates_minutes() -> None:
    """День = долгий приём + два обычных визита: 240 + 20 + 20, а не 20 + 20 + 20.

    Ровно эта разница раздувала средний ₽/час: 5000 ₽ за 280 минут — это 1071 ₽/час,
    а за 60 минут получалось бы 5000 ₽/час, и следующий заказ обязан был побить
    пятитысячную планку.
    """
    visits = [
        _visit(1, kind="onsite", service_minutes=240),
        _visit(2),
        _visit(3),
    ]
    assert total_service_minutes(visits, 20.0) == 280.0

    net_profit = 5000.0
    honest_hourly = net_profit / (total_service_minutes(visits, 20.0) / 60)
    inflated_hourly = net_profit / (len(visits) * 20.0 / 60)
    assert round(honest_hourly) == 1071
    assert round(inflated_hourly) == 5000
