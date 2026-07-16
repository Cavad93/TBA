package com.homevisit.location.domain

import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** Период архива. По умолчанию — сегодня: чаще всего ищут то, что закрыл только что. */
enum class ArchiveRange(val title: String, val days: Long) {
    Today("Сегодня", 0),
    Week("Неделя", 6),
    Month("Месяц", 29),
}

/** Способ сортировки списка архива. */
enum class ArchiveSort(val title: String) {
    ByClosed("По закрытию"),
    ByAdded("По добавлению"),
    ByIncome("По доходу"),
    ByAddress("По адресу"),
}

/**
 * Заказ в архиве: адрес, когда добавлен, когда закрыт и чем кончилось.
 *
 * Тексты времени готовит доменный слой, а не экран: формат даты — это правило
 * продукта, и в двух местах оно разъедется.
 */
data class ArchivedVisit(
    val id: String,
    val address: String,
    val clinic: String,
    val income: Double,
    val done: Boolean,
    val addedAtMillis: Long,
    val closedAtMillis: Long,
    val addedAtText: String,
    val closedAtText: String,
)

data class ArchiveUiState(
    val range: ArchiveRange = ArchiveRange.Today,
    val sort: ArchiveSort = ArchiveSort.ByClosed,
    val visits: List<ArchivedVisit> = emptyList(),
)

/**
 * Ответ сервера на смену старта/финиша дня.
 *
 * [address] — НОРМАЛИЗОВАННЫЙ геокодером адрес: локально надо хранить именно его, а не
 * то, что человек набрал. Координаты и там и там одни, но строки расходились, и один и
 * тот же адрес выглядел на телефоне и на сервере по-разному.
 */
data class AnchorUpdate(
    val reason: String?,
    val address: String?,
)

/**
 * Подробности одного заказа. Открывается по клику и из архива, и из активных вызовов —
 * раньше посмотреть заказ целиком было негде: Лента показывает адрес и деньги,
 * «История» — только агрегаты.
 */
data class OrderDetails(
    val id: String,
    val address: String,
    val clinic: String,
    val income: Double,
    val statusText: String,
    val addedAtText: String,
    val closedAtText: String,
    val driveMinutes: Double? = null,
    val onSiteMinutes: Double? = null,
    val plannedStartAt: String? = null,
)

private val TIME = DateTimeFormatter.ofPattern("HH:mm")
private val DATE_TIME = DateTimeFormatter.ofPattern("dd.MM HH:mm")

/**
 * Метка времени для строки архива: сегодняшнее — только часы, иначе с датой.
 *
 * За сегодня дата в каждой строке — шум: и так понятно, что это сегодня. За неделю
 * без даты, наоборот, не отличить вторник от пятницы.
 */
fun archiveTimeText(millis: Long, today: LocalDate = LocalDate.now(), zone: ZoneId = ZoneId.systemDefault()): String {
    if (millis <= 0) return "—"
    val moment = LocalDateTime.ofInstant(Instant.ofEpochMilli(millis), zone)
    return if (moment.toLocalDate() == today) moment.format(TIME) else moment.format(DATE_TIME)
}

/** Границы периода в миллисекундах: включительно с начала первого дня по конец сегодня. */
fun archiveBounds(
    range: ArchiveRange,
    today: LocalDate = LocalDate.now(),
    zone: ZoneId = ZoneId.systemDefault(),
): Pair<Long, Long> {
    val from = today.minusDays(range.days).atStartOfDay(zone).toInstant().toEpochMilli()
    val to = today.plusDays(1).atStartOfDay(zone).toInstant().toEpochMilli() - 1
    return from to to
}

/** Сортировка списка. Держим в домене — экран не должен знать правил порядка. */
fun sortArchive(visits: List<ArchivedVisit>, sort: ArchiveSort): List<ArchivedVisit> = when (sort) {
    ArchiveSort.ByClosed -> visits.sortedByDescending { it.closedAtMillis }
    ArchiveSort.ByAdded -> visits.sortedByDescending { it.addedAtMillis }
    ArchiveSort.ByIncome -> visits.sortedByDescending { it.income }
    ArchiveSort.ByAddress -> visits.sortedBy { it.address.lowercase() }
}
