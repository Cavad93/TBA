"""Сервер — источник правды: лог расхождений расчёта телефон↔сервер (Фаза 3.6).

Телефон считает выгодность заказа сам (candidate_pure → Kotlin ProfitabilityCalculator),
а при синке присылает СВОЁ число маржинальной прибыли и версию снимка коэффициентов,
на которых считал. Сервер пересчитывает ту же маржу по своим текущим коэффициентам и,
если расходится больше чем на порог (1 ₽), пишет строку в `formula_discrepancies` —
это сигнал «формулы разъехались» или «телефон считал на устаревших коэффициентах».

Здесь только маржинальная прибыль (₽) — ровно та величина, про которую план говорит
«расхождение >1 ₽». Она не требует полного пересчёта дня: income − extra_km×стоимость_км,
и считается ТЕМИ ЖЕ шагами, что в candidate_pure (та же отсечка дребезга по км), — иначе
сам лог давал бы ложные срабатывания.
"""

from __future__ import annotations

import logging

from app.repositories import DailyStatsRepository, SettingsRepository, now_iso
from app.services.matrix_service import snapshot_version
from app.services.profitability_service import vehicle_km_cost

logger = logging.getLogger(__name__)

# Порог расхождения в рублях: план 3.6 — «>1 ₽ пишется в лог как баг».
DISCREPANCY_THRESHOLD_RUB = 1.0

# Отсечка дребезга по км — точь-в-точь как в candidate_pure._zero_tiny(epsilon=0.05):
# короткий подъезд к соседнему дому (пара десятков метров) не должен считаться дорогой.
_KM_EPSILON = 0.05


def _zero_tiny(value: float, epsilon: float) -> float:
    return 0.0 if abs(value) < epsilon else value


def _server_marginal_profit(income: float, extra_km: float, cost_per_km: float) -> float:
    """Маржинальная прибыль заказа по-серверному — теми же шагами, что candidate_pure."""
    paid_extra_km = max(0.0, _zero_tiny(extra_km, _KM_EPSILON))
    return round(income - paid_extra_km * cost_per_km, 2)


def check_visit_parity(
    connection,
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None,
    *,
    visit_id: int | None,
    income: float,
    extra_km: float,
    client_marginal_profit: float | None,
    client_snapshot_version: str | None,
    threshold_rub: float = DISCREPANCY_THRESHOLD_RUB,
) -> float | None:
    """Сверить клиентскую марж. прибыль с серверной; при расхождении >порога — залогировать.

    Возвращает дельту в рублях (или None, если клиент число не прислал — старый APK).
    Сам факт расхождения не влияет на данные: сервер остаётся источником правды, а лог
    нужен людям для разбора «почему на телефоне было одно число, а на сервере другое».
    """
    if client_marginal_profit is None:
        return None  # старый клиент без расчёта на телефоне — сверять нечего

    cost = vehicle_km_cost(settings_repo, stats_repo)
    cost_per_km = cost.fuel_per_km + cost.maintenance_per_km
    server_marginal = _server_marginal_profit(float(income), float(extra_km), cost_per_km)
    delta = abs(float(client_marginal_profit) - server_marginal)

    if delta <= threshold_rub:
        return delta

    min_hourly = settings_repo.get_float("min_hourly_income", 600)
    service_minutes = settings_repo.get_float("default_service_minutes", 20)
    straight_line_factor = settings_repo.get_float("straight_line_factor", 1.35)
    server_snapshot = snapshot_version(
        cost, min_hourly, service_minutes, straight_line_factor,
        auto_optimize=settings_repo.get_bool("auto_optimize", True),
    )
    details = (
        f"маржа: телефон {float(client_marginal_profit):.2f} ₽ vs сервер {server_marginal:.2f} ₽ "
        f"(Δ {delta:.2f} ₽); снимок телефона {client_snapshot_version or '—'} vs сервер {server_snapshot}"
    )
    logger.warning("Расхождение формул (Ф3.6), visit_id=%s: %s", visit_id, details)
    connection.execute(
        """
        INSERT INTO formula_discrepancies(
            visit_id, client_marginal_profit, server_marginal_profit, delta_rub,
            client_snapshot_version, server_snapshot_version, details, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            visit_id,
            round(float(client_marginal_profit), 2),
            server_marginal,
            round(delta, 2),
            client_snapshot_version,
            server_snapshot,
            details,
            now_iso(),
        ),
    )
    return delta


def recent_discrepancies(connection, limit: int = 20) -> list[dict]:
    """Последние расхождения — для эндпоинта разбора (как sync/conflicts)."""
    rows = connection.execute(
        """
        SELECT id, visit_id, client_marginal_profit, server_marginal_profit, delta_rub,
               client_snapshot_version, server_snapshot_version, details, created_at
        FROM formula_discrepancies
        ORDER BY id DESC
        LIMIT ?
        """,
        (max(1, min(100, limit)),),
    ).fetchall()
    return [dict(row) for row in rows]
