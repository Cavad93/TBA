package com.homevisit.location.calc

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Золотые векторы выгодности (Фаза 3.1): Kotlin-калькулятор совпадает с сервером до
 * копейки. Файл candidate_vectors.json — тот же, что гоняет питоновский CI (генерится
 * scripts.gen_golden_vectors). Падение = формула на телефоне разошлась с сервером;
 * чинить перегенерацией векторов И правкой ProfitabilityCalculator, а не подгонкой теста.
 */
class ProfitabilityCalculatorTest {

    private fun loadVectors(): JSONArray {
        val stream = javaClass.classLoader!!.getResourceAsStream("candidate_vectors.json")
            ?: error("candidate_vectors.json не найден в test/resources")
        return JSONArray(stream.bufferedReader().use { it.readText() })
    }

    private fun inputOf(j: JSONObject) = ProfitabilityCalculator.Input(
        income = j.getDouble("income"),
        extraKm = j.getDouble("extra_km"),
        extraDriveMinutes = j.getDouble("extra_drive_minutes"),
        serviceMinutes = j.getDouble("service_minutes"),
        fuelPerKm = j.getDouble("fuel_per_km"),
        maintenancePerKm = j.getDouble("maintenance_per_km"),
        beforeHourly = j.getDouble("before_hourly"),
        afterHourly = j.getDouble("after_hourly"),
        minHourly = j.getDouble("min_hourly"),
        minMarginalHourly = j.getDouble("min_marginal_hourly"),
        isBaseDistrict = j.getBoolean("is_base_district"),
        existingBaseCount = j.getInt("existing_base_count"),
        outsideMinHourly = if (j.has("outside_min_hourly")) j.getDouble("outside_min_hourly") else null,
        outsideMinExtra = j.optDouble("outside_min_extra", 0.0),
        blocksOutsideZone = j.optBoolean("blocks_outside_zone", false),
        parkingCost = j.optDouble("parking_cost", 0.0),
        responseCost = j.optDouble("response_cost", 0.0),
    )

    @Test
    fun matchesGoldenVectors() {
        val vectors = loadVectors()
        assertTrue("векторов мало", vectors.length() >= 5)
        for (i in 0 until vectors.length()) {
            val vec = vectors.getJSONObject(i)
            val name = vec.getString("name")
            val result = ProfitabilityCalculator.evaluate(inputOf(vec.getJSONObject("inputs")))
            val exp = vec.getJSONObject("expected")
            assertEquals("$name decision", exp.getString("decision"), result.decision)
            assertEquals("$name verdict", exp.getString("verdict"), result.verdict)
            assertEquals("$name score", exp.getInt("score"), result.score)
            assertEquals("$name marginal_profit", exp.getDouble("marginal_profit"), result.marginalProfit, 1e-9)
            assertEquals("$name marginal_hourly", exp.getDouble("marginal_hourly"), result.marginalHourly, 1e-9)
            assertEquals("$name marginal_per_km", exp.getDouble("marginal_per_km"), result.marginalPerKm, 1e-9)
            assertEquals("$name extra_car_cost", exp.getDouble("extra_car_cost"), result.extraCarCost, 1e-9)
            assertEquals("$name extra_total_minutes", exp.getDouble("extra_total_minutes"), result.extraTotalMinutes, 1e-9)
        }
    }
}
