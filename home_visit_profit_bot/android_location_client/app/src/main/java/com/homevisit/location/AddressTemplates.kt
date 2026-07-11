package com.homevisit.location

import com.homevisit.location.ui.AppSettingsUiState
import org.json.JSONArray
import org.json.JSONObject

/**
 * Шаблон адреса для Старта/Финиша: «название + адрес». Хранится в настройке
 * `address_templates` как JSON-массив (не список через запятую — в адресах есть
 * запятые: «ул. Ленина, 40»). Один общий список используется и для Старта, и для
 * Финиша: «Дом» не нужно заводить дважды.
 */
internal data class AddressTemplate(val name: String, val address: String)

/** Текстовое значение настройки по ключу (пусто, если настройка не пришла). */
internal fun AppSettingsUiState.settingText(key: String): String =
    snapshot?.sections
        ?.flatMap { it.fields }
        ?.firstOrNull { it.key == key }
        ?.textValue
        .orEmpty()

/** Числовая настройка по ключу; null, если не задана или ноль. */
internal fun AppSettingsUiState.settingNumber(key: String): Double? =
    settingText(key).trim().replace(',', '.').toDoubleOrNull()?.takeIf { it > 0 }

internal fun AppSettingsUiState.addressTemplates(): List<AddressTemplate> =
    parseAddressTemplates(settingText("address_templates"))

internal fun parseAddressTemplates(json: String): List<AddressTemplate> {
    if (json.isBlank()) return emptyList()
    return try {
        val array = JSONArray(json)
        buildList {
            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue
                val address = item.optString("address").trim()
                if (address.isBlank()) continue
                val name = item.optString("name").trim().ifBlank { address }
                add(AddressTemplate(name, address))
            }
        }
    } catch (_: Exception) {
        emptyList()
    }
}

internal fun serializeAddressTemplates(items: List<AddressTemplate>): String {
    val array = JSONArray()
    items.forEach { template ->
        array.put(JSONObject().put("name", template.name).put("address", template.address))
    }
    return array.toString()
}
