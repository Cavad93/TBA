package com.homevisit.location

import java.time.Duration
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * Время начала и окончания работы на точке.
 *
 * Пользователь вводит только «9:00» и «13:00» — дату и продолжительность считаем
 * сами (принцип: меньше ручного ввода). Серверу уходит полный ISO-момент, потому
 * что по нему выстраивается порядок якорей в маршруте.
 */

private val TIME_INPUT = Regex("""^\s*(\d{1,2})\s*[:.\-\s]?\s*(\d{2})\s*$""")

/** «9:00», «09.00», «0900» → LocalTime. Мусор → null. */
internal fun parseTimeOfDay(value: String): LocalTime? {
    val match = TIME_INPUT.matchEntire(value) ?: return null
    val hour = match.groupValues[1].toIntOrNull() ?: return null
    val minute = match.groupValues[2].toIntOrNull() ?: return null
    if (hour !in 0..23 || minute !in 0..59) return null
    return LocalTime.of(hour, minute)
}

/** Момент сегодняшнего дня в ISO — в таком виде время начала хранит сервер. */
internal fun todayAtIso(time: LocalTime, today: LocalDate = LocalDate.now()): String =
    LocalDateTime.of(today, time).format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)

/**
 * Продолжительность между началом и окончанием. Окончание за полночь (например,
 * с 22:00 до 02:00) считаем следующим днём, а не отрицательным временем.
 */
internal fun minutesBetween(start: LocalTime, end: LocalTime): Long {
    val minutes = Duration.between(start, end).toMinutes()
    return if (minutes >= 0) minutes else minutes + Duration.ofDays(1).toMinutes()
}

/** «09:00» из ISO-момента — для показа в Ленте. */
internal fun timeOfDayText(iso: String?): String? {
    if (iso.isNullOrBlank()) return null
    return runCatching {
        LocalDateTime.parse(iso).toLocalTime().format(DateTimeFormatter.ofPattern("HH:mm"))
    }.getOrNull()
}
