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
    drivingHours: String,
    workHours: String,
    serviceMinutes: String,
    coffeeUnits: String = "",
    drinksUnits: String = "",
    mealUnits: String = "",
    selfRating: Int = 0,
): EndDayDetails {
    val startOdometer = preview?.startOdometer ?: 0.0
    val suggestedKm = preview?.suggestedKm ?: 0.0

    val endOdometer = parseNumber(odometer) ?: (startOdometer + suggestedKm)
    val odometerKm = (endOdometer - startOdometer).coerceAtLeast(0.0)
    val actualKm = minOf(suggestedKm, odometerKm)

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
        userFatigueScore = null,
        foodMealExpenses = parseNumber(meal) ?: 0.0,
        coffeeExpenses = parseNumber(coffee) ?: 0.0,
        drinksExpenses = parseNumber(drinks) ?: 0.0,
        parkingExpenses = parseNumber(parking) ?: 0.0,
        // Штуки, а не рубли: 300 ₽ — это одна чашка в аэропорту или три в ларьке,
        // а на восстановление влияет количество кофеина, а не сумма чека.
        coffeeUnits = parseNumber(coffeeUnits) ?: 0.0,
        drinksUnits = parseNumber(drinksUnits) ?: 0.0,
        mealUnits = parseNumber(mealUnits) ?: 0.0,
        selfRating = selfRating.toDouble(),
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
