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
from app.services.profitability_service import vehicle_km_cost
from app.services.routing_service import (
    OutsideCoverageError,
    RoutingError,
    get_estimated_distance_matrix,
)
from app.services.osrm_cache import cached_distance_matrix
from app.services.server_settings import osrm_url as server_osrm_url, request_timeout_seconds


def snapshot_version(cost, min_hourly: float, service_minutes: float, straight_line_factor: float) -> str:
    """Короткая версия снимка коэффициентов: телефон и сервер сверяют, что считают одним.

    Меняется любой коэффициент — меняется строка. Клиент кладёт её рядом с расчётом;
    расхождение версий в логе синка (Ф3.6) объясняет расхождение чисел без гадания.
    Публичная — её же зовёт `formula_parity_service`, чтобы формат снимка был один.
    """
    return f"km{cost.fuel_per_km:.2f}_{cost.maintenance_per_km:.2f}|mh{min_hourly:.0f}|sm{service_minutes:.0f}|f{straight_line_factor:.2f}"


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
    avg_speed = settings_repo.get_float("avg_speed_kmh", 30)
    straight_line_factor = settings_repo.get_float("straight_line_factor", 1.35)

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
        },
        "snapshot_version": snapshot_version(cost, min_hourly, service_minutes, straight_line_factor),
    }
