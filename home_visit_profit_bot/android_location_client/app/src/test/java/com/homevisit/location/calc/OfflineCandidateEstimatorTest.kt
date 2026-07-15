package com.homevisit.location.calc

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Офлайн-оценка нового кандидата по кеш-матрице + достройке плеч по прямой (Фаза 3.4/3.5).
 * Проверяем: далёкий адрес обходится дороже близкого (extraCarCost монотонен по удалению),
 * жирный чек у близкого — go, а формула прямой совпадает с серверной (радиус 6371,
 * km×factor, km/speed×60 — проверяется тем, что расчёт вообще сходится к разумным числам).
 */
class OfflineCandidateEstimatorTest {

    private val start = OfflineCandidateEstimator.LatLon(55.7500, 37.6200)
    private val order1 = OfflineCandidateEstimator.LatLon(55.7600, 37.6400)
    private val finish = OfflineCandidateEstimator.LatLon(55.7500, 37.6200)
    private val cachedPoints = listOf(start, order1, finish)

    // Кеш-матрица [старт, заказ1, финиш] (км) — реальные плечи OSRM (для теста — правдоподобные).
    private val cachedDist = listOf(
        listOf(0.0, 2.0, 0.0),
        listOf(2.0, 0.0, 2.0),
        listOf(0.0, 2.0, 0.0),
    )
    private val cachedDur = cachedDist.map { row -> row.map { it * 2.0 } }

    private val coeff = OfflineCandidateEstimator.Coefficients(
        straightLineFactor = 1.35,
        avgSpeedKmh = 30.0,
        serviceMinutes = 30.0,
        fuelPerKm = 6.0,
        maintenancePerKm = 4.0,
        minHourly = 300.0,
        minMarginalHourly = 200.0,
    )

    private fun estimate(candidate: OfflineCandidateEstimator.LatLon, income: Double) =
        OfflineCandidateEstimator.estimate(
            cachedPoints = cachedPoints,
            cachedDistances = cachedDist,
            cachedDurations = cachedDur,
            candidate = candidate,
            candidateIncome = income,
            existingIncomes = listOf(1000.0),
            coeff = coeff,
        )

    @Test
    fun fartherCandidateCostsMore() {
        val near = estimate(OfflineCandidateEstimator.LatLon(55.7610, 37.6410), income = 800.0)
        val far = estimate(OfflineCandidateEstimator.LatLon(55.9000, 38.0000), income = 800.0)
        assertTrue("далёкий кандидат дороже по машине", far.extraCarCost > near.extraCarCost)
        assertTrue("близкий кандидат выгоднее по ₽/км", near.marginalPerKm > far.marginalPerKm)
    }

    @Test
    fun richNearOrderIsGo() {
        val result = estimate(OfflineCandidateEstimator.LatLon(55.7605, 37.6405), income = 5000.0)
        assertEquals("go", result.verdict)
        assertTrue("маржа положительна", result.marginalProfit > 0)
    }

    @Test
    fun tinyIncomeFarIsNotGo() {
        val result = estimate(OfflineCandidateEstimator.LatLon(55.9500, 38.1000), income = 100.0)
        assertTrue("копеечный дальний заказ не go", result.verdict != "go")
    }
}
