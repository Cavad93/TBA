package com.homevisit.location.domain

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Отчёт сервера об отвергнутых настройках и честное сообщение человеку.
 *
 * Регресс жалобы «в настройках пишу — не сохраняется»: клиент не читал тело
 * ответа /api/sync и при любом исходе писал «Настройки сохранены».
 */
class SettingsSyncReportTest {

    @Test
    fun `разбор блока rejected из ответа сервера`() {
        val response = JSONObject(
            """
            {"ok": true, "settings": {"updated": ["auto_open_navigator"],
             "rejected": [{"key": "osago_expires_at", "label": "Дата окончания ОСАГО",
                           "reason": "osago_expires_at: дата в формате ДД.ММ.ГГГГ или ГГГГ-ММ-ДД"}],
             "ignored": []}}
            """.trimIndent()
        )

        val rejected = parseRejectedSettings(response)

        assertEquals(1, rejected.size)
        assertEquals("osago_expires_at", rejected[0].key)
        assertEquals("Дата окончания ОСАГО", rejected[0].label)
        assertTrue(rejected[0].reason.contains("формате"))
    }

    @Test
    fun `нет блока settings — пустой список, не падение`() {
        assertEquals(emptyList<RejectedSetting>(), parseRejectedSettings(JSONObject("""{"ok": true}""")))
        assertEquals(emptyList<RejectedSetting>(), parseRejectedSettings(null))
        // settings: null приходит для всех событий, кроме settings_saved
        assertEquals(
            emptyList<RejectedSetting>(),
            parseRejectedSettings(JSONObject("""{"ok": true, "settings": null}""")),
        )
    }

    @Test
    fun `сообщение — правда по каждому исходу`() {
        // Не дошло (офлайн/ошибка сети): раньше тут тоже писалось «сохранены».
        assertEquals(
            "Нет связи с сервером: настройки в очереди и уйдут при синхронизации",
            settingsSaveMessage(null),
        )
        assertEquals(
            "Нет связи с сервером: настройки в очереди и уйдут при синхронизации",
            settingsSaveMessage(SettingsSyncOutcome(delivered = false)),
        )
        // Всё применилось.
        assertEquals("Настройки сохранены", settingsSaveMessage(SettingsSyncOutcome(delivered = true)))
        // Частичный отказ: имя поля и причина без технического ключа.
        val partial = settingsSaveMessage(
            SettingsSyncOutcome(
                delivered = true,
                rejected = listOf(
                    RejectedSetting(
                        key = "osago_expires_at",
                        label = "Дата окончания ОСАГО",
                        reason = "osago_expires_at: дата в формате ДД.ММ.ГГГГ или ГГГГ-ММ-ДД",
                    )
                ),
            )
        )
        assertEquals(
            "Сохранено, кроме: Дата окончания ОСАГО — дата в формате ДД.ММ.ГГГГ или ГГГГ-ММ-ДД",
            partial,
        )
    }
}
