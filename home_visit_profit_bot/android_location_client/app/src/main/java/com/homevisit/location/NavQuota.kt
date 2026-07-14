package com.homevisit.location

import android.content.Context
import java.util.Calendar

/**
 * Пять переходов в сутки — столько Яндекс пускает по ссылке без ключа доступа.
 *
 * Шестой переход открыл бы не навигатор, а страницу в браузере: человек ткнул бы
 * «Поехали», увидел рекламную страницу и решил, что сломались мы. Поэтому считаем
 * переходы сами и на шестом честно говорим, что запуск исчерпан, — а координаты
 * кладём в буфер обмена, чтобы уехать всё-таки можно было.
 *
 * Как только Яндекс выдаст ключ, сервер начнёт подписывать ссылки, `signed` придёт
 * true — и счётчик выключится сам, без обновления приложения.
 */
object NavQuota {

    /** Лимит Яндекса. Не наш выбор — их правило. */
    const val DAILY_LIMIT = 5

    /** Меньше этого остатка — предупреждаем заранее, а не по факту тупика. */
    const val WARN_BELOW = 3

    private const val PREFS = "nav_quota"
    private const val KEY_DAY = "day"
    private const val KEY_COUNT = "count"

    /** Сколько переходов осталось сегодня. С подписью лимита нет вовсе. */
    fun remaining(context: Context, signed: Boolean): Int {
        if (signed) return Int.MAX_VALUE
        return (DAILY_LIMIT - used(context)).coerceAtLeast(0)
    }

    fun exhausted(context: Context, signed: Boolean): Boolean = remaining(context, signed) <= 0

    /** Отметить состоявшийся переход. Вызывать только если навигатор реально открылся. */
    fun record(context: Context, signed: Boolean) {
        if (signed) return
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        prefs.edit().putInt(KEY_DAY, today()).putInt(KEY_COUNT, used(context) + 1).apply()
    }

    private fun used(context: Context): Int {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        // Счёт ведётся посуточно: сменился день — счётчик обнулился.
        if (prefs.getInt(KEY_DAY, 0) != today()) return 0
        return prefs.getInt(KEY_COUNT, 0)
    }

    private fun today(): Int {
        val calendar = Calendar.getInstance()
        return calendar.get(Calendar.YEAR) * 1000 + calendar.get(Calendar.DAY_OF_YEAR)
    }
}
