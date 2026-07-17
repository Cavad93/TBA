package com.homevisit.location

import com.homevisit.location.domain.EndDayDetails
import com.homevisit.location.domain.EndDayPreview

/**
 * Расчётная часть мастера завершения смены: подстановка значений в поля и сборка
 * итогового `EndDayDetails`. Вынесено из Compose-кода, чтобы логику было видно
 * отдельно от вёрстки.
 */

/** Предзаполнение денежного поля: ноль показываем пустым, чтобы не мешал вводу. */
internal fun EndDayPreview?.moneyText(select: (EndDayPreview) -> Double): String {
    val value = this?.let(select) ?: 0.0
    return if (value > 0) oneDecimal(value).removeSuffix(",0") else ""
}

internal fun Double?.numberText(): String {
    val value = this ?: return ""
    return if (value > 0) oneDecimal(value).removeSuffix(",0") else ""
}

internal fun Double?.hoursText(): String {
    val minutes = this ?: return ""
    return if (minutes > 0) hoursInput(minutes) else ""
}

internal fun EndDayPreview.kmSourceTitle(): String =
    if (kmSource == "gps") "по GPS" else "по маршруту заказов"

internal fun EndDayPreview.minutesSourceTitle(): String =
    if (minutesSource == "gps") "по GPS" else "по маршруту заказов"

internal fun formatKm(value: Double): String = oneDecimal(value).removeSuffix(",0") + " км"

/**
 * Поля мастера, чей ввод НЕ распознан: не пусто, но не число (или меньше нуля).
 *
 * Молча подставлять 0 или расчётное значение вместо нераспознанной правки нельзя:
 * поля предзаполнены реальными суммами дня, и опечатка при правке обнуляла расход
 * на сервере — тот же механизм «сервер подставляет присланное вместо накопленного»,
 * которым уже теряли vehicle_expenses. Пустое поле — осознанное «не было», это ок.
 */
internal fun invalidEndShiftInputs(
    meal: String,
    coffee: String,
    drinks: String,
    toll: String,
    parking: String,
    other: String,
    fuelAmount: String,
    fuelLiters: String,
    odometer: String,
    drivingHours: String,
    workHours: String,
    serviceMinutes: String,
): List<String> = listOf(
    "Еда" to meal,
    "Кофе" to coffee,
    "Вода/напитки" to drinks,
    "Платная дорога" to toll,
    "Парковка" to parking,
    "Прочее" to other,
    "Заправка" to fuelAmount,
    "Литры" to fuelLiters,
    "Одометр" to odometer,
    "За рулём" to drivingHours,
    "Всего работали" to workHours,
    "Минут на адрес" to serviceMinutes,
).filter { (_, text) -> text.isNotBlank() && parseNumber(text) == null }
    .map { (label, _) -> label }

/** Цена литра по введённой заправке — по ней ловим опечатку в сумме или объёме. */
internal fun fuelPricePerLiter(amount: String, liters: String): Double? {
    val sum = parseNumber(amount) ?: return null
    val volume = parseNumber(liters) ?: return null
    if (sum <= 0 || volume <= 0) return null
    return sum / volume
}

/**
 * Собирает итог смены из ответов мастера, подставляя расчётные значения там, где
 * пользователь ничего не ввёл.
 *
 * Два значения намеренно подрезаются: сервер отказывается закрывать день, если
 * пробег по одометру меньше рабочего или если время за рулём больше общего
 * рабочего времени. Отправить такие данные — значит уронить синхронизацию и
 * оставить смену незакрытой, поэтому приводим их к согласованным.
 */
internal fun buildEndDayDetails(
    preview: EndDayPreview?,
    meal: String,
    coffee: String,
    drinks: String,
    toll: String,
    parking: String,
    other: String,
    fuelAmount: String,
    fuelLiters: String,
    odometer: String,
    /** Рабочий пробег, выбранный человеком при расхождении GPS и одометра. 0 — не спрашивали. */
    chosenKm: Double = 0.0,
    drivingHours: String,
    workHours: String,
    serviceMinutes: String,
    workloadRating: Int = 0,
): EndDayDetails {
    val startOdometer = preview?.startOdometer ?: 0.0
    val suggestedKm = preview?.suggestedKm ?: 0.0

    val endOdometer = parseNumber(odometer) ?: (startOdometer + suggestedKm)
    val odometerKm = (endOdometer - startOdometer).coerceAtLeast(0.0)
    // Если человека спрашивали, какой пробег считать рабочим, — его ответ и есть ответ.
    // Приложение не может отличить личную поездку от провала GPS в тоннеле: это знает
    // только он. Разница уходит в личный пробег, как и была задумана.
    val actualKm = if (chosenKm > 0) {
        minOf(chosenKm, odometerKm)
    } else {
        minOf(suggestedKm, odometerKm)
    }

    val totalWorkMinutes = parseNumber(workHours)?.times(60)
        ?: preview?.totalWorkMinutes
        ?: 0.0
    val drivingMinutes = (parseNumber(drivingHours)?.times(60) ?: preview?.drivingMinutes ?: 0.0)
        .coerceAtMost(totalWorkMinutes)

    val avgService = parseNumber(serviceMinutes) ?: preview?.avgServiceMinutes ?: 0.0
    val completed = preview?.completedVisitsCount ?: 0

    val fuelExpenses = parseNumber(fuelAmount) ?: 0.0
    val litres = parseNumber(fuelLiters) ?: 0.0

    return EndDayDetails(
        actualKm = actualKm,
        totalWorkMinutes = totalWorkMinutes,
        actualRouteMinutes = drivingMinutes,
        completedVisitsCount = completed,
        startOdometer = startOdometer,
        endOdometer = endOdometer,
        fuelExpenses = fuelExpenses,
        fuelLiters = litres,
        // Расход л/100 км считаем только по реальной заправке; иначе сервер возьмёт
        // значение из настроек или из истории.
        fuelConsumptionLitersPer100Km = 0.0,
        fuelCompensation = 0.0,
        parkingCompensation = 0.0,
        tollExpenses = parseNumber(toll) ?: 0.0,
        tollCompensation = 0.0,
        otherExpenses = parseNumber(other) ?: 0.0,
        userWorkloadIndex = null,
        foodMealExpenses = parseNumber(meal) ?: 0.0,
        coffeeExpenses = parseNumber(coffee) ?: 0.0,
        drinksExpenses = parseNumber(drinks) ?: 0.0,
        parkingExpenses = parseNumber(parking) ?: 0.0,
        // Расходы машины и аренды человек в мастере не вводит — они уже записаны за
        // смену. Но вернуть их серверу обязаны: он подставляет ПРИСЛАННОЕ вместо
        // накопленного, и дефолтный 0.0 затирал реальные суммы. В живом дне расходы
        // были, а в закрытом (daily_stats) исчезали — тихая потеря денег из истории.
        vehicleExpenses = preview?.vehicleExpenses ?: 0.0,
        vehicleRent = preview?.vehicleRent ?: 0.0,
        workloadRating = workloadRating.toDouble(),
    ).let { details ->
        // Средняя длительность визита в контракт дня не входит: сервер выводит её
        // из общего времени. Но если пользователь её поправил, а заказы были —
        // уважаем ввод и пересчитываем общее время.
        if (avgService > 0 && completed > 0) {
            val service = avgService * completed
            val total = maxOf(details.totalWorkMinutes, details.actualRouteMinutes + service)
            details.copy(totalWorkMinutes = total)
        } else {
            details
        }
    }
}
