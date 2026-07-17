package com.homevisit.location.calc

import com.homevisit.location.domain.CandidateEstimate
import org.json.JSONObject

/**
 * Сборка офлайн-вердикта кандидата из кеша /api/route/matrix/day (Фаза 3.4/3.5).
 *
 * Чистая функция: кеш дня (точки с координатами + матрица OSRM + коэффициенты +
 * доходы принятых заказов) + координаты нового адреса → CandidateEstimate. Логику
 * достройки плеч по прямой и расчёта вердикта делает уже сверенный с сервером
 * OfflineCandidateEstimator/ProfitabilityCalculator — здесь только парсинг кеша и
 * маппинг результата в модель экрана. Тестируется JVM-тестом без эмулятора.
 *
 * Числа маржи (marginalHourly/perKm, extraCarCost) паритетны серверу — их и сверяет
 * лог расхождений Ф3.6 при возврате сети. Поля, которых у офлайн-ядра нет
 * (before/after hourly, надбавки), оставляем нулями: это мгновенная оценка, сервер
 * уточнит при связи.
 */
object OfflineEstimateMapper {

    fun fromDayMatrix(
        cache: JSONObject,
        candidateLat: Double,
        candidateLon: Double,
        income: Double,
        address: String,
        clinic: String,
        responseCost: Double = 0.0,
    ): CandidateEstimate? {
        val points = parsePoints(cache.optJSONArray("points")) ?: return null
        val distances = parseMatrix(cache.optJSONArray("distances_km")) ?: return null
        val durations = parseMatrix(cache.optJSONArray("durations_minutes")) ?: return null
        if (points.size < 2 || distances.size != points.size || durations.size != points.size) return null
        val incomes = parseDoubles(cache.optJSONArray("incomes"))
        // Цены откликов (платные лиды) приходят тем же порядком, что доходы. Сервер
        // вычитает их из чистого дня, а офлайн-оценка раньше не знала о них вовсе — и
        // на днях с платными лидами телефон был оптимистичнее сервера. Вычитаем здесь,
        // чтобы «до» считалось из тех же денег. Старый кеш без поля даёт пустой список
        // — тогда всё как раньше.
        val responseCosts = parseDoubles(cache.optJSONArray("response_costs"))
        val netIncomes = incomes.mapIndexed { index, value ->
            value - responseCosts.getOrElse(index) { 0.0 }
        }
        // Лиды отменённых заказов дня: сервер вычитает их из «до»/«после»
        // (calculate_candidate_impact), офлайн без них завышал бы ₽/час на потери
        // смены. Старый кеш без поля даёт 0.0 — как раньше.
        val cancelledLeadCosts = cache.optDouble("cancelled_lead_costs", 0.0)
        val c = cache.optJSONObject("coefficients") ?: JSONObject()

        val coeff = OfflineCandidateEstimator.Coefficients(
            straightLineFactor = c.optDouble("straight_line_factor", 1.35),
            avgSpeedKmh = c.optDouble("avg_speed_kmh", 30.0),
            serviceMinutes = c.optDouble("service_minutes", 20.0),
            fuelPerKm = c.optDouble("fuel_per_km", 0.0),
            maintenancePerKm = c.optDouble("maintenance_per_km", 0.0),
            minHourly = c.optDouble("min_hourly_income", 600.0),
            minMarginalHourly = c.optDouble("min_marginal_hourly_income", 600.0),
            outsideMinHourly = c.optDouble("outside_zone_min_hourly_income", 600.0),
            outsideMinExtra = c.optDouble("outside_zone_min_extra_payment", 0.0),
            autoOptimize = c.optBoolean("auto_optimize", true),
        )

        val result = OfflineCandidateEstimator.estimate(
            cachedPoints = points,
            cachedDistances = distances,
            cachedDurations = durations,
            candidate = OfflineCandidateEstimator.LatLon(candidateLat, candidateLon),
            candidateIncome = income,
            existingIncomes = netIncomes,
            coeff = coeff,
            // Цена отклика кандидата: сервер вычитает её из маржи — офлайн обязан
            // тоже, иначе платный лид офлайн выглядит выгоднее, чем он есть.
            candidateResponseCost = responseCost,
            cancelledLeadCosts = cancelledLeadCosts,
        )

        val costPerKm = coeff.fuelPerKm + coeff.maintenancePerKm
        val extraKm = if (costPerKm > 0) result.extraCarCost / costPerKm else 0.0
        val extraDrive = (result.extraTotalMinutes - coeff.serviceMinutes).coerceAtLeast(0.0)

        return CandidateEstimate(
            visitId = 0,   // офлайн-превью ещё не заказ на сервере
            address = address,
            income = income,
            clinic = clinic,
            decision = result.decision,
            reason = "Оценка офлайн по кешу — сервер уточнит при связи",
            score = result.score,
            requiredExtraPayment = 0.0,
            requiredCandidateIncome = 0.0,
            beforeHourly = 0.0,
            afterHourly = 0.0,
            marginalHourly = result.marginalHourly,
            marginalPerKm = result.marginalPerKm,
            costPerKm = costPerKm,
            extraKm = extraKm,
            extraDriveMinutes = extraDrive,
            workloadLevel = "",
            baseMinHourly = coeff.minHourly,
            effectiveMinHourly = coeff.minHourly,
            overworkMarkupPercent = 0,
            overworkBlocksOutsideZone = false,
        )
    }

    private fun parsePoints(array: org.json.JSONArray?): List<OfflineCandidateEstimator.LatLon>? {
        if (array == null) return null
        val out = ArrayList<OfflineCandidateEstimator.LatLon>(array.length())
        for (i in 0 until array.length()) {
            val o = array.optJSONObject(i) ?: return null
            out.add(OfflineCandidateEstimator.LatLon(o.optDouble("lat"), o.optDouble("lon")))
        }
        return out
    }

    private fun parseMatrix(array: org.json.JSONArray?): List<List<Double>>? {
        if (array == null) return null
        val rows = ArrayList<List<Double>>(array.length())
        for (i in 0 until array.length()) {
            val rowArray = array.optJSONArray(i) ?: return null
            val row = ArrayList<Double>(rowArray.length())
            for (j in 0 until rowArray.length()) row.add(rowArray.optDouble(j, 0.0))
            rows.add(row)
        }
        return rows
    }

    private fun parseDoubles(array: org.json.JSONArray?): List<Double> {
        if (array == null) return emptyList()
        val out = ArrayList<Double>(array.length())
        for (i in 0 until array.length()) out.add(array.optDouble(i, 0.0))
        return out
    }
}
