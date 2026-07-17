package com.homevisit.location.calc

/**
 * Порядок объезда заказов на телефоне (Фаза 3.4) — точный перенос серверного
 * optimization_service._best_order на матрицу из /api/route/matrix (Ф3.2).
 *
 * Раздел труда: сервер даёт матрицу длительностей/расстояний, телефон комбинаторику
 * крутит сам — мгновенно и офлайн. Порядок обязан совпадать с сервером до индекса:
 * это проверяют золотые векторы route_vectors.json в обоих CI (как candidate_vectors.json
 * для выгодности). Разойдётся — «на телефоне один маршрут, на сервере другой» — падают оба.
 *
 * Индексация точек как на сервере: 0 — старт дня, 1..visitsCount — заказы, visitsCount+1 —
 * финиш. Оптимизируем по длительности (минуты), а не по километрам, — так же, как сервер.
 * Считается ТОЛЬКО по событию (добавили/завершили заказ), не фоновым циклом — батарея священна.
 */
object RouteOptimizer {

    data class Summary(
        val order: List<Int>,     // индексы заказов (1..n) в порядке объезда
        val totalKm: Double,
        val totalMinutes: Double,
        val routeMinutes: Double, // сумма по _route_minutes (без плеча старта) — для сверки
    )

    /**
     * Оптимальный порядок заказов. anchors — позиции заказов-якорей (onsite с фиксированным
     * временем) в порядке их времени; они остаются на местах, гибкие встраиваются вокруг.
     *
     * respectFeedOrder — перенос серверного `_order_indices` при выключенном auto_optimize
     * (Этап 20): человек строит порядок сам, и день считается ровно по Ленте, без
     * оптимизации. Без этого флага телефон офлайн всегда оптимизировал и расходился
     * с сервером по extra_km на первом же дне с двумя заказами.
     */
    fun bestOrder(
        durations: List<List<Double>>,
        visitsCount: Int,
        anchors: List<Int> = emptyList(),
        respectFeedOrder: Boolean = false,
    ): List<Int> {
        if (respectFeedOrder) return (1..visitsCount).toList()
        val visitIndices = (1..visitsCount).toList()
        val finishIndex = visitsCount + 1
        if (anchors.isNotEmpty()) return orderAroundAnchors(durations, visitIndices, anchors, finishIndex)
        if (visitsCount <= 8) return bestByFullPermutation(durations, visitIndices, finishIndex)
        val nn = nearestNeighborOrder(durations, visitIndices, finishIndex)
        return twoOpt(durations, nn, finishIndex)
    }

    data class CandidateExtra(
        val extraKm: Double,       // лишние км ради заказа (после отсечки дребезга)
        val extraDriveMinutes: Double,
        val beforeKm: Double,
        val afterKm: Double,
        val beforeMinutes: Double,
        val afterMinutes: Double,
    )

    /**
     * Лишние км/минуты ради кандидата — как серверный calculate_candidate_impact: разница
     * оптимального маршрута дня С заказом и БЕЗ. Точки — [старт(0), заказы(1..K),
     * кандидат(K+1), финиш(K+2)]; кандидат всегда предпоследний (сервер добавляет его
     * последним визитом перед финишем). before считается на подматрице без кандидата.
     * anchors — индексы onsite-якорей в ПОЛНОЙ индексации (кандидат якорем не бывает).
     *
     * Отсечки дребезга (0.05 км, 0.5 мин) — те же, что candidate_pure/_zero_tiny, иначе
     * подъезд к соседнему дому считался бы дорогой. extra_km/min идут в ProfitabilityCalculator.
     */
    fun candidateExtra(
        distances: List<List<Double>>,
        durations: List<List<Double>>,
        existingCount: Int,
        anchors: List<Int> = emptyList(),
        respectFeedOrder: Boolean = false,
    ): CandidateExtra {
        val candidateIndex = existingCount + 1
        val after = summarize(distances, durations, existingCount + 1, anchors, respectFeedOrder)
        val beforeDist = dropIndex(distances, candidateIndex)
        val beforeDur = dropIndex(durations, candidateIndex)
        val anchorsBefore = anchors.filter { it != candidateIndex } // индексы 1..K не сдвигаются
        val before = summarize(beforeDist, beforeDur, existingCount, anchorsBefore, respectFeedOrder)
        return CandidateExtra(
            extraKm = zeroTiny(after.totalKm - before.totalKm, 0.05),
            extraDriveMinutes = zeroTiny(after.totalMinutes - before.totalMinutes, 0.5),
            beforeKm = before.totalKm,
            afterKm = after.totalKm,
            beforeMinutes = before.totalMinutes,
            afterMinutes = after.totalMinutes,
        )
    }

    /** Отсечка дребезга — как candidate_pure._zero_tiny. */
    private fun zeroTiny(value: Double, epsilon: Double): Double =
        if (kotlin.math.abs(value) < epsilon) 0.0 else value

    /** Матрица без строки и столбца index (сброс кандидата для расчёта «до»). */
    private fun dropIndex(matrix: List<List<Double>>, index: Int): List<List<Double>> =
        matrix.filterIndexed { i, _ -> i != index }
            .map { row -> row.filterIndexed { j, _ -> j != index } }

