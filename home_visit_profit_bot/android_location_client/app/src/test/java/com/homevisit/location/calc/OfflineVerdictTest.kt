package com.homevisit.location.calc

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Тесты композиции офлайн-вердикта (Фаза 3.4/3.5). OfflineVerdict склеивает три уже
 * сверенных с сервером ядра (RouteOptimizer.candidateExtra + дневная арифметика +
 * ProfitabilityCalculator.evaluate). Здесь ловим регрессии РАЗВОДКИ полей — самое
 * опасное при склейке: перепутанные fuel/maintenance, before/after, забытый доход
 * кандидата в afterNet. Маржинальные числа (их сверяет лог 3.6) обязаны совпадать
 * с прямым вызовом ProfitabilityCalculator до бита.
 */
class OfflineVerdictTest {

    // Индексы полной матрицы: [старт0, заказ1, кандидат2, финиш3], existingCount=1.
    private val distances = listOf(
        listOf(0.0, 10.0, 10.0, 20.0),
        listOf(10.0, 0.0, 5.0, 10.0),
        listOf(10.0, 5.0, 0.0, 10.0),
        listOf(20.0, 10.0, 10.0, 0.0),
    )
    private val durations = distances.map { row -> row.map { it * 2.0 } }

    private fun baseInput(candidateIncome: Double) = OfflineVerdict.Input(
        distances = distances,
        durations = durations,
        existingCount = 1,
        existingIncomes = listOf(1000.0),
        candidateIncome = candidateIncome,
        anchors = emptyList(),
        serviceMinutes = 30.0,
        fuelPerKm = 6.0,
        maintenancePerKm = 4.0,
        minHourly = 300.0,
        minMarginalHourly = 200.0,
    )

    /** OfflineVerdict.evaluate == прямая композиция ядер: гарантия, что разводка не переставлена. */
    @Test
    fun matchesDirectComposition() {
        val input = baseInput(candidateIncome = 800.0)
        val extra = RouteOptimizer.candidateExtra(
            input.distances, input.durations, input.existingCount, input.anchors,
        )
        val costPerKm = input.fuelPerKm + input.maintenancePerKm
        val incomeSum = input.existingIncomes.sum()
        val beforeNet = incomeSum - extra.beforeKm * costPerKm
        val afterNet = incomeSum + input.candidateIncome - extra.afterKm * costPerKm
        val beforeMinutes = extra.beforeMinutes + input.existingCount * input.serviceMinutes
        val afterMinutes = extra.afterMinutes + (input.existingCount + 1) * input.serviceMinutes
        fun hourly(net: Double, min: Double) = if (min <= 0) 0.0 else net / min * 60

        val expected = ProfitabilityCalculator.evaluate(
            ProfitabilityCalculator.Input(
                income = input.candidateIncome,
                extraKm = extra.extraKm,
                extraDriveMinutes = extra.extraDriveMinutes,
                serviceMinutes = input.serviceMinutes,
                fuelPerKm = input.fuelPerKm,
                maintenancePerKm = input.maintenancePerKm,
                beforeHourly = hourly(beforeNet, beforeMinutes),
                afterHourly = hourly(afterNet, afterMinutes),
                minHourly = input.minHourly,
                minMarginalHourly = input.minMarginalHourly,
                isBaseDistrict = true,
                existingBaseCount = 0,
            ),
        )
        assertEquals(expected, OfflineVerdict.evaluate(input))
    }

    /** Маржинальная прибыль = доход − оплачиваемые км × стоимость км (сверяемое число Ф3.6). */
    @Test
    fun marginalProfitUsesCombinedKmCost() {
        val input = baseInput(candidateIncome = 800.0)
        val extra = RouteOptimizer.candidateExtra(
            input.distances, input.durations, input.existingCount, input.anchors,
        )
        val paidKm = maxOf(0.0, if (kotlin.math.abs(extra.extraKm) < 0.05) 0.0 else extra.extraKm)
        val expectedProfit = 800.0 - paidKm * (6.0 + 4.0)
        assertEquals(expectedProfit, OfflineVerdict.evaluate(input).marginalProfit, 0.01)
    }

    /** Доход кандидата обязан влиять на afterHourly: жирный чек → go, копеечный → не go. */
    @Test
    fun candidateIncomeDrivesVerdict() {
        val rich = OfflineVerdict.evaluate(baseInput(candidateIncome = 5000.0))
        val poor = OfflineVerdict.evaluate(baseInput(candidateIncome = 1.0))
        assertEquals("go", rich.verdict)
        assertTrue("копеечный заказ не должен быть go", poor.verdict != "go")
        assertTrue("балл богатого выше", rich.score > poor.score)
    }
}
