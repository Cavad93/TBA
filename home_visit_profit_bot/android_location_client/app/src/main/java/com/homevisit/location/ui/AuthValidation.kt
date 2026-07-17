package com.homevisit.location.ui

/**
 * Ошибка поля «Повтори пароль» или null, если ругаться не на что.
 *
 * Пока второе поле пустое — молчим: ругать человека за поле, до которого он
 * ещё не дошёл, — шум. Ошибка появляется с первого несовпадающего символа
 * и исчезает, как только пароли сошлись.
 */
fun passwordConfirmError(password: String, confirm: String): String? =
    if (confirm.isNotEmpty() && confirm != password) "Пароли не совпадают" else null
