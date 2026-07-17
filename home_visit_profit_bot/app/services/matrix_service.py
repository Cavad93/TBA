"""Матрица расстояний и коэффициенты для расчётов на телефоне (Фаза 3.2).

Раздел труда: сервер — карты (матрица OSRM с кешем из Ф1.5), телефон — арифметика.
Эндпоинт отдаёт квадратную матрицу расстояний/времени между точками дня и снимок
коэффициентов (стоимость км, пороги ₽/час, минуты на адрес), по которым телефон
считает выгодность офлайн. «Формула — на телефон, коэффициенты — с сервера».

OSRM молчать не должен: если точка вне покрытия карт или сервер карт недоступен —
считаем матрицу по прямой (haversine × коэффициент) и честно ставим флаг `fallback`,
чтобы телефон и человек знали, что это оценка, а не дорога по карте.
"""

from __future__ import annotations

from app.models import Point
from app.repositories import DailyStatsRepository, SettingsRepository
from app.services.overwork_pricing_service import build_pricing
from app.services.profitability_service import vehicle_km_cost
from app.services.routing_service import (
    OutsideCoverageError,
    RoutingError,
    get_estimated_distance_matrix,
)
from app.services.osrm_cache import cached_distance_matrix
from app.services.server_settings import osrm_url as server_osrm_url, request_timeout_seconds


def snapshot_version(
    cost,
    min_hourly: float,
    service_minutes: float,
    straight_line_factor: float,
    *,
    auto_optimize: bool = True,
) -> str:
    """Короткая версия снимка коэффициентов: телефон и сервер сверяют, что считают одним.

    Меняется любой коэффициент — меняется строка. Клиент кладёт её рядом с расчётом;
    расхождение версий в логе синка (Ф3.6) объясняет расхождение чисел без гадания.
    Публичная — её же зовёт `formula_parity_service`, чтобы формат снимка был один.
    Флаг auto_optimize в версии обязателен: режим порядка объезда меняет extra_km,
    и расхождение из-за него должно объясняться версией снимка, а не выглядеть багом.
    """
    order = "1" if auto_optimize else "0"
    return (
        f"km{cost.fuel_per_km:.2f}_{cost.maintenance_per_km:.2f}"
        f"|mh{min_hourly:.0f}|sm{service_minutes:.0f}|f{straight_line_factor:.2f}|o{order}"
    )


# Старое имя оставлено как псевдоним: на него мог ссылаться внешний код/тесты.
_snapshot_version = snapshot_version


def build_matrix_response(
    points: list[Point],
    settings_repo: SettingsRepository,
    stats_repo: DailyStatsRepository | None,
    *,
    profile: str = "driving",
    route_time_factor: float = 1.0,
    service_minutes: float = 20.0,
    debt: float = 0.0,
) -> dict:
    """Собрать ответ /api/route/matrix: матрица + коэффициенты + флаг fallback.

    Хендлер синхронный (как все 43 в проекте) и крутится в anyio-threadpool — блокирующий
    вызов OSRM тут не держит event loop (решение Фазы 1). Поэтому и матрицу берём
    синхронным cached_distance_matrix, а не async-вариантом.
    """
    cost = vehicle_km_cost(settings_repo, stats_repo, route_time_factor=route_time_factor)
    min_hourly = settings_repo.get_float("min_hourly_income", 600)
    min_marginal_hourly = settings_repo.get_float("min_marginal_hourly_income", min_hourly)
    outside_min_hourly = settings_repo.get_float("outside_zone_min_hourly_income", min_hourly)
    outside_min_extra = settings_repo.get_float("outside_zone_min_extra_payment", 0)
    # Пороги — ЭФФЕКТИВНЫЕ (с надбавкой за переработку): живая серверная оценка судит
    # по ним, и офлайн-вердикт телефона обязан судить теми же цифрами, а не базовыми —
    # иначе в самолётном режиме при высоком долге заказы выглядели бы выгоднее.
    pricing = build_pricing(
        debt=debt,
        min_hourly=min_hourly,
        outside_min_hourly=outside_min_hourly,
        min_marginal_hourly=min_marginal_hourly,
    )
    min_hourly = pricing.effective_min_hourly
    min_marginal_hourly = pricing.effective_min_marginal_hourly
    outside_min_hourly = pricing.effective_outside_min_hourly
    avg_speed = settings_repo.get_float("avg_speed_kmh", 30)
    straight_line_factor = settings_repo.get_float("straight_line_factor", 1.35)
    # Режим порядка объезда обязан ехать в снимок: при выключенной оптимизации
    # сервер считает день по порядку Ленты (Этап 20), и телефон офлайн обязан
    # считать так же — иначе extra_km расходится на первом же дне с 2+ заказами.
    auto_optimize = settings_repo.get_bool("auto_optimize", True)

    fallback = False
    if len(points) < 2:
        distances = [[0.0]]
        durations = [[0.0]]
    else:
        try:
            matrix = cached_distance_matrix(
                points,
                osrm_url=server_osrm_url(profile),
                profile=profile,
                timeout_seconds=request_timeout_seconds(),
                duration_factor=route_time_factor,
            )
            distances = matrix.distances_km
            durations = matrix.durations_minutes
        except (OutsideCoverageError, RoutingError):
            # Вне покрытия или сервер карт молчит — по прямой, но честно помечаем.
            estimate = get_estimated_distance_matrix(
                points, avg_speed_kmh=avg_speed, straight_line_factor=straight_line_factor
            )
            distances = estimate.distances_km
            durations = estimate.durations_minutes
            fallback = True

    return {
        "distances_km": distances,
        "durations_minutes": durations,
        "fallback": fallback,
        "coefficients": {
            "fuel_per_km": round(cost.fuel_per_km, 4),
            "maintenance_per_km": round(cost.maintenance_per_km, 4),
            "cost_per_km": round(cost.fuel_per_km + cost.maintenance_per_km, 4),
            "min_hourly_income": min_hourly,
            "min_marginal_hourly_income": min_marginal_hourly,
            "outside_zone_min_hourly_income": outside_min_hourly,
            "outside_zone_min_extra_payment": outside_min_extra,
            "service_minutes": service_minutes,
            "avg_speed_kmh": avg_speed,
            "straight_line_factor": straight_line_factor,
            "auto_optimize": auto_optimize,
        },
        "snapshot_version": snapshot_version(
            cost, min_hourly, service_minutes, straight_line_factor, auto_optimize=auto_optimize
        ),
    }
