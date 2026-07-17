package com.homevisit.location.calc

/**
 * Офлайн-вердикт «стоит ли ехать» на телефоне (Фаза 3.4/3.5) — без сети, по кешированной
 * матрице из /api/route/matrix. Композиция уже сверенных с сервером ядер:
 *   1. RouteOptimizer.candidateExtra — лишние км/мин ради заказа (маршрут дня С заказом vs БЕЗ);
 *   2. дневная выгодность до/после из локальных данных Room (доход − км×стоимость_км, минуты
 *      = маршрут + визиты×сервис) — так же, как серверный calculate_day_profitability по своим
 *      основным слагаемым;
 *   3. ProfitabilityCalculator.evaluate — маржа, вердикт go/edge/skip, балл 0–100.
 *
 * Паритет: маржинальные числа (marginal_profit/hourly/per_km, extra_car_cost) СОВПАДАЮТ с
 * сервером до копейки — они зависят только от дохода, extra_km и стоимости км, а те считаются
 * теми же ядрами. Именно эти числа сверяет лог расхождений Ф3.6. Дневной hourly здесь —
 * оценка по доступным на телефоне слагаемым (компенсации и прочие расходы дня живут только
 * в авторитетном серверном вердикте); поэтому онлайн вердикт берётся с сервера, а офлайн —
 * этот модуль как мгновенная замена. Решение зафиксировано в Журнале MASTER_PLAN.
 *
 * Индексация точек — как в RouteOptimizer/сервере: [старт(0), заказы(1..K), кандидат(K+1),
 * финиш(K+2)]. anchors — индексы onsite-якорей в полной матрице (кандидат якорем не бывает).
 */
object OfflineVerdict {

    data class Input(
        val distances: List<List<Double>>,
        val durations: List<List<Double>>,
        val existingCount: Int,
        val existingIncomes: List<Double>,   // доходы K уже принятых заказов дня
        val candidateIncome: Double,
        val anchors: List<Int> = emptyList(),
        // Коэффициенты — из снимка матрицы (/api/route/matrix), т.е. с сервера.
        val serviceMinutes: Double,
        val fuelPerKm: Double,
        val maintenancePerKm: Double,
        val minHourly: Double,
        val minMarginalHourly: Double,
        val outsideMinHourly: Double? = null,
        val outsideMinExtra: Double = 0.0,
        val isBaseDistrict: Boolean = true,
        val existingBaseCount: Int = 0,
        val blocksOutsideZone: Boolean = false,
        // Цена отклика КАНДИДАТА (платный лид Профи/Авито). Сервер вычитает её из
        // маржи (profitability_service:312); без этого поля офлайн-вердикт терял её
        // и знак маржи мог перевернуться (сервер −400 ₽, телефон +400 ₽).
        val candidateResponseCost: Double = 0.0,
        // Лиды отменённых заказов дня — вычитаются из «до» и «после», как на сервере.
        val cancelledLeadCosts: Double = 0.0,
        // false → день считается по порядку Ленты (перенос respect_feed_order Этапа 20).
        val autoOptimize: Boolean = true,
    )

    /** Мгновенный офлайн-вердикт заказа. Возвращает тот же Result, что ProfitabilityCalculator. */
    fun evaluate(input: Input): ProfitabilityCalculator.Result {
        val extra = RouteOptimizer.candidateExtra(
            input.distances, input.durations, input.existingCount, input.anchors,
            respectFeedOrder = !input.autoOptimize,
        )
        val costPerKm = input.fuelPerKm + input.maintenancePerKm
        val incomeSum = input.existingIncomes.sum()

        val beforeNet = incomeSum - extra.beforeKm * costPerKm - input.cancelledLeadCosts
        val afterNet = incomeSum + input.candidateIncome - input.candidateResponseCost -
            extra.afterKm * costPerKm - input.cancelledLeadCosts
        val beforeMinutes = extra.beforeMinutes + input.existingCount * input.serviceMinutes
        val afterMinutes = extra.afterMinutes + (input.existingCount + 1) * input.serviceMinutes
        val beforeHourly = safeHourly(beforeNet, beforeMinutes)
        val afterHourly = safeHourly(afterNet, afterMinutes)

        return ProfitabilityCalculator.evaluate(
            ProfitabilityCalculator.Input(
                income = input.candidateIncome,
                extraKm = extra.extraKm,
                extraDriveMinutes = extra.extraDriveMinutes,
                serviceMinutes = input.serviceMinutes,
                fuelPerKm = input.fuelPerKm,
                maintenancePerKm = input.maintenancePerKm,
                beforeHourly = beforeHourly,
                afterHourly = afterHourly,
                minHourly = input.minHourly,
                minMarginalHourly = input.minMarginalHourly,
                isBaseDistrict = input.isBaseDistrict,
                existingBaseCount = input.existingBaseCount,
                outsideMinHourly = input.outsideMinHourly,
                outsideMinExtra = input.outsideMinExtra,
                blocksOutsideZone = input.blocksOutsideZone,
                responseCost = input.candidateResponseCost,
            )
        )
    }

    /** ₽/час — как серверный _safe_hourly: net / (minutes/60). */
    private fun safeHourly(netProfit: Double, totalMinutes: Double): Double =
        if (totalMinutes <= 0) 0.0 else netProfit / totalMinutes * 60
}
