package com.homevisit.location

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Зоны обслуживания: разбор при РЕДАКТИРОВАНИИ и при СОХРАНЕНИИ — разный (пункт 7).
 *
 * Жалоба: «жму добавить зону — ничего не открывается и не добавляется». Кнопка честно
 * дописывала пустую зону в JSON, но экран заново разбирал этот JSON на каждой
 * перерисовке, а разбор выбрасывал пустые зоны. Свежая карточка исчезала на следующем
 * кадре — добавление выглядело мёртвым.
 */
class BaseZonesTest {

    @Test
    fun `blank zone survives editing so the new card is visible`() {
        val json = serializeBaseZones(listOf(BaseZone()))

        val editing = parseBaseZones(json, dropBlank = false)

        assertEquals(1, editing.size)
    }

    @Test
    fun `blank zone is dropped on save`() {
        val json = serializeBaseZones(listOf(BaseZone()))

        assertTrue(parseBaseZones(json).isEmpty())
    }

    @Test
    fun `filled zones survive both ways`() {
        val zone = BaseZone(region = "Ленинградская область", city = "Санкт-Петербург", districts = listOf("Приморский"))
        val json = serializeBaseZones(listOf(zone))

        assertEquals(listOf(zone), parseBaseZones(json))
        assertEquals(listOf(zone), parseBaseZones(json, dropBlank = false))
    }

    @Test
    fun `adding a zone to an existing list keeps the old ones`() {
        val existing = BaseZone(city = "Санкт-Петербург")
        val json = serializeBaseZones(parseBaseZones(serializeBaseZones(listOf(existing)), dropBlank = false) + BaseZone())

        val zones = parseBaseZones(json, dropBlank = false)

        assertEquals(2, zones.size)
        assertEquals("Санкт-Петербург", zones.first().city)
    }

    @Test
    fun `broken json does not crash the screen`() {
        assertTrue(parseBaseZones("не json", dropBlank = false).isEmpty())
        assertTrue(parseBaseZones("").isEmpty())
    }
}
