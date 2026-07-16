package com.homevisit.location.domain

import java.time.LocalDate
import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Архив закрытых заказов: границы периода, метки времени и сортировки (п.12). */
class ArchiveTest {

    private val zone: ZoneId = ZoneId.of("Europe/Moscow")
    private val today: LocalDate = LocalDate.of(2026, 7, 16)

    private fun at(hour: Int, minute: Int, day: LocalDate = today): Long =
        day.atTime(hour, minute).atZone(zone).toInstant().toEpochMilli()

    private fun visit(
        id: String,
        address: String = "Адрес",
        income: Double = 1000.0,
        done: Boolean = true,
        added: Long = at(9, 0),
        closed: Long = at(10, 0),
    ) = ArchivedVisit(
        id = id,
        address = address,
        clinic = "",
        income = income,
        done = done,
        addedAtMillis = added,
        closedAtMillis = closed,
        addedAtText = archiveTimeText(added, today, zone),
        closedAtText = archiveTimeText(closed, today, zone),
    )

    @Test
    fun `today range covers the whole day and nothing before it`() {
        val (from, to) = archiveBounds(ArchiveRange.Today, today, zone)

        assertEquals(today.atStartOfDay(zone).toInstant().toEpochMilli(), from)
        assertTrue("конец сегодня входит в период", at(23, 59) <= to)
        assertTrue("вчерашнее в «сегодня» не попадает", at(23, 59, today.minusDays(1)) < from)
    }

    @Test
    fun `week range reaches back six days`() {
        val (from, _) = archiveBounds(ArchiveRange.Week, today, zone)

        assertEquals(today.minusDays(6).atStartOfDay(zone).toInstant().toEpochMilli(), from)
    }

    @Test
    fun `today shows only time and older entries show a date`() {
        // За сегодня дата в каждой строке — шум; за неделю без даты не отличить дни.
        assertEquals("10:00", archiveTimeText(at(10, 0), today, zone))
        assertEquals("14.07 10:00", archiveTimeText(at(10, 0, today.minusDays(2)), today, zone))
    }

    @Test
    fun `missing timestamp is shown as a dash and never as 1970`() {
        assertEquals("—", archiveTimeText(0, today, zone))
    }

    @Test
    fun `sort by closing time puts the latest first`() {
        val early = visit("a", closed = at(10, 0))
        val late = visit("b", closed = at(18, 0))

        val sorted = sortArchive(listOf(early, late), ArchiveSort.ByClosed)

        assertEquals(listOf("b", "a"), sorted.map { it.id })
    }

    @Test
    fun `sort by income puts the richest first`() {
        val cheap = visit("a", income = 500.0)
        val rich = visit("b", income = 3000.0)

        assertEquals(listOf("b", "a"), sortArchive(listOf(cheap, rich), ArchiveSort.ByIncome).map { it.id })
    }

    @Test
    fun `sort by address ignores case`() {
        val b = visit("b", address = "аврора")
        val a = visit("a", address = "Байкал")

        assertEquals(listOf("b", "a"), sortArchive(listOf(a, b), ArchiveSort.ByAddress).map { it.id })
    }

    @Test
    fun `sort by added time is independent of closing time`() {
        val addedFirst = visit("a", added = at(8, 0), closed = at(20, 0))
        val addedLater = visit("b", added = at(12, 0), closed = at(13, 0))

        assertEquals(listOf("b", "a"), sortArchive(listOf(addedFirst, addedLater), ArchiveSort.ByAdded).map { it.id })
        assertEquals(listOf("a", "b"), sortArchive(listOf(addedFirst, addedLater), ArchiveSort.ByClosed).map { it.id })
    }
}
