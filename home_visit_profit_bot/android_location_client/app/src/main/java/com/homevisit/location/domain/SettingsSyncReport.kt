package com.homevisit.location.domain

import org.json.JSONObject

/**
 * Итог отправки настроек на сервер.
 *
 * Сервер применяет батч поключево и возвращает в ответе /api/sync блок
 * `settings` со списком отвергнутых полей. Раньше клиент не читал тело ответа
 * вовсе и при любом исходе писал «Настройки сохранены» — человек вводил дату
 * ОСАГО, видел «сохранено», а значение молча исчезало вместе со всем батчем.
 */
data class RejectedSetting(
    val key: String,
    val label: String,
    val reason: String,
)

data class SettingsSyncOutcome(
    /** Дошло ли событие до сервера (сеть была, ответ 2xx). */
    val delivered: Boolean,
    val rejected: List<RejectedSetting> = emptyList(),
)

/** Разбор блока `settings.rejected` из ответа /api/sync (событие settings_saved). */
fun parseRejectedSettings(response: JSONObject?): List<RejectedSetting> {
    val settings = response?.optJSONObject("settings") ?: return emptyList()
    val rejected = settings.optJSONArray("rejected") ?: return emptyList()
    return (0 until rejected.length()).mapNotNull { index ->
        val item = rejected.optJSONObject(index) ?: return@mapNotNull null
        val key = item.optString("key")
        if (key.isBlank()) return@mapNotNull null
        RejectedSetting(
            key = key,
            label = item.optString("label").ifBlank { key },
            reason = item.optString("reason"),
        )
    }
}

/** Честное сообщение после «Сохранить» — вместо безусловного «Настройки сохранены». */
fun settingsSaveMessage(outcome: SettingsSyncOutcome?): String = when {
    outcome == null || !outcome.delivered ->
        "Нет связи с сервером: настройки в очереди и уйдут при синхронизации"
    outcome.rejected.isEmpty() -> "Настройки сохранены"
    else -> {
        val details = outcome.rejected.joinToString("; ") { bad ->
            // Причина с сервера начинается с технического ключа («osago_expires_at: …») —
            // человеку показываем label и текст после двоеточия.
            val reason = bad.reason.substringAfter(": ", bad.reason)
            "${bad.label} — $reason"
        }
        "Сохранено, кроме: $details"
    }
}