    /** Полный путь: суммарные км/минуты по 0 → order → finish (как _summary_from_order). */
    fun summarize(
        distances: List<List<Double>>,
        durations: List<List<Double>>,
        visitsCount: Int,
        anchors: List<Int> = emptyList(),
        respectFeedOrder: Boolean = false,
    ): Summary {
        val order = bestOrder(durations, visitsCount, anchors, respectFeedOrder)
        val finishIndex = visitsCount + 1
        val path = listOf(0) + order + listOf(finishIndex)
        var totalKm = 0.0
        var totalMinutes = 0.0
        for (i in 0 until path.size - 1) {
            totalKm += distances[path[i]][path[i + 1]]
            totalMinutes += durations[path[i]][path[i + 1]]
        }
        return Summary(order, totalKm, totalMinutes, routeMinutes(durations, order, finishIndex))
    }

    // --- перенос _route_minutes: 0 → order → finish по длительностям ---
    private fun routeMinutes(durations: List<List<Double>>, order: List<Int>, finishIndex: Int): Double {
        var current = 0
        var total = 0.0
        for (pointIndex in order) {
            total += durations[current][pointIndex]
            current = pointIndex
        }
        total += durations[current][finishIndex]
        return total
    }

    // --- перенос перебора ≤8: лексикографический порядок перестановок [1..n], первый минимум ---
    private fun bestByFullPermutation(durations: List<List<Double>>, visitIndices: List<Int>, finishIndex: Int): List<Int> {
        var best: List<Int>? = null
        var bestCost = Double.POSITIVE_INFINITY
        permutations(visitIndices) { perm ->
            val cost = routeMinutes(durations, perm, finishIndex)
            // strict `<` — при равенстве оставляем ПЕРВУЮ (как Python min), поэтому перебор
            // идёт в том же лексикографическом порядке, что itertools.permutations([1..n]).
            if (cost < bestCost) {
                bestCost = cost
                best = perm
            }
        }
        return best ?: visitIndices
    }

    /**
     * Перестановки в лексикографическом порядке (как itertools.permutations отсортированного
     * входа): на каждом шаге берём оставшиеся по возрастанию. callback на каждую полную.
     */
    private fun permutations(items: List<Int>, callback: (List<Int>) -> Unit) {
        val remaining = items.toMutableList()
        val current = ArrayList<Int>(items.size)
        fun recurse() {
            if (remaining.isEmpty()) { callback(current.toList()); return }
            for (i in remaining.indices) {
                val value = remaining.removeAt(i)
                current.add(value)
                recurse()
                current.removeAt(current.size - 1)
                remaining.add(i, value)
            }
        }
        recurse()
    }

    // --- перенос _nearest_neighbor_order: ближайший по длительности, значения различны → без ничьих ---
    private fun nearestNeighborOrder(durations: List<List<Double>>, visitIndices: List<Int>, finishIndex: Int): List<Int> {
        val remaining = visitIndices.toMutableList()
        var current = 0
        val order = ArrayList<Int>(visitIndices.size)
        while (remaining.isNotEmpty()) {
            var bestIdx = 0
            var bestVal = Double.POSITIVE_INFINITY
            for (i in remaining.indices) {
                val d = durations[current][remaining[i]]
                if (d < bestVal) { bestVal = d; bestIdx = i }
            }
            val next = remaining.removeAt(bestIdx)
            order.add(next)
            current = next
        }
        return order
    }

    // --- перенос _two_opt: разворот сегмента [left,right), принимаем при строгом улучшении ---
    private fun twoOpt(durations: List<List<Double>>, order: List<Int>, finishIndex: Int): List<Int> {
        var best = order.toList()
        var improved = true
        while (improved) {
            improved = false
            for (left in 0 until best.size - 1) {
                for (right in left + 2..best.size) {
                    val candidate = best.subList(0, left) +
                        best.subList(left, right).reversed() +
                        best.subList(right, best.size)
                    if (routeMinutes(durations, candidate, finishIndex) < routeMinutes(durations, best, finishIndex)) {
                        best = candidate
                        improved = true
                    }
                }
            }
        }
        return best
    }

    // --- перенос _order_around_anchors: cheapest insertion, якоря на местах ---
    private fun orderAroundAnchors(
        durations: List<List<Double>>,
        visitIndices: List<Int>,
        anchors: List<Int>,
        finishIndex: Int,
    ): List<Int> {
        val order = anchors.toMutableList()
        val flexible = visitIndices.filter { it !in anchors }
        for (index in flexible) {
            var bestPosition = 0
            var bestCost = Double.POSITIVE_INFINITY
            for (position in 0..order.size) {
                val candidate = order.subList(0, position) + listOf(index) + order.subList(position, order.size)
                val cost = routeMinutes(durations, candidate, finishIndex)
                if (cost < bestCost) { bestCost = cost; bestPosition = position }
            }
            order.add(bestPosition, index)
        }
        return order
    }
}
