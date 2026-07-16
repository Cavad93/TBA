from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.repositories import SettingsRepository

# Модель дохода. От неё зависит сам смысл вопроса «стоит ли ехать».
#
# У сдельщика лишний заказ приносит деньги, и вопрос — покрывает ли он дорогу и время.
#
# У окладника лишний заказ НЕ ПРИНОСИТ НИЧЕГО. Он только тратит его топливо и его время.
# Поэтому вердикт «выгодно/невыгодно» для него бессмыслен: выгодных заказов у него не
# бывает вовсе. Осмысленный вопрос другой — укладывается ли он в план и во сколько ему
# самому обходится этот план. И тогда оптимизация маршрута из «приятной мелочи»
# превращается в то, что напрямую экономит его собственные деньги.

INCOME_MODELS: dict[str, str] = {
    "per_order": "Сдельный — плачу́т за заказ",
    "salary": "Оклад и премия",
    "mixed": "Оклад плюс сдельные сверху",
}

DEFAULT_INCOME_MODEL = "per_order"

# Плановых часов в месяце по умолчанию: 40-часовая неделя (ТК РФ, ст. 91).
DEFAULT_MONTH_HOURS = 164.0


@dataclass(frozen=True)
class IncomeModel:
    kind: str
    monthly_salary: float
    monthly_bonus: float
    month_hours: float
    confirmed_month: str | None

    @property
    def is_salary(self) -> bool:
        return self.kind in {"salary", "mixed"}

    @property
    def pays_per_order(self) -> bool:
        return self.kind in {"per_order", "mixed"}

    @property
    def hourly_rate(self) -> float:
        """Во сколько оценивается час по окладу — если оклада нет, ноль."""
        if not self.is_salary or self.month_hours <= 0:
            return 0.0
        return (self.monthly_salary + self.monthly_bonus) / self.month_hours

    def needs_confirmation(self, today: date | None = None) -> bool:
        """Спрашивать оклад раз в месяц — и только подтвердить, а не вводить заново."""
        if not self.is_salary:
            return False
        current = (today or date.today()).strftime("%Y-%m")
        return self.confirmed_month != current

    def payload(self, today: date | None = None) -> dict[str, object]:
        return {
            "kind": self.kind,
            "title": INCOME_MODELS.get(self.kind, INCOME_MODELS[DEFAULT_INCOME_MODEL]),
            "is_salary": self.is_salary,
            "pays_per_order": self.pays_per_order,
            "monthly_salary": round(self.monthly_salary),
            "monthly_bonus": round(self.monthly_bonus),
            "month_hours": round(self.month_hours),
            "hourly_rate": round(self.hourly_rate, 1),
            "needs_confirmation": self.needs_confirmation(today),
            "confirm_text": self._confirm_text(),
        }

    def _confirm_text(self) -> str:
        if not self.is_salary:
            return ""
        # Разделители тысяч заменяем в ЧИСЛАХ, а не во всей фразе: глобальный
        # replace съедал и грамматическую запятую («…₽, премия…» → «…₽  премия…»).
        salary = f"{self.monthly_salary:,.0f}".replace(",", " ")
        bonus = f"{self.monthly_bonus:,.0f}".replace(",", " ")
        return f"Оклад {salary} ₽, премия {bonus} ₽. Всё так же в этом месяце?"


def income_model(settings: SettingsRepository) -> IncomeModel:
    kind = (settings.get("income_model", DEFAULT_INCOME_MODEL) or DEFAULT_INCOME_MODEL).strip()
    if kind not in INCOME_MODELS:
        kind = DEFAULT_INCOME_MODEL
    return IncomeModel(
        kind=kind,
        monthly_salary=max(0.0, settings.get_float("monthly_salary", 0.0)),
        monthly_bonus=max(0.0, settings.get_float("monthly_bonus", 0.0)),
        month_hours=max(1.0, settings.get_float("planned_month_hours", DEFAULT_MONTH_HOURS)),
        confirmed_month=settings.get("income_confirmed_month") or None,
    )


def confirm_month(settings: SettingsRepository, *, today: date | None = None) -> None:
    """Подтвердить, что оклад и премия не изменились. Одна кнопка, без ввода."""
    settings.set("income_confirmed_month", (today or date.today()).strftime("%Y-%m"))


def salary_income_for_shift(model: IncomeModel, work_minutes: float) -> float:
    """Доля месячного оклада, заработанная за эту смену.

    Оклад — это не «доход смены», но и не ноль: он зарабатывается временем. Разносим
    его по отработанным часам, иначе окладник видел бы нулевую выручку и отрицательную
    прибыль каждый день.
    """
    if not model.is_salary or work_minutes <= 0:
        return 0.0
    return model.hourly_rate * (work_minutes / 60)
