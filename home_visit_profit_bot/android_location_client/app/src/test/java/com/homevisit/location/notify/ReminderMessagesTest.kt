package com.homevisit.location.notify

import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Тексты плановых уведомлений (Ф7.1-7.3, 5.5): тон заботы, числа — из данных дня.
 * ОСАГО напоминает только на 14/7/1 день и после истечения, иначе молчит.
 */
class ReminderMessagesTest {

    @Test
    fun dayCloseShowsNetMoney() {
        val m = ReminderMessages.dayClose(netToday = 1234.0, isPaidOff = true)
        assertTrue(m.body.contains("1234 ₽ чистыми"))
        assertTrue(m.body.contains("отбита"))
    }

    @Test
    fun weeklyShowsNetAndSavedHours() {
        val m = ReminderMessages.weekly(netWeek = 25000.0, savedHours = 6)
        assertTrue(m.body.contains("25000 ₽"))
        assertTrue(m.body.contains("6 ч"))
    }

    @Test
    fun osagoRemindsOnlyAtThresholds() {
        assertNull("на 10 дней не тревожим", ReminderMessages.osago(10, expired = false))
        assertTrue(ReminderMessages.osago(14, expired = false)!!.body.contains("14 дней"))
        assertTrue(ReminderMessages.osago(1, expired = false)!!.body.contains("завтра"))
        assertTrue(ReminderMessages.osago(0, expired = true)!!.title.contains("истёк"))
    }

    @Test
    fun negativeShiftAlertsOnlyInTheRed() {
        assertNull("в плюсе — молчим", ReminderMessages.negativeShift(500.0))
        assertNull("ноль — молчим", ReminderMessages.negativeShift(0.0))
        val m = ReminderMessages.negativeShift(-320.0)!!
        assertTrue(m.body.contains("-320 ₽"))
        assertTrue(m.title.contains("минус"))
    }

    @Test
    fun shiftStartIsCaringNotPushy() {
        val m = ReminderMessages.shiftStart()
        assertTrue(m.title.isNotBlank())
        // Без «давай-давай»/приказов — забота.
        assertTrue(m.body.contains("Когда будете готовы"))
    }
}
