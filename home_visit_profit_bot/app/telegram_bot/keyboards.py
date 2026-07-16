from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Начать день"), KeyboardButton("Добавить адрес")],
            [KeyboardButton("Телемедицина"), KeyboardButton("ОФИС")],
            [KeyboardButton("CBI/выгорание"), KeyboardButton("Корреляции усталости")],
            [KeyboardButton("Принять"), KeyboardButton("Отклонить")],
            [KeyboardButton("Маршрут"), KeyboardButton("Завершить адрес")],
            [KeyboardButton("Отменить адрес"), KeyboardButton("Изменить финиш")],
            [KeyboardButton("Завершить день")],
            [KeyboardButton("Сводка"), KeyboardButton("Статистика"), KeyboardButton("Настройки")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def telemed_clinic_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("ПСК"), KeyboardButton("ДНД")]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите клинику",
    )


def clinic_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Династия"), KeyboardButton("ПСК")],
            [KeyboardButton("ВИТАМЕД"), KeyboardButton("ДНД")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите клинику",
    )


def candidate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Принять", callback_data="accept_candidate"),
                InlineKeyboardButton("Отказаться", callback_data="reject_candidate"),
            ],
            [InlineKeyboardButton("Фраза для клиники", callback_data="candidate_phrase")],
        ]
    )


def stop_classification_keyboard(visit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Обед/пауза", callback_data=f"fatigue_stop:pause:{visit_id}"),
                InlineKeyboardButton("Ожидание", callback_data=f"fatigue_stop:waiting:{visit_id}"),
            ],
            [
                InlineKeyboardButton("Обычный", callback_data=f"fatigue_stop:normal:{visit_id}"),
                InlineKeyboardButton("Тяжёлый", callback_data=f"fatigue_stop:heavy:{visit_id}"),
            ],
            [InlineKeyboardButton("Конфликтный", callback_data=f"fatigue_stop:conflict:{visit_id}")],
        ]
    )


def fatigue_feedback_keyboard(work_day_id: int, predicted_score: float) -> InlineKeyboardMarkup:
    score = int(round(predicted_score))
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Да", callback_data=f"fatigue_feedback:agree:{work_day_id}:{score}"),
                InlineKeyboardButton("Ниже", callback_data=f"fatigue_feedback:lower:{work_day_id}:{score}"),
                InlineKeyboardButton("Выше", callback_data=f"fatigue_feedback:higher:{work_day_id}:{score}"),
            ],
            [InlineKeyboardButton("Ввести число", callback_data=f"fatigue_feedback:manual:{work_day_id}:{score}")],
        ]
    )
