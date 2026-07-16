package com.homevisit.location.notify

import android.content.Context
import androidx.work.Data
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.Calendar
import java.util.concurrent.TimeUnit

/**
 * Расписание плановых уведомлений петли удержания (Фаза 7.1/7.2, 5.5).
 *
 * Каждый тип — суточная периодическая работа с начальной задержкой до нужного часа:
 * утро (старт смены), вечер (закрытие дня), день (проверка ОСАГО). Внешние триггеры —
 * локальный WorkManager, без FCM/Google-сервисов. Отключается настройкой
 * `reminders_enabled` (сам воркер молчит, см. ReminderWorker) — «лёгкий выход» (Ф7.8).
 */
object ReminderScheduler {

    private const val WORK_SHIFT_START = "reminder_shift_start"
    private const val WORK_DAY_CLOSE = "reminder_day_close"
    private const val WORK_OSAGO = "reminder_osago"
    private const val WORK_NEGATIVE = "reminder_negative_alert"
    private const val WORK_WEEKLY = "reminder_weekly"

    fun schedule(context: Context, now: Calendar = Calendar.getInstance()) {
        enqueueDaily(context, WORK_SHIFT_START, ReminderWorker.KIND_SHIFT_START, targetHour = 9, now = now)
        enqueueDaily(context, WORK_DAY_CLOSE, ReminderWorker.KIND_DAY_CLOSE, targetHour = 20, now = now)
        enqueueDaily(context, WORK_OSAGO, ReminderWorker.KIND_OSAGO, targetHour = 10, now = now)
        // Проверка «смена в минусе» — середина дня (Ф10.3): кричим днём, а не вечером.
        enqueueDaily(context, WORK_NEGATIVE, ReminderWorker.KIND_NEGATIVE_ALERT, targetHour = 15, now = now)
        // Недельная сводка (Ф7.3): раз в 7 дней вечером — «настоящая неделя чистыми».
        enqueuePeriodic(context, WORK_WEEKLY, ReminderWorker.KIND_WEEKLY, targetHour = 19, days = 7, now = now)
    }

    /** Отменить все напоминания (например, при выходе из аккаунта). */
    fun cancelAll(context: Context) {
        val wm = WorkManager.getInstance(context)
        wm.cancelUniqueWork(WORK_SHIFT_START)
        wm.cancelUniqueWork(WORK_DAY_CLOSE)
        wm.cancelUniqueWork(WORK_OSAGO)
        wm.cancelUniqueWork(WORK_NEGATIVE)
        wm.cancelUniqueWork(WORK_WEEKLY)
    }

    private fun enqueueDaily(context: Context, workName: String, kind: String, targetHour: Int, now: Calendar) =
        enqueuePeriodic(context, workName, kind, targetHour, days = 1, now = now)

    private fun enqueuePeriodic(context: Context, workName: String, kind: String, targetHour: Int, days: Long, now: Calendar) {
        val request = PeriodicWorkRequestBuilder<ReminderWorker>(days, TimeUnit.DAYS)
            .setInitialDelay(initialDelayMinutes(now, targetHour), TimeUnit.MINUTES)
            .setInputData(Data.Builder().putString(ReminderWorker.KEY_KIND, kind).build())
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            workName,
            // KEEP: не сбрасываем уже стоящее расписание на каждом запуске приложения.
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }

    /** Минут до ближайшего наступления targetHour:00 (сегодня или завтра). Чистая, тестируемая. */
    fun initialDelayMinutes(now: Calendar, targetHour: Int): Long {
        val target = (now.clone() as Calendar).apply {
            set(Calendar.HOUR_OF_DAY, targetHour)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        if (!target.after(now)) {
            target.add(Calendar.DAY_OF_MONTH, 1)
        }
        return (target.timeInMillis - now.timeInMillis) / 60000L
    }
}
