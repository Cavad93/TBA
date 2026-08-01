"""Матрица активного дня с координатами точек — основа офлайн-вердикта (Фаза 3.4/3.5).

Клиент координат заказов не хранит: сервер собирает точки [старт, принятые…, финиш]
и отдаёт их координаты в порядке матрицы + доходы заказов. Считается на настоящем
OSRM (сервер 2 через SSH-туннель).
"""

from __future__ import annotations

from app.db import connect
from app.services.matrix_service import build_matrix_response
from app.repositories import DailyStatsRepository, SettingsRepository
from app.services.mobile_visit_service import MobileVisitService
from app.services.profitability_service import calculate_day_profitability
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


def test_day_matrix_sends_service_minutes_of_every_visit(config) -> None:
    """Минуты каждого визита едут в кеш тем же порядком, что доходы (отчёт 878).

    Без этого списка телефон считал день как «количество заказов × средняя», и приём
    с 9 до 13 стоил в офлайн-расчёте 20 минут: минуты дня занижены, средний ₽/час
    раздут, а вердикт сравнивает новый заказ именно с ним. Порядок и длина обязаны
    совпадать с incomes — иначе минуты приедут не к тем заказам.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Финиш", 30, 20,
                          start_lat=59.930, start_lon=30.310,
                          finish_lat=59.960, finish_lon=30.400)
        ordinary = visits.create_candidate(day.id, "Обычный визит", 2000, 0, 0, None, True,
                                           lat=59.940, lon=30.330)
        visits.accept(ordinary.id)
        appointment = visits.create_onsite(
            day.id, "Приём 9:00–13:00", 5000, 240, "2026-07-13T09:00:00", None,
            lat=59.950, lon=30.360,
        )
        visits.accept(appointment.id)

        response = MobileVisitService(connection).day_matrix()

    minutes = response["service_minutes_list"]
    assert len(minutes) == len(response["incomes"]), "длина обязана совпадать с доходами"
    # Порядок — тот же, что у точек-заказов: обычный визит, затем приём.
    ids = [point["visit_id"] for point in response["points"] if point["visit_id"] is not None]
    assert ids == [ordinary.id, appointment.id]
    assert minutes[0] == day.planned_service_minutes, "у обычного визита — плановая средняя"
    assert minutes[1] == 240, "у приёма — его собственные четыре часа"


def test_day_matrix_sends_the_real_order_count(config) -> None:
    """Число заказов дня едет явно — из геометрии кеша его не вывести.

    Телефон раньше считал «сколько заказов уже есть» как «точек минус старт и финиш».
    Завершённые заказы в точки не попадают (они схлопнуты в точку старта), поэтому день
    с тремя завершёнными и нулём принятых выглядел офлайн ПУСТОЙ ЛЕНТОЙ. А пустая лента
    обнуляет порог: телефон говорил «однозначно да» там, где сервер говорил «невыгодно».
    Расхождение систематическое и всегда в сторону оптимизма.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Финиш", 30, 20,
                          start_lat=59.930, start_lon=30.310,
                          finish_lat=59.960, finish_lon=30.400)
        done = visits.create_candidate(day.id, "Завершённый", 2000, 0, 0, None, True,
                                       lat=59.935, lon=30.320)
        visits.accept(done.id)
        visits.complete_visit(done.id)
        active = visits.create_candidate(day.id, "Принятый", 1500, 0, 0, None, True,
                                         lat=59.940, lon=30.330)
        visits.accept(active.id)

        response = MobileVisitService(connection).day_matrix()

    # Точек-заказов в матрице — только одна (завершённый схлопнут в старт).
    order_points = [p for p in response["points"] if p["visit_id"] is not None]
    assert len(order_points) == 1
    # А заказов у дня — два, и именно это число судит порог.
    assert response["existing_count"] == 2, (
        "офлайн снова посчитает завершённые заказы несуществующими и обнулит порог"
    )


