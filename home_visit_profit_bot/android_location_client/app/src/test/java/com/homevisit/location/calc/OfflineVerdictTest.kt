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

    /** Доход кандидата обязан течь в маржу и afterHourly: больше чек → больше маржа и балл. */
    @Test
    fun candidateIncomeDrivesVerdict() {
        val rich = OfflineVerdict.evaluate(baseInput(candidateIncome = 5000.0))
        val poor = OfflineVerdict.evaluate(baseInput(candidateIncome = 1.0))
        assertEquals("go", rich.verdict)
        assertTrue("маржа реагирует на доход", rich.marginalProfit > poor.marginalProfit)
        assertTrue("балл богатого не ниже", rich.score >= poor.score)
    }

    /**
     * Регресс Этапа 22: цена отклика КАНДИДАТА обязана вычитаться из маржи и офлайн.
     * До правки поле терялось по всей цепочке (VM → mapper → estimator → verdict), и
     * знак маржи переворачивался: сервер −400 ₽, телефон +400 ₽ на одном и том же лиде.
     */
    @Test
    fun candidateResponseCostCutsMarginOffline() {
        val free = OfflineVerdict.evaluate(baseInput(candidateIncome = 800.0))
        val paid = OfflineVerdict.evaluate(
            baseInput(candidateIncome = 800.0).copy(candidateResponseCost = 800.0),
        )
        assertEquals(
            "лид вычитается из маржи рубль в рубль",
            free.marginalProfit - 800.0,
            paid.marginalProfit,
            0.011,
        )
        assertTrue("дорогой лид загоняет маржу в минус", paid.marginalProfit < 0)
    }

    /** Лиды отменённых заказов дня режут «до»/«после»: потери смены не прячутся из ₽/час. */
    @Test
    fun cancelledLeadCostsLowerDayHourly() {
        val clean = OfflineVerdict.evaluate(baseInput(candidateIncome = 800.0))
        val burned = OfflineVerdict.evaluate(
            baseInput(candidateIncome = 800.0).copy(cancelledLeadCosts = 100000.0),
        )
        assertEquals("go", clean.verdict)
        assertTrue(
            "сгоревшие лиды обязаны менять решение, а не только маржу",
            burned.decision != clean.decision,
        )
    }

    /** autoOptimize=false прокидывается до RouteOptimizer: порядок Ленты, а не оптимум. */
    @Test
    fun feedOrderFlagReachesRouteOptimizer() {
        // Матрица, где порядок Ленты заметно длиннее оптимального: у «до»/«после»
        // меняются км, значит extraCarCost при выключенной оптимизации другой.
        val dist = listOf(
            listOf(0.0, 10.0, 1.0, 1.0, 30.0),
            listOf(10.0, 0.0, 1.0, 1.0, 1.0),
            listOf(1.0, 1.0, 0.0, 5.0, 10.0),
            listOf(1.0, 1.0, 5.0, 0.0, 10.0),
            listOf(30.0, 1.0, 10.0, 10.0, 0.0),
        )
        val dur = dist.map { row -> row.map { it * 2.0 } }
        val base = baseInput(candidateIncome = 800.0).copy(
            distances = dist,
            durations = dur,
            existingCount = 2,
            existingIncomes = listOf(1000.0, 1000.0),
        )
        val optimized = OfflineVerdict.evaluate(base)
        val feedOrder = OfflineVerdict.evaluate(base.copy(autoOptimize = false))
        assertTrue(
            "порядок Ленты дороже оптимального — числа обязаны отличаться",
            feedOrder.extraCarCost != optimized.extraCarCost ||
                feedOrder.marginalProfit != optimized.marginalProfit,
        )
    }
}
