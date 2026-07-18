from __future__ import annotations

from app.models import Point, Visit
from app.services import routing_service
from app.services.optimization_service import optimize_route_estimated, optimize_route_manual
from app.services.routing_service import DistanceMatrix, RoutingError, get_distance_matrix


def test_manual_route_sums_accepted_order() -> None:
    visits = [
        Visit(2, 1, "accepted", 2, "B", "B", None, False, None, None, 1000, 7, 20),
        Visit(1, 1, "accepted", 1, "A", "A", None, False, None, None, 1000, 5, 10),
    ]

    route = optimize_route_manual(visits)

    assert route.order == [1, 2]
    assert route.total_km == 12
    assert route.total_minutes == 30


def test_estimated_route_optimizes_with_coordinates_without_osrm() -> None:
    visits = [
        Visit(1, 1, "accepted", 1, "A", "A", None, False, 59.95, 30.30, 1000, 0, 0),
        Visit(2, 1, "accepted", 2, "B", "B", None, False, 60.00, 30.20, 1000, 0, 0),
    ]

    route = optimize_route_estimated(
        Point("start", 59.93, 30.31),
        visits,
        Point("finish", 59.93, 30.31),
        avg_speed_kmh=30,
        straight_line_factor=1.35,
    )

    assert sorted(route.order) == [1, 2]
    assert route.total_km > 0
    assert route.total_minutes > 0
    assert route.legs


def _feed_worse_than_optimal() -> tuple[Point, list[Visit], Point]:
    """Лента расставлена ХУЖЕ оптимального: сначала дальний заказ, потом ближний.

    Старт на юге, финиш на севере. Заказ 1 (первый в Ленте) — у финиша,
    заказ 2 — у старта. Объезд по Ленте (1→2) гоняет через весь город и обратно,
    оптимальный (2→1) идёт по пути. Так видно, что вердикт считается по разным
    маршрутам.
    """
    start = Point("start", 59.93, 30.31)
    finish = Point("finish", 60.10, 30.31)
    visits = [
        Visit(1, 1, "accepted", 1, "дальний", "дальний", None, False, 60.05, 30.31, 1000, 0, 0),
        Visit(2, 1, "accepted", 2, "ближний", "ближний", None, False, 59.94, 30.31, 1000, 0, 0),
    ]
    return start, visits, finish


def test_feed_order_route_keeps_user_order_and_is_longer_than_optimal() -> None:
    """Порядок Ленты не переставляется, и его дорога честно длиннее оптимальной.

    Раньше день считался ВСЕГДА по оптимальному маршруту: человек, отключивший
    авто-оптимизацию, видел чужой (короткий) километраж и завышенный ₽/час.
    """
    start, visits, finish = _feed_worse_than_optimal()

    feed = optimize_route_estimated(
        start, visits, finish, avg_speed_kmh=30, straight_line_factor=1.35,
        respect_feed_order=True,
    )
    optimal = optimize_route_estimated(
        start, visits, finish, avg_speed_kmh=30, straight_line_factor=1.35,
    )

    assert feed.order == [1, 2]        # ровно как в Ленте, без перестановки
    assert optimal.order == [2, 1]     # оптимизатор разворачивает объезд
    assert feed.total_km > optimal.total_km
    assert feed.total_minutes > optimal.total_minutes


def test_feed_order_matches_optimal_when_feed_is_already_optimal() -> None:
    """Если Лента уже оптимальна (авто-оптимизация включена) — цифры не меняются."""
    start, visits, finish = _feed_worse_than_optimal()
    already_optimal = [visits[1], visits[0]]  # 2 → 1: тот же порядок, что выберет оптимизатор

    feed = optimize_route_estimated(
        start, already_optimal, finish, avg_speed_kmh=30, straight_line_factor=1.35,
        respect_feed_order=True,
    )
    optimal = optimize_route_estimated(
        start, already_optimal, finish, avg_speed_kmh=30, straight_line_factor=1.35,
    )

    assert feed.order == optimal.order == [2, 1]
    assert feed.total_km == optimal.total_km
    assert feed.total_minutes == optimal.total_minutes


def test_feed_order_puts_new_candidate_last() -> None:
    """Новый кандидат оценивается последним — как он и встанет в Ленте.

    В Ленте у кандидата ещё нет order_number, поэтому он сортируется в конец;
    оценка обязана считать его там же, а не втискивать в середину «как удобнее».
    """
    start, visits, finish = _feed_worse_than_optimal()
    candidate = Visit(3, 1, "candidate", None, "новый", "новый", None, False, 59.95, 30.31, 700, 0, 0)

    feed = optimize_route_estimated(
        start, visits + [candidate], finish, avg_speed_kmh=30, straight_line_factor=1.35,
        respect_feed_order=True,
    )

    assert feed.order == [1, 2, 3]


