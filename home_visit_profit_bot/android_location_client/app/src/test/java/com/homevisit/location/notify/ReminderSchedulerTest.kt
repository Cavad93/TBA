package com.homevisit.location.notify

import org.junit.Assert.assertEquals
import org.junit.Test
import java.util.Calendar

/**
 * Расписание напоминаний (Ф7): задержка до ближайшего целевого часа — сегодня, если
 * он ещё впереди, иначе завтра.
 */
class ReminderSchedulerTest {

    private fun at(hour: Int, minute: Int): Calendar =
        Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, hour)
            set(Calendar.MINUTE, minute)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }

    @Test
    fun delayToLaterToday() {
        // 08:00, цель 9:00 → 60 минут.
        assertEquals(60L, ReminderScheduler.initialDelayMinutes(at(8, 0), 9))
    }

    @Test
    fun delayRollsToTomorrowWhenPassed() {
        // 10:00, цель 9:00 → до завтрашних 9:00 = 23 ч = 1380 мин.
        assertEquals(23 * 60L, ReminderScheduler.initialDelayMinutes(at(10, 0), 9))
    }

    @Test
    fun delayHalfHourBefore() {
        // 19:30, цель 20:00 → 30 минут.
        assertEquals(30L, ReminderScheduler.initialDelayMinutes(at(19, 30), 20))
    }
}
