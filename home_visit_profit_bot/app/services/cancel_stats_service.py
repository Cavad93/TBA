"""Статистика отмен и пустых откликов (Фаза 11.4).

Платформы не показывают работнику, сколько у него съедают отмены в пути и платные
лиды, которые не стали заказом. Мы показываем это правдой из его же данных:
  - отмены в пути (`cancelled_in_route`) — сумма `cancel_loss` и число, по источникам;
  - пустые отклики — `response_cost` заказов, которые НЕ завершились, по источникам
    (заплатил за лид Профи/Авито, а заказа нет).

Если доля потерь в доходе выше порога (серверная настройка) — деликатный совет о
предоплате. Совет, не приказ: «стоит брать», а не «бери».
"""

from __future__ import annotations

from typing import Any

from app.database import Database

# Доля потерь в доходе, выше которой стоит подсказать про предоплату.
DEFAULT_LOSS_ADVICE_THRESHOLD = 0.10


def _bucket(rows: list[dict[str, Any]], money_key: str) -> dict[str, Any]:
    total_money = 0.0
    total_count = 0
    by_source: dict[str, dict[str, float]] = {}
    for row in rows:
        money = float(row[money_key] or 0)
        if money <= 0:
            continue
        source = row.get("source") or "не указан"
        total_money += money
        total_count += 1
        agg = by_source.setdefault(source, {"count": 0, "money": 0.0})
        agg["count"] += 1
        agg["money"] += money
    return {
        "count": total_count,
        "money": round(total_money, 2),
        "by_source": [
            {"source": src, "count": int(v["count"]), "money": round(v["money"], 2)}
            for src, v in sorted(by_source.items(), key=lambda kv: -kv[1]["money"])
        ],
    }


def cancel_lead_stats(
    connection: Database,
    start_date: str,
    end_date: str,
    *,
    total_income: float,
    threshold: float = DEFAULT_LOSS_ADVICE_THRESHOLD,
) -> dict[str, Any]:
    """Агрегат отмен в пути и пустых откликов за период [start_date, end_date)."""
    raw = connection.execute(
        """
        SELECT v.order_source AS source, v.status AS status,
               v.cancel_loss AS cancel_loss, v.response_cost AS response_cost
        FROM visits v
        JOIN work_days w ON v.work_day_id = w.id
        WHERE w.date >= ? AND w.date < ?
        """,
        (start_date, end_date),
    ).fetchall()
    rows = [dict(r) if not isinstance(r, dict) else r for r in raw]

    cancels = [r for r in rows if r.get("status") == "cancelled_in_route"]
    # Пустой отклик — платный лид у заказа, который НЕ завершился.
    empty_leads = [r for r in rows if r.get("status") != "completed" and float(r.get("response_cost") or 0) > 0]

    cancellations = _bucket(cancels, "cancel_loss")
    leads = _bucket(empty_leads, "response_cost")

    total_loss = cancellations["money"] + leads["money"]
    loss_share = (total_loss / total_income) if total_income > 0 else 0.0

    advice = None
    if total_loss > 0 and loss_share >= threshold:
        advice = (
            f"Отмены и пустые отклики съели {round(loss_share * 100)}% дохода "
            f"({round(total_loss)} ₽). На дальних адресах стоит брать предоплату за выезд."
        )

    return {
        "cancellations": cancellations,
        "empty_leads": leads,
        "loss_total": round(total_loss, 2),
        "loss_share": round(loss_share, 4),
        "advice": advice,
    }
