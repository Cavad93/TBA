"""Точка безубыточности смены (Фаза 10.2).

Аренда авто и прочие обязательные траты — это «беговая дорожка»: смена начинается в
минусе на сумму фикс-расходов, и только когда чистый доход завершённых заказов их
перекрыл, работник начинает зарабатывать себе. Момент «смена отбита» — когда
накопленный чистый (доходы завершённых визитов − топливо по факту км − износ)
пересекает сумму фикс-расходов.

Считается ТОЛЬКО здесь, на сервере; телефон получает готовый блок в /api/home и
рендерит без пересчёта (единственная его арифметика — прогресс-бар). Прежняя
версия этого докстринга обещала расчёт «и на телефоне» — такого кода никогда не
существовало (paritet-проход Этапа 32), обещание вводило аудит в заблуждение.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Visit, WorkDay
from app.repositories import DailyStatsRepository, SettingsRepository
from app.services.profitability_service import calculate_day_profitability


@dataclass(frozen=True)
class BreakevenStatus:
    fixed_costs: float          # аренда + прочие обязательные расходы смены, ₽
    accumulated_net: float      # накопленный чистый доход завершённых визитов, ₽
    is_paid_off: bool           # смена отбита (чистый ≥ фикс-расходов)
    remaining_to_breakeven: float  # сколько ещё до нуля, ₽ (0, если уже отбита)

    def payload(self) -> dict:
        return {
            "fixed_costs": round(self.fixed_costs, 2),
            "accumulated_net": round(self.accumulated_net, 2),
            "is_paid_off": self.is_paid_off,
            "remaining_to_breakeven": round(self.remaining_to_breakeven, 2),
        }


def shift_fixed_costs(settings_repo: SettingsRepository) -> float:
    """Сумма обязательных расходов смены: аренда авто + прочее (мойка, связь…).

    Аренду исторически можно было задать двумя одноимёнными ручками в разных
    разделах настроек: shift_rent_cost («Экономика») и daily_vehicle_rent
    («Машина» — раньше она не влияла НИ НА ЧТО, мёртвая ручка). Смысл один —
    аренда за смену, поэтому берём максимум, а не сумму: сумма задвоила бы
    аренду у тех, кто заполнил обе.
    """
    rent = max(
        0.0,
        settings_repo.get_float("shift_rent_cost", 0.0),
        settings_repo.get_float("daily_vehicle_rent", 0.0),
    )
    other = max(0.0, settings_repo.get_float("shift_fixed_costs", 0.0))
    return rent + other


def shift_breakeven(
    day: WorkDay,
    visits: list[Visit],
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None = None,
) -> BreakevenStatus | None:
    """Статус безубыточности или None, если фикс-расходов нет (блок не показываем).

    None при нулевых фикс-расходах: у кого свой авто и нет обязательных трат —
    безубыточность бессмысленна, смена в плюсе с первого заказа.
    """
    fixed = shift_fixed_costs(settings_repo)
    # Аренда, ВНЕСЁННАЯ расходом дня, — тоже фикс-расход, даже если настройки
    # пусты: раньше такой человек блока не видел вовсе («смена в плюсе с первого
    # заказа» при минусе на аренду). Максимум с настройкой заодно чинит и
    # рассинхрон «в настройках 1000, внесено 1200»: порог — реальная касса.
    fixed = max(fixed, max(0.0, day.vehicle_rent or 0.0) + max(0.0, settings_repo.get_float("shift_fixed_costs", 0.0)))
    if fixed <= 0:
        return None

    completed = [visit for visit in visits if visit.status == "completed"]
    # Чистый доход завершённых визитов: доходы − топливо по факту км − износ.
    # calculate_day_profitability со списком только завершённых считает маршрут по ним.
    net, _, _, _, _ = calculate_day_profitability(day, completed, settings_repo, stats_repo)
    # Аренда, внесённая расходом дня (категория «Аренда машины»), — это и есть те
    # фикс-расходы, которые отбиваем. Внутри net она уже вычтена, и сравнение net
    # с fixed требовало бы отбить аренду ДВАЖДЫ. Возвращаем её в операционный чистый.
    operating_net = net + max(0.0, day.vehicle_rent or 0.0)

    remaining = fixed - operating_net
    return BreakevenStatus(
        fixed_costs=fixed,
        accumulated_net=operating_net,
        is_paid_off=operating_net >= fixed,
        remaining_to_breakeven=max(0.0, remaining),
    )
