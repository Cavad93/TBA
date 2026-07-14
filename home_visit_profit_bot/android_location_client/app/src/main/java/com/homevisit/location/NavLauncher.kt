package com.homevisit.location

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import com.homevisit.location.domain.NavTarget

/**
 * Отдать маршрут навигатору.
 *
 * Ссылка приходит с сервера уже собранной и подписанной — телефон её только
 * открывает. Здесь остаётся одна работа: аккуратно деградировать, если нужного
 * приложения на телефоне нет.
 *
 * Лестница отступления:
 *   1. Яндекс тем приложением, которое выбрано в настройках.
 *   2. Второе приложение Яндекса — Карты вместо Навигатора и наоборот: обе схемы
 *      понимают одна другую хуже, чем хотелось бы, но открыть ссылку любой из них
 *      всё равно лучше, чем не открыть ничего.
 *   3. Системная схема geo: — любое картографическое приложение на телефоне.
 *   4. Ничего не вышло — говорим об этом словами, а не молчим.
 */
object NavLauncher {

    /** Что произошло при попытке уехать. UI по этому решает, что сказать человеку. */
    enum class Result { OpenedChosen, OpenedOther, OpenedFallback, NothingInstalled }

    private val YANDEX_PACKAGES = listOf("ru.yandex.yandexnavi", "ru.yandex.yandexmaps")

    fun open(context: Context, target: NavTarget): Result {
        if (target.url.isNotBlank()) {
            if (start(context, target.url, target.packageName)) return Result.OpenedChosen
            // Тот же URL, но без привязки к пакету: пусть система сама решит, кто его откроет.
            if (start(context, target.url, packageName = null)) return Result.OpenedOther
        }
        if (target.fallbackUrl.isNotBlank() && start(context, target.fallbackUrl, packageName = null)) {
            return Result.OpenedFallback
        }
        return Result.NothingInstalled
    }

    /** Установлен ли на телефоне хоть один Яндекс. Нужно, чтобы не обещать лишнего. */
    fun hasYandex(context: Context): Boolean = YANDEX_PACKAGES.any { packageName ->
        val probe = Intent(Intent.ACTION_VIEW, Uri.parse("yandexnavi://build_route_on_map"))
            .setPackage(packageName)
        probe.resolveActivity(context.packageManager) != null ||
            context.packageManager.getLaunchIntentForPackage(packageName) != null
    }

    private fun start(context: Context, url: String, packageName: String?): Boolean {
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
            // Навигатор запускается поверх нас как отдельная задача — иначе кнопка
            // «назад» из Яндекса вернёт не туда, откуда ушли.
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            if (!packageName.isNullOrBlank()) setPackage(packageName)
        }
        if (intent.resolveActivity(context.packageManager) == null) return false
        return try {
            context.startActivity(intent)
            true
        } catch (error: ActivityNotFoundException) {
            // Между проверкой и запуском приложение могли удалить. Редко, но бывает.
            false
        }
    }
}
