package com.homevisit.location

import org.json.JSONArray
import org.json.JSONObject

/**
 * Зона обслуживания: область → город → районы.
 *
 * Зон может быть сколько угодно, и в каждой сколько угодно районов. Хранится JSON-строкой:
 * в названиях бывают запятые, список через запятую их бы поломал.
 */
data class BaseZone(
    val region: String = "",
    val city: String = "",
    val districts: List<String> = emptyList(),
)

internal fun parseBaseZones(raw: String): List<BaseZone> {
    if (raw.isBlank()) return emptyList()
    return runCatching {
        val array = JSONArray(raw)
        (0 until array.length()).mapNotNull { index ->
            val item = array.optJSONObject(index) ?: return@mapNotNull null
            val districtsJson = item.optJSONArray("districts") ?: JSONArray()
            val districts = (0 until districtsJson.length())
                .map { districtsJson.optString(it).trim() }
                .filter { it.isNotEmpty() }
            val zone = BaseZone(
                region = item.optString("region").trim(),
                city = item.optString("city").trim(),
                districts = districts,
            )
            if (zone.city.isBlank() && zone.region.isBlank() && zone.districts.isEmpty()) null else zone
        }
    }.getOrDefault(emptyList())
}

internal fun serializeBaseZones(zones: List<BaseZone>): String {
    val array = JSONArray()
    zones.forEach { zone ->
        array.put(
            JSONObject()
                .put("region", zone.region)
                .put("city", zone.city)
                .put("districts", JSONArray(zone.districts)),
        )
    }
    return array.toString()
}
