package com.homevisit.location

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.homevisit.location.domain.SettingType
import com.homevisit.location.ui.AppSettingsUiState

/**
 * Страница «Параметры расчёта»: то же, что раньше было простынёй внутри настроек,
 * но отдельным экраном и с пояснением к каждому параметру.
 */
@Composable
internal fun AppSettingsPage(appSettings: AppSettingsUiState, workActions: WorkActions) {
    ScreenColumn {
        AppSettingsCard(
            appSettings = appSettings,
            onRefresh = workActions.onRefreshAppSettings,
            onSave = workActions.onSaveAppSettings,
        )
    }
}

/**
 * Страница «Зоны обслуживания».
 *
 * Сначала объясняем, зачем это вообще нужно, потом даём завести зоны: область → город →
 * районы. Городов и районов может быть сколько угодно; если районы не указаны, базовым
 * считается весь город.
 */
@Composable
internal fun BaseZonesPage(appSettings: AppSettingsUiState, workActions: WorkActions) {
    val snapshot = appSettings.snapshot
    val field = snapshot?.sections
        ?.flatMap { it.fields }
        ?.firstOrNull { it.type == SettingType.Zones }

    // Держим зоны JSON-строкой: так состояние переживает поворот экрана без своего Saver.
    var zonesJson by rememberSaveable(field?.textValue) { mutableStateOf(field?.textValue ?: "[]") }
    val zones = parseBaseZones(zonesJson)

    ScreenColumn {
        ZonesIntroCard()

        if (snapshot == null) {
            Button(
                modifier = Modifier.fillMaxWidth(),
                enabled = !appSettings.isLoading,
                onClick = workActions.onRefreshAppSettings,
            ) {
                Text(if (appSettings.isLoading) "Загружаю…" else "Загрузить настройки")
            }
            return@ScreenColumn
        }

        zones.forEachIndexed { index, zone ->
            ZoneCard(
                zone = zone,
                onChange = { updated ->
                    zonesJson = serializeBaseZones(zones.toMutableList().also { it[index] = updated })
                },
                onRemove = {
                    zonesJson = serializeBaseZones(zones.toMutableList().also { it.removeAt(index) })
                },
            )
        }

        OutlinedButton(
            modifier = Modifier.fillMaxWidth(),
            onClick = { zonesJson = serializeBaseZones(zones + BaseZone()) },
        ) {
            Text("Добавить зону")
        }

        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = !appSettings.isLoading,
            onClick = {
                val cleaned = zones.filter { it.city.isNotBlank() || it.region.isNotBlank() || it.districts.isNotEmpty() }
                workActions.onSaveAppSettings(mapOf("base_zones" to serializeBaseZones(cleaned)))
            },
        ) {
            Text(if (appSettings.isLoading) "Сохраняю…" else "Сохранить зоны")
        }

        if (appSettings.message.isNotBlank()) {
            Text(
                appSettings.message,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ZonesIntroCard() {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Где вы работаете обычно", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Зона обслуживания — территория, которую вы считаете «своей». Заказы внутри неё " +
                    "оцениваются по обычной планке ₽/час. Заказ за её пределами — это лишняя дорога, " +
                    "поэтому он должен приносить больше: приложение спросит с него повышенную планку " +
                    "и надбавку, которые вы задали в параметрах расчёта.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Указывайте так подробно, как удобно: область → город → районы. Районов можно не " +
                    "указывать вовсе — тогда своим считается весь город. Зон может быть несколько.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ZoneCard(zone: BaseZone, onChange: (BaseZone) -> Unit, onRemove: () -> Unit) {
    var newDistrict by rememberSaveable { mutableStateOf("") }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    zone.city.ifBlank { "Новая зона" },
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = onRemove) {
                    Icon(Icons.Filled.Delete, contentDescription = "Удалить зону", tint = MaterialTheme.colorScheme.error)
                }
            }
            OutlinedTextField(
                modifier = Modifier.fillMaxWidth(),
                value = zone.region,
                onValueChange = { onChange(zone.copy(region = it)) },
                singleLine = true,
                label = { Text("Область, край или республика") },
            )
            OutlinedTextField(
                modifier = Modifier.fillMaxWidth(),
                value = zone.city,
                onValueChange = { onChange(zone.copy(city = it)) },
                singleLine = true,
                label = { Text("Город") },
            )

            Text(
                "Районы города · необязательно",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            zone.districts.forEachIndexed { index, district ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    OutlinedTextField(
                        modifier = Modifier.weight(1f),
                        value = district,
                        onValueChange = { value ->
                            onChange(zone.copy(districts = zone.districts.toMutableList().also { it[index] = value }))
                        },
                        singleLine = true,
                        label = { Text("Район") },
                    )
                    IconButton(onClick = {
                        onChange(zone.copy(districts = zone.districts.toMutableList().also { it.removeAt(index) }))
                    }) {
                        Icon(Icons.Filled.Delete, contentDescription = "Удалить район")
                    }
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                OutlinedTextField(
                    modifier = Modifier.weight(1f),
                    value = newDistrict,
                    onValueChange = { newDistrict = it },
                    singleLine = true,
                    label = { Text("Добавить район") },
                )
                OutlinedButton(
                    enabled = newDistrict.isNotBlank(),
                    onClick = {
                        onChange(zone.copy(districts = zone.districts + newDistrict.trim()))
                        newDistrict = ""
                    },
                ) {
                    Text("+")
                }
            }
        }
    }
}