def test_day_matrix_carries_the_authoritative_day_before(config) -> None:
    """Снимок несёт готовое «до» дня — то самое, по которому судит серверный вердикт.

    Телефон видит в кеше только принятые заказы: завершённые визиты схлопнуты в точку
    старта, телемедицина, работа в офисе, расходы дня и компенсации не едут вовсе.
    Собирая «до» сам, офлайн систематически завышал его — и говорил «бери» там, где
    сервер говорил «невыгодно». Теперь считать нечего: число приходит готовым.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Финиш", 30, 20,
                          start_lat=59.930, start_lon=30.310,
                          finish_lat=59.960, finish_lon=30.400)
        # Завершённый заказ — телефон о нём из точек матрицы не узнает.
        done = visits.create_candidate(day.id, "Завершённый", 3000, 0, 0, None, True,
                                       lat=59.935, lon=30.320)
        visits.accept(done.id)
        visits.complete_visit(done.id)
        active = visits.create_candidate(day.id, "Принятый", 1500, 0, 0, None, True,
                                         lat=59.940, lon=30.330)
        visits.accept(active.id)
        # Телемедицина и расходы дня — тоже мимо кеша.
        days.update_money(day.id, "telemed_income", 800)
        days.update_money(day.id, "telemed_minutes", 45)
        days.update_money(day.id, "food_expenses", 350)

        response = MobileVisitService(connection).day_matrix()
        fresh = days.active()
        expected_net, expected_minutes, _, _, _ = calculate_day_profitability(
            fresh,
            visits.list_for_day(day.id, ("accepted", "completed")),
            SettingsRepository(connection),
            DailyStatsRepository(connection),
        )

    assert response["day_before_net"] == expected_net
    assert response["day_before_minutes"] == expected_minutes
    # Доход завершённого заказа и телемедицина обязаны быть внутри — иначе телефон
    # снова окажется оптимистичнее сервера.
    assert response["day_before_net"] > 0
    assert response["day_before_minutes"] >= 45, "минуты телемедицины потерялись"


def test_day_before_subtracts_burned_leads_like_the_verdict(config) -> None:
    """Сгоревшие лиды вычтены из готового «до» — как это делает серверный вердикт.

    calculate_day_profitability считает лиды по ПЕРЕДАННОМУ списку, а отменённых заказов
    в нём нет: вердикт вычитает их отдельной строкой. Отдай телефону «до» без этого
    вычета — и офлайн окажется завышен ровно на сумму сгоревших лидов, всегда в сторону
    оптимизма. Сверка паритета поймала это до выкатки.
    """
    with connect(config) as connection:
        days = WorkDayRepository(connection)
        visits = VisitRepository(connection)
        day = days.create("Дом", "Дом", 30, 20, start_lat=59.930, start_lon=30.310)
        active = visits.create_candidate(day.id, "Принятый", 2000, 0, 0, None, True,
                                         lat=59.940, lon=30.330)
        visits.accept(active.id)
        burned = visits.create_candidate(day.id, "Отменённый", 1500, 0, 0, None, True,
                                         lat=59.950, lon=30.350, response_cost=400)
        visits.accept(burned.id)
        visits.cancel_visit(burned.id)

        with_burned = MobileVisitService(connection).day_matrix()["day_before_net"]

        # Тот же день, но лид ничего не стоил.
        day2 = days.create("Дом", "Дом", 30, 20, start_lat=59.930, start_lon=30.310)
        active2 = visits.create_candidate(day2.id, "Принятый", 2000, 0, 0, None, True,
                                          lat=59.940, lon=30.330)
        visits.accept(active2.id)
        free = visits.create_candidate(day2.id, "Отменённый", 1500, 0, 0, None, True,
                                       lat=59.950, lon=30.350, response_cost=0)
        visits.accept(free.id)
        visits.cancel_visit(free.id)
        without_burned = MobileVisitService(connection).day_matrix()["day_before_net"]

    assert round(without_burned - with_burned, 2) == 400.0, (
        "сгоревший лид не вычтен из готового «до» — офлайн будет оптимистичнее сервера"
    )
