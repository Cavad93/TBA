"""Матрица активного дня с координатами точек — основа офлайн-вердикта (Фаза 3.4/3.5).

Клиент координат заказов не хранит: сервер собирает точки [старт, принятые…, финиш]
и отдаёт их координаты в порядке матрицы + доходы заказов. Считается на настоящем
OSRM (сервер 2 через SSH-туннель).
"""

from __future__ import annotations

from app.db import connect
from app.services.matrix_service import build_matrix_response
from app.services.mobile_visit_service import MobileVisitService
from app.repositories import SettingsRepository, VisitRepository, WorkDayRepository


def test_matrix_thresholds_are_effective_under_overwork(config) -> None:
    """Пороги снимка — эффективные (с надбавкой за переработку), как у живой оценки.

    Раньше матрица несла базовые пороги, и офлайн-вердикт при высоком долге судил
    мягче серверного. Долг 70 → ступень +25%.
    """
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        settings.set("min_hourly_income", "600")
        response = build_matrix_response([], settings, None, debt=70.0)
    assert response["coefficients"]["min_hourly_income"] == 750.0


def test_matrix_thresholds_stay_base_without_debt(config) -> None:
    """Без долга пороги остаются базовыми — поведение прежнее."""
    with connect(config) as connection:
        settings = SettingsRepository(connection)
        settings.set("min_hourly_income", "600")
        response = build_matrix_response([], settings, None)
    assert response["coefficients"]["min_hourly_income"] == 600.0


def test_day_matrix_returns_points_incomes_and_square_matrix(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Финиш", 30, 20,
                          start_lat=59.930, start_lon=30.310,
                          finish_lat=59.960, finish_lon=30.400)
        a = visits.create_candidate(day.id, "Заказ А", 2000, 0, 0, None, True, lat=59.940, lon=30.330)
        b = visits.create_candidate(day.id, "Заказ Б", 1500, 0, 0, None, True, lat=59.950, lon=30.360)
        visits.accept(a.id)
        visits.accept(b.id)

        response = MobileVisitService(connection).day_matrix()

    # Точки: старт + 2 заказа + финиш = 4, матрица 4×4.
    points = response["points"]
    assert len(points) == 4
    assert len(response["distances_km"]) == 4
    assert all(len(row) == 4 for row in response["distances_km"])
    # Заказы несут visit_id, старт/финиш — нет.
    assert points[0]["visit_id"] is None      # старт
    assert points[-1]["visit_id"] is None     # финиш
    assert points[1]["visit_id"] == a.id
    assert points[2]["visit_id"] == b.id
    # Доходы заказов в том же порядке.
    assert response["incomes"] == [2000, 1500]
    # Коэффициенты для офлайн-расчёта на месте.
    assert response["coefficients"]["straight_line_factor"] > 0
    assert "snapshot_version" in response


def test_day_matrix_folds_finish_to_start_when_absent(config) -> None:
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        # Финиша нет → замыкаем на старт (Ф9.2), точка финиша = координаты старта.
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.930, start_lon=30.310)
        a = visits.create_candidate(day.id, "Заказ А", 2000, 0, 0, None, True, lat=59.940, lon=30.330)
        visits.accept(a.id)
        response = MobileVisitService(connection).day_matrix()

    points = response["points"]
    assert len(points) == 3  # старт + заказ + финиш(=старт)
    assert points[-1]["lat"] == 59.930 and points[-1]["lon"] == 30.310
