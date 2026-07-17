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

/**
 * Разбор зон обслуживания.
 *
 * [dropBlank] — выбрасывать ли пустые зоны. При СОХРАНЕНИИ выбрасывать надо (пустая
 * зона на сервере не нужна), а при РЕДАКТИРОВАНИИ нельзя: только что добавленная зона
 * пуста по определению. Экран заново разбирает JSON на каждой перерисовке, поэтому
 * свежедобавленная карточка исчезала на следующем кадре — кнопка «Добавить зону»
 * выглядела мёртвой, хотя честно отрабатывала.
 */
internal fun parseBaseZones(raw: String, dropBlank: Boolean = true): List<BaseZone> {
    if (raw.isBlank()) return emptyList()
    return runCatching {
        val array = JSONArray(raw)
        (0 until array.length()).mapNotNull { index ->
            val item = array.optJSONObject(index) ?: return@mapNotNull null
            val districtsJson = item.optJSONArray("districts") ?: JSONArray()
            val allDistricts = (0 until districtsJson.length())
                .map { districtsJson.optString(it).trim() }
            // При редактировании пустой район ЖИВ: человек стёр текст, чтобы вписать
            // новый, а безусловный фильтр удалял строку на следующем кадре — та же
            // болезнь, что была у пустой зоны. Отсев пустых — только при сохранении.
            val districts = if (dropBlank) allDistricts.filter { it.isNotEmpty() } else allDistricts
            val zone = BaseZone(
                region = item.optString("region").trim(),
                city = item.optString("city").trim(),
                districts = districts,
            )
            val blank = zone.city.isBlank() && zone.region.isBlank() && zone.districts.isEmpty()
            if (dropBlank && blank) null else zone
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
