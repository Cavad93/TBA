package com.homevisit.location.notify

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.homevisit.location.MainActivity
import com.homevisit.location.R
import com.homevisit.location.data.HomeVisitRepository

/**
 * Плановое уведомление петли удержания (Фаза 7.1/7.2, 5.5). Тип приходит в inputData
 * ("kind"). Данные для текста тянем с /api/home. Тон — забота (см. ReminderMessages),
 * лёгкий выход — настройка `reminders_enabled` (по умолчанию вкл): выключил — тишина.
 *
 * Внешние триггеры — локальный WorkManager, не FCM: APK раздаётся мимо Play Store,
 * без Google-сервисов и серверной push-инфраструктуры (решение Джавада).
 */
class ReminderWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val prefs = applicationContext.getSharedPreferences(MainActivity.PREFS, Context.MODE_PRIVATE)
        if (!prefs.getBoolean(KEY_REMINDERS_ENABLED, true)) {
            return Result.success()  // человек отключил — молчим
        }
        val serverUrl = prefs.getString(MainActivity.KEY_SERVER_URL, "").orEmpty()
        val apiKey = prefs.getString(MainActivity.KEY_API_KEY, "").orEmpty()
        if (serverUrl.isBlank() || apiKey.isBlank()) return Result.success()

        val kind = inputData.getString(KEY_KIND) ?: return Result.success()
        val home = HomeVisitRepository.create(applicationContext).fetchHome(serverUrl, apiKey)

        val message = when (kind) {
            KIND_SHIFT_START -> ReminderMessages.shiftStart()
            KIND_DAY_CLOSE -> {
                // Честный чистый ДНЯ, не breakeven.accumulated_net: в том аренда
                // ВОЗВРАЩЕНА для порога, и «Сегодня X ₽ чистыми» врало в плюс ровно
                // на аренду. Нет данных (офлайн без кэша, смены нет) — молчим,
                // а не сочиняем «0 ₽ чистыми».
                val net = home?.todayNet ?: return Result.success()
                val paidOff = home.breakeven?.isPaidOff
                ReminderMessages.dayClose(net, paidOff)
            }
            KIND_OSAGO -> {
                val osago = home?.osago ?: return Result.success()
                ReminderMessages.osago(osago.daysLeft, osago.expired) ?: return Result.success()
            }
            KIND_NEGATIVE_ALERT -> {
                // Только в активную смену и только если реально в минусе (Ф10.3).
                // По честному чистому дня: операционный accumulated_net с
                // возвращённой арендой молчал при реальном минусе на аренду.
                if (home?.shiftActive != true) return Result.success()
                val net = home.todayNet ?: return Result.success()
                ReminderMessages.negativeShift(net) ?: return Result.success()
            }
            KIND_WEEKLY -> {
                // Недельная сводка (Ф7.3): «настоящая неделя чистыми». Тянем week-отчёт.
                val week = HomeVisitRepository.create(applicationContext)
                    .fetchStatsReport(serverUrl, apiKey, com.homevisit.location.domain.ReportPeriod.Week)
                val net = week?.summary?.netProfit ?: return Result.success()
                if (net == 0.0) return Result.success()
                ReminderMessages.weekly(net, savedHours = 0)
            }
            else -> return Result.success()
        }
        notify(kind, message)
        return Result.success()
    }

    private fun notify(kind: String, message: ReminderMessages.Message) {
        ensureChannel()
        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(message.title)
            .setContentText(message.body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message.body))
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()
        runCatching {
            NotificationManagerCompat.from(applicationContext).notify(kind.hashCode(), notification)
        }
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, "Напоминания", NotificationManager.IMPORTANCE_DEFAULT,
            ).apply { description = "Старт смены, закрытие дня, ОСАГО" }
            val manager = applicationContext.getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    companion object {
        const val CHANNEL_ID = "reminders"
        const val KEY_KIND = "kind"
        const val KEY_REMINDERS_ENABLED = "reminders_enabled"
        const val KIND_SHIFT_START = "shift_start"
        const val KIND_DAY_CLOSE = "day_close"
        const val KIND_OSAGO = "osago"
        const val KIND_NEGATIVE_ALERT = "negative_alert"
        const val KIND_WEEKLY = "weekly"
    }
}
