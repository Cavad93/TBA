package com.homevisit.location.calc

import java.math.BigDecimal
import java.math.RoundingMode

/**
 * Чистое ядро расчёта выгодности заказа на телефоне (Фаза 3.3).
 *
 * Точный перенос серверного `candidate_pure.evaluate` (+ make_decision, profitability_score,
 * decision_to_verdict). Формула — здесь, коэффициенты — с сервера (снимок из /api/route/matrix
 * и /api/settings). Паритет до копейки проверяется золотыми векторами
 * (candidate_vectors.json) в обоих CI: разойдётся телефон с сервером — падают оба.
 *
 * Округление КРИТИЧНО для паритета: Python round() — «к чётному» (half-even). Поэтому
 * здесь BigDecimal HALF_EVEN для 2 знаков и Math.rint (тоже half-even) для балла, а не
 * String.format/Math.round (те округляют «от нуля» и разошлись бы на граничных .xx5).
 */
object ProfitabilityCalculator {

    data class Input(
        val income: Double,
        val extraKm: Double,
        val extraDriveMinutes: Double,
        val serviceMinutes: Double,
        val fuelPerKm: Double,
        val maintenancePerKm: Double,
        val beforeHourly: Double,
        val afterHourly: Double,
        val minHourly: Double,
        val minMarginalHourly: Double,
        val isBaseDistrict: Boolean,
        val existingBaseCount: Int,
        val outsideMinHourly: Double? = null,
        val outsideMinExtra: Double = 0.0,
        val blocksOutsideZone: Boolean = false,
        // Парковка у точки заказа (Фаза 9.4): нижняя граница вычитается из маржи,
        // как в серверном candidate_pure/calculate_candidate_impact. 0 — нет платной зоны.
        val parkingCost: Double = 0.0,
        // Цена отклика (Фаза 11.2): платный лид (Профи/Авито) — прямой расход заказа,
        // вычитается из маржи так же, как парковка. 0 — сарафан/бесплатный источник.
        val responseCost: Double = 0.0,
    )

    data class Result(
        val marginalProfit: Double,
        val marginalHourly: Double,
        val marginalPerKm: Double,
        val extraCarCost: Double,
        val extraTotalMinutes: Double,
        val decision: String,
        val verdict: String,
        val score: Int,
    )

    fun evaluate(input: Input): Result {
        val extraKm = zeroTiny(input.extraKm, 0.05)
        val extraDrive = zeroTiny(input.extraDriveMinutes, 0.5)
        val costPerKm = input.fuelPerKm + input.maintenancePerKm
        val outsideMinHourly = input.outsideMinHourly ?: input.minHourly

        val paidExtraKm = maxOf(0.0, extraKm)
        val paidExtraDrive = maxOf(0.0, extraDrive)
        val extraTotalMinutes = paidExtraDrive + input.serviceMinutes
        val extraCarCost = paidExtraKm * costPerKm
        val marginalProfit = input.income - extraCarCost - input.parkingCost - input.responseCost
        val marginalHourly = safeHourly(marginalProfit, extraTotalMinutes)
        val marginalPerKm = if (paidExtraKm > 0) marginalProfit / paidExtraKm else 0.0

        val decision = makeDecision(
            beforeHourly = input.beforeHourly,
            afterHourly = input.afterHourly,
            isBaseDistrict = input.isBaseDistrict,
            existingBaseCount = input.existingBaseCount,
            minHourly = input.minHourly,
            outsideMinHourly = outsideMinHourly,
            outsideMinExtra = input.outsideMinExtra,
            blocksOutsideZone = input.blocksOutsideZone,
        )
        val verdict = decisionToVerdict(decision)
        val score = profitabilityScore(decision, marginalHourly, input.minMarginalHourly)

        return Result(
            marginalProfit = round2(marginalProfit),
            marginalHourly = round2(marginalHourly),
            marginalPerKm = round2(marginalPerKm),
            extraCarCost = round2(extraCarCost),
            extraTotalMinutes = round2(extraTotalMinutes),
            decision = decision,
            verdict = verdict,
            score = score,
        )
    }

    private fun safeHourly(netProfit: Double, totalMinutes: Double): Double =
        if (totalMinutes <= 0) 0.0 else netProfit / totalMinutes * 60

    private fun zeroTiny(value: Double, epsilon: Double): Double =
        if (kotlin.math.abs(value) < epsilon) 0.0 else value

    /** round(x, 2) как в Python — half-even ПО ДВОИЧНОМУ значению.

     * Именно BigDecimal(value), не BigDecimal.valueOf(value): valueOf идёт через
     * Double.toString (кратчайшую десятичную запись), и на значениях вида 750.175
     * тай ловится по десятичной записи — Python же округляет точное двоичное
     * значение. На достижимых .xx5 это давало ±0.01 (750.17 у сервера, 750.18 тут).
     */
    private fun round2(value: Double): Double =
        BigDecimal(value).setScale(2, RoundingMode.HALF_EVEN).toDouble()

    /**
     * Точный перенос make_decision. Строки решений совпадают с сервером посимвольно —
     * от них зависит и вердикт (decisionToVerdict ищет подстроки), и показ на экране.
     */
    private fun makeDecision(
        beforeHourly: Double,
        afterHourly: Double,
        isBaseDistrict: Boolean,
        existingBaseCount: Int,
        minHourly: Double,
        outsideMinHourly: Double,
        outsideMinExtra: Double,
        blocksOutsideZone: Boolean,
    ): String {
        if (!isBaseDistrict) {
            if (blocksOutsideZone) return "ТОЛЬКО СО СПЕЦТАРИФОМ"
            val target = maxOf(beforeHourly, outsideMinHourly)
            if (afterHourly >= target && outsideMinExtra <= 0) return "МОЖНО БРАТЬ"
            if (afterHourly >= target) return "ТОЛЬКО С НАДБАВКОЙ"
            return "ТОЛЬКО СО СПЕЦТАРИФОМ"
        }
        if (afterHourly > beforeHourly) return "ОДНОЗНАЧНО ДА"
        if (afterHourly >= minHourly) return "МОЖНО БРАТЬ"
        return "НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ"
    }

    /** Точный перенос decision_to_verdict: «невыгодно» проверяем первым (содержит «спецтариф»). */
    private fun decisionToVerdict(decision: String): String {
        val text = decision.uppercase()
        if (text.contains("НЕВЫГОДНО")) return "skip"
        if (text.contains("СПЕЦТАРИФ") || text.contains("НАДБАВК")) return "edge"
        if (text.contains("ДА") || text.contains("МОЖНО БРАТЬ")) return "go"
        return "edge"
    }

    /** Точный перенос profitability_score: полоса по вердикту, позиция по tanh, half-even округление. */
    private fun profitabilityScore(decision: String, marginalHourly: Double, targetMarginalHourly: Double): Int {
        val verdict = decisionToVerdict(decision)
        val position = if (targetMarginalHourly > 0) {
            0.5 + 0.5 * Math.tanh((marginalHourly - targetMarginalHourly) / (targetMarginalHourly * 0.6))
        } else {
            if (marginalHourly >= 0) 1.0 else 0.0
        }
        val (low, high) = when (verdict) {
            "skip" -> 5 to 33
            "go" -> 67 to 96
            else -> 34 to 66
        }
        // int(round(...)) с half-even — Math.rint округляет к чётному, как Python round().
        return Math.rint(low + position * (high - low)).toInt()
    }
}
