package com.homevisit.location.calc

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Золотые векторы порядка маршрута (Фаза 3.4): Kotlin RouteOptimizer выдаёт ТОТ ЖЕ порядок,
 * что серверный optimization_service._best_order. Файл route_vectors.json — общий с
 * питоновским CI (генерится scripts.gen_route_vectors). Падение = TSP на телефоне разошёлся
 * с сервером; чинить перегенерацией векторов И правкой RouteOptimizer, а не подгонкой теста.
 */
class RouteOptimizerTest {

    private fun loadVectors(): JSONArray {
        val stream = javaClass.classLoader!!.getResourceAsStream("route_vectors.json")
            ?: error("route_vectors.json не найден в test/resources")
        return JSONArray(stream.bufferedReader().use { it.readText() })
    }

    private fun matrix(j: JSONArray): List<List<Double>> =
        (0 until j.length()).map { r ->
            val row = j.getJSONArray(r)
            (0 until row.length()).map { c -> row.getDouble(c) }
        }

    private fun intList(j: JSONArray): List<Int> =
        (0 until j.length()).map { j.getInt(it) }

    private fun loadCandidateVectors(): JSONArray {
        val stream = javaClass.classLoader!!.getResourceAsStream("route_candidate_vectors.json")
            ?: error("route_candidate_vectors.json не найден в test/resources")
        return JSONArray(stream.bufferedReader().use { it.readText() })
    }

    @Test
    fun matchesCandidateDeltaVectors() {
        val vectors = loadCandidateVectors()
        assertTrue("векторов мало", vectors.length() >= 3)
        for (i in 0 until vectors.length()) {
            val vec = vectors.getJSONObject(i)
            val name = vec.getString("name")
            val inputs = vec.getJSONObject("inputs")
            val distances = matrix(inputs.getJSONArray("distances_km"))
            val durations = matrix(inputs.getJSONArray("durations_minutes"))
            val existingCount = inputs.getInt("existing_count")
            val anchors = intList(inputs.getJSONArray("anchors"))
            val exp = vec.getJSONObject("expected")

            val extra = RouteOptimizer.candidateExtra(distances, durations, existingCount, anchors)
            assertEquals("$name extra_km", exp.getDouble("extra_km"), extra.extraKm, 1e-6)
            assertEquals("$name extra_drive_minutes", exp.getDouble("extra_drive_minutes"), extra.extraDriveMinutes, 1e-6)
            assertEquals("$name before_km", exp.getDouble("before_km"), extra.beforeKm, 1e-6)
            assertEquals("$name after_km", exp.getDouble("after_km"), extra.afterKm, 1e-6)
        }
    }

    @Test
    fun matchesGoldenVectors() {
        val vectors = loadVectors()
        assertTrue("векторов мало", vectors.length() >= 5)
        for (i in 0 until vectors.length()) {
            val vec = vectors.getJSONObject(i)
            val name = vec.getString("name")
            val inputs = vec.getJSONObject("inputs")
            val distances = matrix(inputs.getJSONArray("distances_km"))
            val durations = matrix(inputs.getJSONArray("durations_minutes"))
            val visitsCount = inputs.getInt("visits_count")
            val anchors = intList(inputs.getJSONArray("anchors"))
            val exp = vec.getJSONObject("expected")

            val summary = RouteOptimizer.summarize(distances, durations, visitsCount, anchors)
            assertEquals("$name order", intList(exp.getJSONArray("order")), summary.order)
            assertEquals("$name total_km", exp.getDouble("total_km"), summary.totalKm, 1e-6)
            assertEquals("$name total_minutes", exp.getDouble("total_minutes"), summary.totalMinutes, 1e-6)
            assertEquals("$name route_minutes", exp.getDouble("route_minutes"), summary.routeMinutes, 1e-6)
        }
    }
}
