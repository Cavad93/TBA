from __future__ import annotations

from dataclasses import dataclass

# Состояние меняет экономическое решение — это и есть смысл продукта.
# Навигатор показывает, куда ехать; мы показываем, стоит ли ехать — а «стоит ли»
# зависит не только от километров, но и от того, чем человек за эту поездку заплатит.
#
# Механизм ровно один: при высоком долге восстановления поднимается МИНИМАЛЬНЫЙ ТАРИФ.
# Не «надбавка сверху», не «штраф», не отдельная строка — именно порог, ниже которого
# заказ не проходит. Так человек видит понятное: «обычный минимум 900 ₽/ч, сегодня —
# 1 150 ₽/ч». Раньше в системе жила параллельная «надбавка за нагрузку»: она считалась
# на сервере, доезжала до телефона и нигде не показывалась. Держать оба механизма
# нельзя — они складываются, и заказ дорожает дважды.

OVERWORK_MARKUP_STEPS: list[tuple[float, float]] = [
    (40, 0.00),   # норма и лёгкая нагрузка — обычный режим
    (60, 0.10),   # усталость накапливается — повышаем минимальную ставку
    (80, 0.25),   # высокий долг — дешёвые и дальние заказы не проходят
    (100, 0.40),  # критический перегруз — только самые выгодные и короткие
]

# Начиная с этого долга заказ вне базовой зоны не может получить вердикт «стоит ехать»:
# дальняя дорога на исходе ресурса — это не вопрос денег.
OUTSIDE_ZONE_BLOCK_DEBT = 61.0


@dataclass(frozen=True)
class OverworkPricing:
    """Во что состояние обходится заказу — в тех же рублях за час."""

    debt: float
    markup: float
    base_min_hourly: float
    effective_min_hourly: float
    base_outside_min_hourly: float
    effective_outside_min_hourly: float
    base_min_marginal_hourly: float
    effective_min_marginal_hourly: float
    blocks_outside_zone: bool
    reason: str

    @property
    def changed(self) -> bool:
        return self.markup > 0

    def payload(self) -> dict[str, object]:
        return {
            "debt": round(self.debt, 1),
            "markup_percent": round(self.markup * 100),
            "base_min_hourly": round(self.base_min_hourly),
            "effective_min_hourly": round(self.effective_min_hourly),
            "changed": self.changed,
            "blocks_outside_zone": self.blocks_outside_zone,
            "reason": self.reason,
        }


def overwork_markup(debt: float) -> float:
    for threshold, markup in OVERWORK_MARKUP_STEPS:
        if debt <= threshold:
            return markup
    return OVERWORK_MARKUP_STEPS[-1][1]


def build_pricing(
    *,
    debt: float,
    min_hourly: float,
    outside_min_hourly: float,
    min_marginal_hourly: float,
) -> OverworkPricing:
    markup = overwork_markup(debt)
    factor = 1 + markup
    blocks = debt >= OUTSIDE_ZONE_BLOCK_DEBT
    return OverworkPricing(
        debt=debt,
        markup=markup,
        base_min_hourly=min_hourly,
        effective_min_hourly=min_hourly * factor,
        base_outside_min_hourly=outside_min_hourly,
        effective_outside_min_hourly=outside_min_hourly * factor,
        base_min_marginal_hourly=min_marginal_hourly,
        effective_min_marginal_hourly=min_marginal_hourly * factor,
        blocks_outside_zone=blocks,
        reason=_reason(debt, markup, min_hourly, min_hourly * factor, blocks),
    )


def _reason(debt: float, markup: float, base: float, effective: float, blocks: bool) -> str:
    if markup <= 0:
        return "Долг восстановления в норме — минимальный тариф обычный."
    text = (
        f"Долг восстановления {debt:.0f} из 100. "
        f"Обычный минимум {base:.0f} ₽/ч, сегодня — {effective:.0f} ₽/ч (+{markup * 100:.0f}%)."
    )
    if blocks:
        text += " Заказы вне зоны сегодня лучше не брать."
    return text