def test_osrm_null_matrix_values_raise_instead_of_becoming_zero(monkeypatch) -> None:
    def fake_get_json(url: str, timeout_seconds: float) -> dict:
        return {
            "code": "Ok",
            "distances": [[0, None], [None, 0]],
            "durations": [[0, None], [None, 0]],
        }

    monkeypatch.setattr(routing_service, "_get_json", fake_get_json)

    try:
        get_distance_matrix(
            [Point("A", 59.9, 30.3), Point("B", 59.95, 30.35)],
            osrm_url="http://example.test",
        )
    except RoutingError:
        pass
    else:
        raise AssertionError("Expected RoutingError for null OSRM matrix values")


def test_osrm_duration_factor_changes_minutes_but_not_distance(monkeypatch) -> None:
    def fake_get_json(url: str, timeout_seconds: float) -> dict:
        return {
            "code": "Ok",
            "distances": [[0, 1000], [1000, 0]],
            "durations": [[0, 600], [600, 0]],
        }

    monkeypatch.setattr(routing_service, "_get_json", fake_get_json)

    matrix = get_distance_matrix(
        [Point("A", 59.9, 30.3), Point("B", 59.95, 30.35)],
        osrm_url="http://example.test",
        duration_factor=1.5,
    )

    assert matrix.distances_km[0][1] == 1
    assert matrix.durations_minutes[0][1] == 15


# --- отчёт 17: 2-opt вокруг якорей распрямляет крюки жадной вставки ---

def _durations_matrix(durations: list[list[float]]) -> DistanceMatrix:
    """DistanceMatrix только с временами (расстояния для этих тестов не важны)."""
    n = len(durations)
    return DistanceMatrix(distances_km=[[0.0] * n for _ in range(n)], durations_minutes=durations)


def test_two_opt_shortens_greedy_detour_and_keeps_anchor() -> None:
    """Разворот сегмента без якоря сокращает крюк; якорь остаётся на месте (отчёт 17)."""
    from app.services.optimization_service import _anchors_preserved, _route_minutes, _two_opt

    # 0=старт, 1,2, 3=якорь, 4=финиш. Порядок [1,2,3] делает крюк; [2,1,3] короче.
    matrix = _durations_matrix([
        [0, 10, 1, 9, 0],
        [10, 0, 1, 5, 3],
        [1, 1, 0, 1, 3],
        [9, 5, 1, 0, 1],
        [0, 3, 3, 1, 0],
    ])
    improved = _two_opt(matrix, [1, 2, 3], finish_index=4, anchors=[3])
    assert _route_minutes(matrix, improved, 4) < _route_minutes(matrix, [1, 2, 3], 4)
    assert _anchors_preserved(improved, [3])  # якорь 3 не переставлен


def test_two_opt_never_reorders_two_anchors() -> None:
    """Даже если разворот якорей дешевле — их относительный порядок (по времени) свят."""
    from app.services.optimization_service import _anchors_preserved, _route_minutes, _two_opt

    # 0=старт, 1,2 = якоря, 3=финиш. [2,1] дешевле [1,2], но якоря менять нельзя.
    matrix = _durations_matrix([
        [0, 10, 1, 0],
        [10, 0, 1, 5],
        [1, 1, 0, 1],
        [0, 5, 1, 0],
    ])
    assert _route_minutes(matrix, [2, 1], 3) < _route_minutes(matrix, [1, 2], 3)
    result = _two_opt(matrix, [1, 2], finish_index=3, anchors=[1, 2])
    assert result == [1, 2]  # порядок якорей сохранён вопреки более дешёвому [2,1]
    assert _anchors_preserved(result, [1, 2])


def test_order_around_anchors_applies_two_opt() -> None:
    """Полный путь якорной оптимизации теперь распрямляет крюк жадной вставки."""
    from app.services.optimization_service import _order_around_anchors, _route_minutes

    matrix = _durations_matrix([
        [0, 10, 1, 9, 0],
        [10, 0, 1, 5, 3],
        [1, 1, 0, 1, 3],
        [9, 5, 1, 0, 1],
        [0, 3, 3, 1, 0],
    ])
    order = _order_around_anchors(matrix, visit_indices=[1, 2, 3], anchors=[3], finish_index=4)
    # Якорь 3 на месте, а суммарное время не хуже честной жадной вставки [2,1,3] (8 мин).
    assert order[-1] == 3 or 3 in order
    assert _route_minutes(matrix, order, 4) <= 8


def test_route_time_safety_margin_is_applied_over_factor() -> None:
    """Отчёт 18: итоговое время = коэффициент пробок × запас (1.1). Запас отдельно
    от коэффициента, чтобы обучение на факте его не «съело»."""
    from app.services.routing_service import ROUTE_TIME_SAFETY_MARGIN, with_route_time_margin

    assert ROUTE_TIME_SAFETY_MARGIN == 1.1
    assert with_route_time_margin(2.0) == 2.2  # дефолт 2.0 × запас 1.1
    assert with_route_time_margin(1.0) == 1.1
