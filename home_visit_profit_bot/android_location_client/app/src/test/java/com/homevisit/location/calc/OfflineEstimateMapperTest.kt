package com.homevisit.location.calc

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Сборка офлайн-вердикта из кеша /api/route/matrix/day (Фаза 3.4/3.5). Проверяем, что
 * кеш дня + координаты нового адреса дают осмысленный CandidateEstimate: вердикт из
 * известного набора, балл в диапазоне, деньги на км/час посчитаны, плечи достроены.
 */
class OfflineEstimateMapperTest {

    private fun matrix(rows: List<List<Double>>): JSONArray {
        val arr = JSONArray()
        rows.forEach { row -> arr.put(JSONArray().apply { row.forEach { put(it) } }) }
        return arr
    }

    private fun dayCache(): JSONObject {
        // 3 точки: старт(0), заказ(1), финиш(2)=старт. Плечи заданы явно (детерминизм).
        val points = JSONArray()
            .put(JSONObject().put("lat", 59.930).put("lon", 30.310).put("label", "старт").put("visit_id", JSONObject.NULL))
            .put(JSONObject().put("lat", 59.940).put("lon", 30.330).put("label", "Заказ").put("visit_id", 10))
            .put(JSONObject().put("lat", 59.930).put("lon", 30.310).put("label", "финиш").put("visit_id", JSONObject.NULL))
        val dist = matrix(listOf(
            listOf(0.0, 2.0, 0.0),
            listOf(2.0, 0.0, 2.0),
            listOf(0.0, 2.0, 0.0),
        ))
        val dur = matrix(listOf(
            listOf(0.0, 5.0, 0.0),
            listOf(5.0, 0.0, 5.0),
            listOf(0.0, 5.0, 0.0),
        ))
        val coeff = JSONObject()
            .put("fuel_per_km", 8.0)
            .put("maintenance_per_km", 4.0)
            .put("cost_per_km", 12.0)
            .put("min_hourly_income", 600.0)
            .put("min_marginal_hourly_income", 600.0)
            .put("outside_zone_min_hourly_income", 600.0)
            .put("outside_zone_min_extra_payment", 0.0)
            .put("service_minutes", 20.0)
            .put("avg_speed_kmh", 30.0)
            .put("straight_line_factor", 1.35)
        return JSONObject()
            .put("points", points)
            .put("distances_km", dist)
            .put("durations_minutes", dur)
            .put("incomes", JSONArray().put(2000.0))
            .put("coefficients", coeff)
            .put("snapshot_version", "test")
    }

    @Test
    fun mapsCacheToEstimate() {
        val est = OfflineEstimateMapper.fromDayMatrix(
            dayCache(), candidateLat = 59.945, candidateLon = 30.340,
            income = 1500.0, address = "Новый адрес", clinic = "",
        )
        assertNotNull(est)
        est!!
        assertEquals("Новый адрес", est.address)
        assertEquals(1500.0, est.income, 0.0001)
        assertTrue("вердикт из набора", est.decision.isNotBlank())
        assertTrue("балл 1..100", est.score in 1..100)
        assertEquals(12.0, est.costPerKm, 0.0001)
        assertTrue("плечо кандидата достроено", est.extraKm > 0)
    }

    @Test
    fun returnsNullOnBrokenCache() {
        val broken = JSONObject().put("points", JSONArray())
        val est = OfflineEstimateMapper.fromDayMatrix(broken, 59.9, 30.3, 1000.0, "x", "")
        assertEquals(null, est)
    }
}
