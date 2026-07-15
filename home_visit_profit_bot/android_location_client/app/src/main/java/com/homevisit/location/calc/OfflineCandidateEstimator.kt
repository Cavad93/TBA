package com.homevisit.location.calc

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Офлайн-оценка НОВОГО кандидата в самолётном режиме (Фаза 3.4/3.5).
 *
 * Кешированная матрица /api/route/matrix покрывает уже известные точки дня
 * [старт, заказы…, финиш] реальными плечами OSRM. Нового адреса в ней нет —
 * его плечи достраиваем ПО ПРЯМОЙ (haversine × straight_line_factor для км,
 * км / avg_speed × 60 для минут) ровно так же, как сервер считает вне покрытия
 * карт. Это честная оценка (не выдумка нуля): человек видит вердикт мгновенно,
 * а при возврате сети сервер пересчитает точным OSRM и лог Ф3.6 сверит.
 *
 * Индексация результата — как ждёт RouteOptimizer/OfflineVerdict:
 * [старт(0), заказы(1..K), кандидат(K+1), финиш(K+2)].
 */
object OfflineCandidateEstimator {

    data class LatLon(val lat: Double, val lon: Double)

    data class Coefficients(
        val straightLineFactor: Double,
        val avgSpeedKmh: Double,
        val serviceMinutes: Double,
        val fuelPerKm: Double,
        val maintenancePerKm: Double,
        val minHourly: Double,
        val minMarginalHourly: Double,
        val outsideMinHourly: Double? = null,
        val outsideMinExtra: Double = 0.0,
    )

    /**
     * @param cachedPoints  координаты точек кеш-матрицы в порядке [старт, заказы…, финиш]
     * @param cachedDistances/cachedDurations  кеш-матрицы того же порядка (размер n×n, n=K+2)
     * @param candidate  координаты нового адреса
     * @param existingIncomes  доходы K уже принятых заказов
     * @param anchors  индексы onsite-якорей в ПОЛНОЙ (augmented) индексации
     */
    fun estimate(
        cachedPoints: List<LatLon>,
        cachedDistances: List<List<Double>>,
        cachedDurations: List<List<Double>>,
        candidate: LatLon,
        candidateIncome: Double,
        existingIncomes: List<Double>,
        coeff: Coefficients,
        anchors: List<Int> = emptyList(),
        isBaseDistrict: Boolean = true,
        existingBaseCount: Int = 0,
        blocksOutsideZone: Boolean = false,
    ): ProfitabilityCalculator.Result {
        val n = cachedPoints.size
        require(n >= 2) { "кеш-матрица должна содержать хотя бы старт и финиш" }
        require(cachedDistances.size == n && cachedDurations.size == n) {
            "размер кеш-матрицы не совпадает с числом точек"
        }
        val k = n - 2 // число уже принятых заказов
        val candIdx = k + 1
        val m = n + 1

        // Координаты в augmented-индексации: старт+заказы, кандидат, финиш.
        val augPoints = ArrayList<LatLon>(m)
        for (i in 0..k) augPoints.add(cachedPoints[i])
        augPoints.add(candidate)
        augPoints.add(cachedPoints[n - 1]) // финиш

        // old-индекс точки по new-индексу (кандидат не отображается).
        fun oldIndex(newIdx: Int): Int = when {
            newIdx <= k -> newIdx
            newIdx == m - 1 -> n - 1 // финиш
            else -> -1               // кандидат
        }

        val dist = Array(m) { DoubleArray(m) }
        val dur = Array(m) { DoubleArray(m) }
        for (a in 0 until m) {
            for (b in 0 until m) {
                if (a == b) continue
                val oa = oldIndex(a)
                val ob = oldIndex(b)
                if (oa >= 0 && ob >= 0) {
                    dist[a][b] = cachedDistances[oa][ob]
                    dur[a][b] = cachedDurations[oa][ob]
                } else {
                    val km = haversineKm(augPoints[a], augPoints[b]) * coeff.straightLineFactor
                    dist[a][b] = km
                    dur[a][b] = if (coeff.avgSpeedKmh > 0) km / coeff.avgSpeedKmh * 60.0 else 0.0
                }
            }
        }

        return OfflineVerdict.evaluate(
            OfflineVerdict.Input(
                distances = dist.map { it.toList() },
                durations = dur.map { it.toList() },
                existingCount = k,
                existingIncomes = existingIncomes,
                candidateIncome = candidateIncome,
                anchors = anchors,
                serviceMinutes = coeff.serviceMinutes,
                fuelPerKm = coeff.fuelPerKm,
                maintenancePerKm = coeff.maintenancePerKm,
                minHourly = coeff.minHourly,
                minMarginalHourly = coeff.minMarginalHourly,
                outsideMinHourly = coeff.outsideMinHourly,
                outsideMinExtra = coeff.outsideMinExtra,
                isBaseDistrict = isBaseDistrict,
                existingBaseCount = existingBaseCount,
                blocksOutsideZone = blocksOutsideZone,
            ),
        )
    }

    /** Гаверсинус, км. Тот же радиус Земли (6371 км), что серверный _haversine_km. */
    private fun haversineKm(a: LatLon, b: LatLon): Double {
        val r = 6371.0
        val dLat = Math.toRadians(b.lat - a.lat)
        val dLon = Math.toRadians(b.lon - a.lon)
        val lat1 = Math.toRadians(a.lat)
        val lat2 = Math.toRadians(b.lat)
        val h = sin(dLat / 2) * sin(dLat / 2) +
            sin(dLon / 2) * sin(dLon / 2) * cos(lat1) * cos(lat2)
        return 2 * r * atan2(sqrt(h), sqrt(1 - h))
    }
}
