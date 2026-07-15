"""Пул соединений не имеет права протечь чужими данными между пользователями.

Соединение из пула переиспользуется. Пользователя мы включаем через session-scope GUC
`app.user_id` (он должен пережить несколько commit внутри запроса). Значит при возврате
соединения в пул GUC ОБЯЗАН сброситься — иначе следующий запрос увидит чужие
персональные данные. Это тест ровно на это, и он нарочно зажимает пул до ОДНОГО
соединения (max_size=1), чтобы все запросы делили его и протечка, если она есть,
вылезла немедленно.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

from app.config import AppConfig
from app.database import connect, current_user_id
from app.pool import build_pool, db_from_pool
from app.repositories import VisitRepository, WorkDayRepository
from app.services.auth_service import AuthService


def _make_user(config: AppConfig, email: str) -> int:
    with connect(config) as conn:
        service = AuthService(conn, config)
        service.register(email, "supersecret", "Ник")
        service.verify_email(email, "123456")
        return service.users.get_by_email(email)["id"]


@contextmanager
def _db(pool, user_id):
    gen = db_from_pool(pool, user_id)
    db = next(gen)
    try:
        yield db
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_single_connection_does_not_leak_user_between_requests(fresh_db) -> None:
    config = fresh_db
    user_a = _make_user(config, "a@x.com")
    user_b = _make_user(config, "b@x.com")

    # ОДНО соединение на весь пул: A и B получат физически один и тот же сокет.
    pool = build_pool(config, min_size=1, max_size=1)
    pool.open()
    try:
        # A заводит день и визит.
        with _db(pool, user_a) as db:
            day_a = WorkDayRepository(db).create("Дом A", "Дом A", 30, 20)
            VisitRepository(db).create_candidate(day_a.id, "Адрес A", 1000, 0, 0, None, True, clinic="К")

        # B на ТОМ ЖЕ соединении не видит ничего от A.
        with _db(pool, user_b) as db:
            visits_b = db.execute("SELECT count(*) AS c FROM visits").fetchone()["c"]
            days_b = db.execute("SELECT count(*) AS c FROM work_days").fetchone()["c"]
            assert visits_b == 0, f"B видит {visits_b} чужих визитов — GUC протёк"
            assert days_b == 0, f"B видит {days_b} чужих дней — GUC протёк"

        # A по-прежнему видит только своё.
        with _db(pool, user_a) as db:
            days_a = db.execute("SELECT count(*) AS c FROM work_days").fetchone()["c"]
            assert days_a == 1
    finally:
        pool.close()


def test_reset_clears_guc_to_empty(fresh_db) -> None:
    """После возврата соединения app.user_id обязан стать пустым, не прежним."""
    config = fresh_db
    user_a = _make_user(config, "a@x.com")
    pool = build_pool(config, min_size=1, max_size=1)
    pool.open()
    try:
        with _db(pool, user_a) as db:
            got = db.execute("SELECT current_setting('app.user_id', true) AS u").fetchone()["u"]
            assert got == str(user_a)
        # Берём соединение снова без пользователя — GUC уже пуст.
        with _db(pool, None) as db:
            got = db.execute("SELECT current_setting('app.user_id', true) AS u").fetchone()["u"]
            assert got in ("", None), f"GUC не сброшен: {got!r}"
    finally:
        pool.close()


def test_concurrent_users_stay_isolated(fresh_db) -> None:
    """Много потоков, у каждого свой пользователь — никто не видит чужие визиты."""
    config = fresh_db
    users = [_make_user(config, f"u{i}@x.com") for i in range(6)]

    # Каждый заводит день + один визит (под своим user_id, через прямое соединение —
    # это подготовка данных, не предмет теста).
    for uid in users:
        current_user_id.set(uid)
        with connect(config) as conn:
            day = WorkDayRepository(conn).create("Дом", "Дом", 30, 20)
            VisitRepository(conn).create_candidate(day.id, "Адрес", 1000, 0, 0, None, True, clinic="К")
    current_user_id.set(None)

    pool = build_pool(config, min_size=2, max_size=4)
    pool.open()
    errors: list[str] = []
    barrier = threading.Barrier(len(users))

    def worker(uid: int) -> None:
        try:
            barrier.wait()
            for _ in range(5):
                with _db(pool, uid) as db:
                    rows = db.execute("SELECT count(*) AS c FROM visits").fetchone()["c"]
                    if rows != 1:
                        errors.append(f"user {uid} увидел {rows} визитов вместо 1")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"user {uid}: {exc}")

    threads = [threading.Thread(target=worker, args=(uid,)) for uid in users]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        pool.close()

    assert not errors, "; ".join(errors)
