package com.homevisit.location

import com.homevisit.location.domain.SettingField
import com.homevisit.location.domain.SettingType
import com.homevisit.location.domain.SettingsSection
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * Сбор изменений настроек: дата ОСАГО и очистка.
 *
 * Регресс жалобы владельца: «16.07.2027» в поле даты топило весь батч
 * (сервер знал только ISO), а стёртую дату вообще нельзя было отправить.
 */
class SettingsChangesTest {

    private fun dateSection(current: String = "") = listOf(
        SettingsSection(
            key = "osago",
            title = "ОСАГО",
            fields = listOf(
                SettingField(
                    key = "osago_expires_at",
                    label = "Дата окончания ОСАГО",
                    type = SettingType.Date,
                    textValue = current,
                )
            ),
        )
    )

    @Test
    fun `человеческая дата нормализуется в ISO ещё на клиенте`() {
        for (raw in listOf("16.07.2027", "16/07/2027", "16-07-2027", "2027-07-16")) {
            val changes = collectSettingsChanges(
                sections = dateSection(),
                textEdits = mapOf("osago_expires_at" to raw),
                boolEdits = emptyMap(),
            )
            assertEquals(raw, "2027-07-16", changes["osago_expires_at"])
        }
    }

    @Test
    fun `нераспознанная дата уходит как есть — отказ покажет сервер`() {
        // Молча выбрасывать ввод нельзя: человек должен увидеть причину отказа.
        val changes = collectSettingsChanges(
            sections = dateSection(),
            textEdits = mapOf("osago_expires_at" to "когда-нибудь"),
            boolEdits = emptyMap(),
        )
        assertEquals("когда-нибудь", changes["osago_expires_at"])
    }

    @Test
    fun `стёртая дата отправляется пустой — продал машину, убрал напоминание`() {
        val changes = collectSettingsChanges(
            sections = dateSection(current = "2026-01-01"),
            textEdits = mapOf("osago_expires_at" to ""),
            boolEdits = emptyMap(),
        )
        assertEquals("", changes["osago_expires_at"])
    }

    @Test
    fun `нетронутая дата не отправляется`() {
        val changes = collectSettingsChanges(
            sections = dateSection(current = "2026-01-01"),
            textEdits = emptyMap(),
            boolEdits = emptyMap(),
        )
        assertFalse(changes.containsKey("osago_expires_at"))
    }

    @Test
    fun `normalizeDateInput — границы`() {
        assertEquals("2027-07-16", normalizeDateInput("16.07.2027"))
        assertEquals("2027-07-06", normalizeDateInput("6.7.2027"))
        assertEquals("2027-07-16", normalizeDateInput("2027-7-16"))
        assertNull(normalizeDateInput("32.07.2027"))
        assertNull(normalizeDateInput("16.13.2027"))
        assertNull(normalizeDateInput("вчера"))
        assertNull(normalizeDateInput("16.07.27"))
    }
}
