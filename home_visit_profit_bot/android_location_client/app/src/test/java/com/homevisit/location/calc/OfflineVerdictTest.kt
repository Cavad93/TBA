package com.homevisit.location.calc

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
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

    /**
     * Лиды отменённых заказов дня режут «до»/«после» — потери смены двигают решение.
     *
     * Арифметика (матрица baseInput): before 20 км/70 мин, after 25 км/110 мин,
     * cost 10 ₽/км.
     *
     * ЧТО ИЗМЕНИЛОСЬ В ЭТАПЕ 66 И ПОЧЕМУ ЭТО ПРАВИЛЬНО. Раньше сгоревший лид на 400 ₽
     * ронял дневной ₽/час ниже порога, и СЛЕДУЮЩИЙ заказ становился «невыгодным».
     * Но сгоревший лид — утопленные деньги: они уже потрачены и не вернутся ни если
     * взять этот заказ, ни если отказаться. Решение о следующем заказе они менять не
     * должны — в решение входят только те расходы, которых можно избежать, отказавшись
     * (топливо, износ, платный лид САМОГО этого заказа).
     *
     * Старое поведение было вторым изданием той же ошибки, на которую жаловался
     * владелец: неудача в начале дня заставляла приложение отказываться от заказов,
     * которые приносят деньги, — и день закапывался глубже.
     *
     * Деньги при этом не спрятаны: сгоревший лид по-прежнему вычитается из чистого дня
     * и виден в дневных ₽/час. Он влияет на ОТТЕНОК (однозначно да / можно брать), но
     * больше не блокирует.
     */
    @Test
    fun cancelledLeadCostsDoNotBlockTheNextOrder() {
        val clean = OfflineVerdict.evaluate(baseInput(candidateIncome = 100.0))
        val burned = OfflineVerdict.evaluate(
            baseInput(candidateIncome = 100.0).copy(cancelledLeadCosts = 400.0),
        )
        // Заказ сам по себе не изменился — значит и вердикт по нему не должен.
        assertEquals(clean.verdict, burned.verdict)
        assertEquals(clean.marginalProfit, burned.marginalProfit, 1e-9)
        assertEquals(clean.marginalHourly, burned.marginalHourly, 1e-9)
    }

    /**
     * autoOptimize=false прокидывается до RouteOptimizer: порядок Ленты, а не оптимум.
     *
     * Матрица построена так, что порядок Ленты — катастрофа (плечо 0→1 = 200 км),
     * а оптимум дешёвый (0→2→3→1→4 = 8 км). extra_km у кандидата одинаков (5 км) —
     * различие живёт в «до»/«после»: оптимум даёт after 1539 ₽/ч < before 1790 →
     * «МОЖНО БРАТЬ», Лента даёт after −83.8 > before −139.9 → «ОДНОЗНАЧНО ДА».
     * Разные решения = флаг реально дошёл до порядка объезда.
     */
    @Test
    fun feedOrderFlagReachesRouteOptimizer() {
        val dist = listOf(
            listOf(0.0, 200.0, 1.0, 1.0, 200.0),
            listOf(200.0, 0.0, 1.0, 1.0, 1.0),
            listOf(1.0, 1.0, 0.0, 5.0, 200.0),
            listOf(1.0, 1.0, 5.0, 0.0, 200.0),
            listOf(200.0, 1.0, 200.0, 200.0, 0.0),
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
        assertEquals("МОЖНО БРАТЬ", optimized.decision)
        assertEquals("ОДНОЗНАЧНО ДА", feedOrder.decision)
    }

    /**
     * Работа на точке считается СВОЕЙ длительностью, а не средней по заказам (отчёт 878).
     *
     * Без этого приём с 9 до 13 шёл за 30 плановых минут: минуты дня занижены, средний
     * ₽/час раздут, и новый заказ обязан побить завышенную планку. Проверяем, что сумма
     * с сервера действительно вытесняет «K × средняя», а не просто лежит в поле.
     */
    @Test
    fun longAppointmentUsesItsOwnDuration() {
        val short = OfflineVerdict.evaluate(baseInput(candidateIncome = 800.0))
        val long = OfflineVerdict.evaluate(
            baseInput(candidateIncome = 800.0).copy(existingServiceMinutes = 240.0),
        )
        // Тот же заказ на дне с четырёхчасовым приёмом обязан выглядеть НЕ ХУЖЕ: средний
        // ₽/час дня падает, планка опускается, вердикт не может стать строже.
        val rank = mapOf("skip" to 0, "edge" to 1, "go" to 2)
        assertTrue(
            "длинный приём ужесточил вердикт: было ${short.verdict}, стало ${long.verdict}",
            rank.getValue(long.verdict) >= rank.getValue(short.verdict),
        )
    }

    /** Нет поля в кеше (снимок сделан до обновления) — считаем по-старому, без падений. */
    @Test
    fun missingServiceMinutesFallsBackToAverage() {
        val fallback = OfflineVerdict.evaluate(baseInput(candidateIncome = 800.0))
        val explicit = OfflineVerdict.evaluate(
            // 1 заказ × 30 плановых минут — ровно то, что считала старая формула.
            baseInput(candidateIncome = 800.0).copy(existingServiceMinutes = 30.0),
        )
        assertEquals(explicit.decision, fallback.decision)
        assertEquals(explicit.score, fallback.score)
    }

    /**
     * Готовое «до» с сервера вытесняет самосборку — видно по ОТТЕНКУ вердикта (отчёт 913).
     *
     * В кеше телефона только принятые заказы: завершённый визит схлопнут в точку старта,
     * телемедицина, работа в офисе, расходы дня и компенсации не едут вовсе. Сервер знает
     * день целиком, телефон — нет.
     *
     * Богатый день выбран не случайно. После варианта А дневной ₽/час различает ровно одно:
     * «ОДНОЗНАЧНО ДА» (заказ поднимает средний ₽/час) против «МОЖНО БРАТЬ» (опускает).
     * На самосборном дне тот же заказ средний ₽/час поднимает, а на дне по 20 000 ₽/час —
     * опускает. Возьми я день ПРОВАЛЬНЫЙ, оттенок совпал бы с самосборным (там заказ тоже
     * поднимает ставку), и тест не поймал бы ничего — ровно на этом он и упал в CI.
     */
    @Test
    fun authoritativeDayBeforeChangesTheShade() {
        val homemade = OfflineVerdict.evaluate(baseInput(candidateIncome = 800.0))
        // Тот же день, но сервер знает: чистыми 20 000 ₽ за час — заказ такую планку снижает.
        val fromServer = OfflineVerdict.evaluate(
            baseInput(candidateIncome = 800.0).copy(
                dayBeforeNet = 20000.0,
                dayBeforeMinutes = 60.0,
            ),
        )
        // Маржа самого заказа от этого не меняется — она про заказ, а не про день.
        assertEquals(homemade.marginalProfit, fromServer.marginalProfit, 1e-9)
        assertEquals(homemade.marginalHourly, fromServer.marginalHourly, 1e-9)
        assertEquals("ОДНОЗНАЧНО ДА", homemade.decision)
        assertEquals("МОЖНО БРАТЬ", fromServer.decision)
    }

    /**
     * Дневное «до» НЕ переворачивает вердикт — и это честная граница этапа 69.
     *
     * После варианта А заказ судит его собственная ставка: планка берётся из настроек и
     * ожидаемой ставки часа, а средний ₽/час дня в неё не входит. Значит и полный день с
     * сервера не может превратить «бери» в «невыгодно». Ставлю это тестом, чтобы не
     * приписывать этапу 69 силы, которой у него нет: он чинит оттенок вердикта и число в
     * плитке «чистыми/ч», а не пропуск заказа.
     */
    @Test
    fun authoritativeDayNeverFlipsTheVerdict() {
        val homemade = OfflineVerdict.evaluate(baseInput(candidateIncome = 800.0))
        val ruinedDay = OfflineVerdict.evaluate(
            baseInput(candidateIncome = 800.0).copy(
                dayBeforeNet = -100000.0,
                dayBeforeMinutes = 60.0,
            ),
        )
        assertEquals(homemade.verdict, ruinedDay.verdict)
        assertEquals(homemade.score, ruinedDay.score)
    }

    /**
     * Дневные ₽/час выдаются наружу только когда день пришёл с сервера.
     *
     * Их показывает плитка «чистыми/ч» на экране оценки. Отдать туда самосборное число
     * значит вернуть ровно ту ошибку, ради которой затевался этап 69, — поэтому на старом
     * кеше здесь null, а не «примерно посчитали сами».
     */
    @Test
    fun dayHourlyIsExposedOnlyWhenTheServerSentTheDay() {
        val homemade = OfflineVerdict.evaluateFull(baseInput(candidateIncome = 800.0))
        assertNull(homemade.dayBeforeHourly)
        assertNull(homemade.dayAfterHourly)

        val fromServer = OfflineVerdict.evaluateFull(
            baseInput(candidateIncome = 800.0).copy(
                dayBeforeNet = 5000.0,
                dayBeforeMinutes = 100.0,
            ),
        )
        // 5000 ₽ за 100 минут — ровно 3000 ₽/час, без арифметики телефона.
        assertEquals(3000.0, fromServer.dayBeforeHourly!!, 1e-9)
        // Заказ на 800 ₽ добавляет минут больше, чем денег: ставка дня падает, но остаётся
        // положительной — то самое число, что человек увидит в плитке.
        assertTrue("ставка после заказа должна быть ниже", fromServer.dayAfterHourly!! < 3000.0)
        assertTrue("ставка после заказа должна остаться положительной", fromServer.dayAfterHourly!! > 0)
    }

    /** Старый кеш без готового «до» считается ровно как раньше — до последней копейки. */
    @Test
    fun oldCacheKeepsTheOldNumbers() {
        val input = baseInput(candidateIncome = 800.0)
        val result = OfflineVerdict.evaluate(input)

        // Дословно старая формула: «после» через ПОЛНЫЕ км и минуты маршрута.
        val extra = RouteOptimizer.candidateExtra(
            input.distances, input.durations, input.existingCount, input.anchors,
        )
        val costPerKm = input.fuelPerKm + input.maintenancePerKm + input.extraPerKm
        val incomeSum = input.existingIncomes.sum()
        val beforeNet = incomeSum - extra.beforeKm * costPerKm - input.cancelledLeadCosts
        val afterNet = incomeSum + input.candidateIncome - input.candidateResponseCost -
            extra.afterKm * costPerKm - input.cancelledLeadCosts
        val existingService = input.existingCount * input.serviceMinutes
        val beforeMinutes = extra.beforeMinutes + existingService
        val afterMinutes = extra.afterMinutes + existingService + input.serviceMinutes
        fun hourly(net: Double, min: Double) = if (min <= 0) 0.0 else net / min * 60

        val expected = ProfitabilityCalculator.evaluate(
            ProfitabilityCalculator.Input(
                income = input.candidateIncome,
                extraKm = extra.extraKm,
                extraDriveMinutes = extra.extraDriveMinutes,
                serviceMinutes = input.serviceMinutes,
                fuelPerKm = input.fuelPerKm,
                maintenancePerKm = input.maintenancePerKm,
                extraPerKm = input.extraPerKm,
                beforeHourly = hourly(beforeNet, beforeMinutes),
                afterHourly = hourly(afterNet, afterMinutes),
                minHourly = input.minHourly,
                minMarginalHourly = input.minMarginalHourly,
                isBaseDistrict = input.isBaseDistrict,
                existingBaseCount = input.existingBaseCount,
                outsideMinHourly = input.outsideMinHourly,
                outsideMinExtra = input.outsideMinExtra,
                blocksOutsideZone = input.blocksOutsideZone,
                responseCost = input.candidateResponseCost,
                existingCount = input.existingCount,
            ),
        )
        assertEquals(expected.decision, result.decision)
        assertEquals(expected.score, result.score)
        assertEquals(expected.marginalProfit, result.marginalProfit, 1e-9)
    }
}
