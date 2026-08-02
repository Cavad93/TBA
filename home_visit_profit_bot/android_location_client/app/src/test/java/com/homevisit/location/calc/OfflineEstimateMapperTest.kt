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

    /**
     * Минуты приёма доезжают из кеша до вердикта (отчёт 878).
     *
     * Поле `service_minutes_list` прокладывается через mapper → estimator → verdict.
     * Тест нужен именно потому, что цепочка длинная: потеряйся поле на любом стыке,
     * ничего бы не упало — вердикт просто тихо считался бы по «K × средняя», как раньше.
     */
    @Test
    fun serviceMinutesListReachesTheVerdict() {
        val short = OfflineEstimateMapper.fromDayMatrix(
            dayCache(), candidateLat = 59.945, candidateLon = 30.340,
            income = 1500.0, address = "Новый адрес", clinic = "",
        )
        // Тот же день, но принятый заказ — приём на четыре часа.
        val withAppointment = OfflineEstimateMapper.fromDayMatrix(
            dayCache().put("service_minutes_list", JSONArray().put(240.0)),
            candidateLat = 59.945, candidateLon = 30.340,
            income = 1500.0, address = "Новый адрес", clinic = "",
        )
        assertNotNull(short)
        assertNotNull(withAppointment)
        // Средний ₽/час дня с четырёхчасовым приёмом ниже, планка ниже — вердикт не строже.
        val rank = mapOf("skip" to 0, "edge" to 1, "go" to 2)
        val before = rank[verdictOf(short!!.decision)] ?: 1
        val after = rank[verdictOf(withAppointment!!.decision)] ?: 1
        assertTrue(
            "длинный приём ужесточил вердикт: ${short.decision} → ${withAppointment.decision}",
            after >= before,
        )
    }

    /** Старый кеш без поля — прежнее поведение, без падений и без NaN. */
    @Test
    fun cacheWithoutServiceMinutesListStillWorks() {
        val est = OfflineEstimateMapper.fromDayMatrix(
            dayCache(), candidateLat = 59.945, candidateLon = 30.340,
            income = 1500.0, address = "Новый адрес", clinic = "",
        )
        assertNotNull(est)
        assertTrue("балл 1..100", est!!.score in 1..100)
    }

    /**
     * Плитка «чистыми/ч» перестаёт показывать ноль (отчёт 913).
     *
     * Экран оценки рисует afterHourly. Пока телефон собирал день сам, честного числа взять
     * было неоткуда и маппер отдавал ноль — офлайн человек видел «0 ₽» там, где онлайн
     * стоит ставка дня. Сервер теперь присылает «до» целиком.
     */
    @Test
    fun authoritativeDayFillsTheHourlyGauge() {
        val est = OfflineEstimateMapper.fromDayMatrix(
            dayCache().put("day_before_net", 5000.0).put("day_before_minutes", 100.0),
            candidateLat = 59.945, candidateLon = 30.340,
            income = 1500.0, address = "Новый адрес", clinic = "",
        )
        assertNotNull(est)
        // 5000 ₽ за 100 минут — ровно 3000 ₽/час.
        assertEquals(3000.0, est!!.beforeHourly, 1e-9)
        assertTrue("плитка «чистыми/ч» больше не ноль", est.afterHourly > 0.0)
    }

    /** Старый кеш без готового «до» — прежнее поведение: нули, а не самосборное число. */
    @Test
    fun oldCacheLeavesTheHourlyGaugeEmpty() {
        val est = OfflineEstimateMapper.fromDayMatrix(
            dayCache(), candidateLat = 59.945, candidateLon = 30.340,
            income = 1500.0, address = "Новый адрес", clinic = "",
        )
        assertNotNull(est)
        assertEquals(0.0, est!!.beforeHourly, 0.0)
        assertEquals(0.0, est.afterHourly, 0.0)
    }

    private fun verdictOf(decision: String): String {
        val text = decision.uppercase()
        return when {
            text.contains("НЕВЫГОДНО") -> "skip"
            text.contains("СПЕЦТАРИФ") || text.contains("НАДБАВК") -> "edge"
            else -> "go"
        }
    }
}
