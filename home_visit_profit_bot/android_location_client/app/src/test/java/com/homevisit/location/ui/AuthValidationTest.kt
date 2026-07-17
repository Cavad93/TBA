package com.homevisit.location.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AuthValidationTest {

    @Test
    fun `пустое поле подтверждения не ругается`() {
        // Человек ещё не дошёл до второго поля — ошибки быть не должно.
        assertNull(passwordConfirmError("abcd1234", ""))
    }

    @Test
    fun `несовпадение даёт ошибку у поля`() {
        assertEquals("Пароли не совпадают", passwordConfirmError("abcd1234", "abcd123"))
    }

    @Test
    fun `частичный ввод уже проверяется`() {
        // Ошибка видна с первого несовпадающего символа, а не после сабмита.
        assertEquals("Пароли не совпадают", passwordConfirmError("abcd1234", "x"))
    }

    @Test
    fun `совпадение снимает ошибку`() {
        assertNull(passwordConfirmError("abcd1234", "abcd1234"))
    }
}
