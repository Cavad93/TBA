package com.homevisit.location.notify

import kotlin.math.roundToInt

/**
 * Тексты плановых уведомлений петли удержания (Фаза 7.1–7.3, 5.5). Чистые функции —
 * проверяются JVM-тестом без устройства.
 *
 * Тон — забота, не морализаторство (Ф7.8): уведомление зовёт и заботится, не давит и
 * не стыдит. У каждого — лёгкий выход (отключаемо в настройках, см. ReminderScheduler).
 * Петля тянет к лучшим решениям и отдыху, а не к гринду (душа продукта).
 */
object ReminderMessages {

    data class Message(val title: String, val body: String)

    /** Утро: мягкое приглашение начать смену. Без «давай-давай». */
    fun shiftStart(): Message = Message(
        title = "Штурвал готов",
        body = "Доброе утро. Когда будете готовы — начните смену, чтобы видеть, стоит ли брать заказ.",
    )

    /** Вечер: закрыть день и увидеть ЧИСТЫМИ, а не грязными. */
    fun dayClose(netToday: Double, isPaidOff: Boolean?): Message {
        val money = "${netToday.roundToInt()} ₽ чистыми"
        val tail = when (isPaidOff) {
            true -> " Смена отбита — всё сверху ваше."
            false -> ""
            null -> ""
        }
        return Message(
            title = "Закройте день",
            body = "Сегодня $money.$tail Загляните — сколько реально заработали.",
        )
    }

    /** Раз в неделю: настоящая неделя чистыми (+ сколько уберегли часов, если есть). */
    fun weekly(netWeek: Double, savedHours: Int): Message {
        val saved = if (savedHours > 0) " Уберегли ~$savedHours ч переработки." else ""
        return Message(
            title = "Ваша неделя",
            body = "Чистыми за неделю: ${netWeek.roundToInt()} ₽.$saved Хорошего отдыха.",
        )
    }

    /**
     * ОСАГО (Ф5.5): напоминание за 14/7/1 день и после истечения. null — рано напоминать
     * (или дата не задана): не тревожим зря.
     */
    fun osago(daysLeft: Int, expired: Boolean): Message? {
        if (expired) {
            return Message(
                title = "ОСАГО истёк",
                body = "Полис закончился. Без действующего штрафуют — стоит продлить спокойно.",
            )
        }
        if (daysLeft !in listOf(14, 7, 1)) return null
        val word = when (daysLeft) {
            1 -> "завтра"
            else -> "через $daysLeft ${dayWord(daysLeft)}"
        }
        return Message(
            title = "ОСАГО заканчивается",
            body = "Полис истекает $word. Напомнили заранее — можно продлить без спешки.",
        )
    }

    private fun dayWord(n: Int): String {
        val d10 = n % 10
        val d100 = n % 100
        return when {
            d10 == 1 && d100 != 11 -> "день"
            d10 in 2..4 && d100 !in 12..14 -> "дня"
            else -> "дней"
        }
    }
}
