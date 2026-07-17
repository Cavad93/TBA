package com.homevisit.location

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AddressPartsTest {

    @Test
    fun `город с типом распознаётся`() {
        assertTrue(looksLikeCity("г Санкт-Петербург"))
        assertTrue(looksLikeCity("Казань"))
        assertTrue(looksLikeCity("Нижний Новгород"))
    }

    @Test
    fun `улица и дом городом не считаются`() {
        assertFalse(looksLikeCity("ул Ленина"))
        assertFalse(looksLikeCity("Ленина 5"))   // цифра дома
        assertFalse(looksLikeCity("пр-кт Испытателей"))
        assertFalse(looksLikeCity(""))
    }

    @Test
    fun `полный адрес DaData разбивается на город и улицу-дом`() {
        val (city, address) = splitCityAddress("г Санкт-Петербург, ул Лидии Зверевой, д 3 к 1 стр 1")
        assertEquals("г Санкт-Петербург", city)
        // Корпус и строение сохранены — ровно то, что было не видно в обрезанной подсказке.
        assertEquals("ул Лидии Зверевой, д 3 к 1 стр 1", address)
    }

    @Test
    fun `адрес без города целиком уходит в поле адреса`() {
        val (city, address) = splitCityAddress("ул Ленина, д 5")
        assertEquals("", city)
        assertEquals("ул Ленина, д 5", address)
    }

    @Test
    fun `одна часть без запятой считается адресом`() {
        val (city, address) = splitCityAddress("Дом")
        assertEquals("", city)
        assertEquals("Дом", address)
    }

    @Test
    fun `склейка возвращает полную строку для резолва`() {
        assertEquals(
            "Санкт-Петербург, ул Лидии Зверевой, д 3 к 1",
            joinCityAddress("Санкт-Петербург", "ул Лидии Зверевой, д 3 к 1"),
        )
    }

    @Test
    fun `склейка не дублирует город, если он уже в адресе`() {
        assertEquals(
            "г Казань, ул Баумана, д 1",
            joinCityAddress("Казань", "г Казань, ул Баумана, д 1"),
        )
    }

    @Test
    fun `склейка терпит пустые части`() {
        assertEquals("ул Ленина 5", joinCityAddress("", "ул Ленина 5"))
        assertEquals("Казань", joinCityAddress("Казань", ""))
    }

    @Test
    fun `разбор и склейка — обратимы для адреса с городом`() {
        val full = "г Санкт-Петербург, ул Лидии Зверевой, д 3 к 1"
        val (city, address) = splitCityAddress(full)
        assertEquals(full, joinCityAddress(city, address))
    }
}
