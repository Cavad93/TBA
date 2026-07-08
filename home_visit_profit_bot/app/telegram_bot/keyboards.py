from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Начать день"), KeyboardButton("Добавить адрес")],
            [KeyboardButton("Принять"), KeyboardButton("Отклонить")],
            [KeyboardButton("Маршрут"), KeyboardButton("Завершить адрес")],
            [KeyboardButton("Отменить адрес"), KeyboardButton("Изменить финиш")],
            [KeyboardButton("Завершить день")],
            [KeyboardButton("Сводка"), KeyboardButton("Статистика"), KeyboardButton("Настройки")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
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
