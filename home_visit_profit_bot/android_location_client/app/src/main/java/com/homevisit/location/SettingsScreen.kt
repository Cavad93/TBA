@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.homevisit.location

import android.Manifest
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material.icons.filled.Coffee
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.StarBorder
import androidx.compose.material3.Card
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedIconButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.FormatListBulleted
import androidx.compose.material.icons.automirrored.filled.TrendingUp
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Bedtime
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.NearMe
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material.icons.filled.MonitorHeart
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Today
import androidx.compose.material.icons.filled.Work
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.homevisit.location.data.HomeVisitRepository
import com.homevisit.location.domain.AuthUser
import com.homevisit.location.ui.AuthFlow
import com.homevisit.location.ui.AuthViewModel
import com.homevisit.location.domain.ClinicReportRow
import com.homevisit.location.domain.SettingField
import com.homevisit.location.domain.SettingType
import com.homevisit.location.domain.SettingsSection
import com.homevisit.location.domain.EndDayDetails
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.FatigueCorrelationCell
import com.homevisit.location.domain.FatigueCorrelationReport
import com.homevisit.location.domain.FatigueSnapshot
import com.homevisit.location.domain.FatigueTrendPoint
import com.homevisit.location.domain.FatigueTrendReport
import com.homevisit.location.domain.HomeRecommendation
import com.homevisit.location.domain.HomeRecovery
import com.homevisit.location.domain.HomeSnapshot
import com.homevisit.location.domain.HomeStartPrompt
import com.homevisit.location.domain.ProfileDriving
import com.homevisit.location.domain.ProfileWellbeing
import com.homevisit.location.domain.ReportPeriod
import com.homevisit.location.domain.ReportSnapshot
import com.homevisit.location.domain.ReportSummary
import com.homevisit.location.domain.ShiftBar
import com.homevisit.location.domain.ShiftOrder
import com.homevisit.location.domain.ShiftToday
import com.homevisit.location.domain.StopLabel
import com.homevisit.location.domain.WellbeingGauge
import com.homevisit.location.domain.WorkDayStatus
import com.homevisit.location.sync.SyncScheduler
import com.homevisit.location.ui.AppSettingsUiState
import com.homevisit.location.ui.CandidateUiState
import com.homevisit.location.ui.FatigueUiState
import com.homevisit.location.ui.GpsEstimateUiState
import com.homevisit.location.ui.GpsHintUiState
import com.homevisit.location.ui.HomeUiState
import com.homevisit.location.ui.HomeVisitUiState
import com.homevisit.location.ui.HomeVisitViewModel
import com.homevisit.location.ui.ReportUiState
import com.homevisit.location.ui.RouteUiState
import com.homevisit.location.ui.ProfileUiState
import com.homevisit.location.ui.RouteVisitUi
import com.homevisit.location.ui.ShiftUiState
import com.homevisit.location.ui.SyncUiState
import java.util.Locale
import kotlinx.coroutines.launch

@Composable
internal fun SettingsScreen(
    settingsState: GpsSettingsState,
    syncState: SyncUiState,
    appSettings: AppSettingsUiState,
    workActions: WorkActions,
    onSync: () -> Unit,
    onOpenReports: () -> Unit = {},
    onOpenFatigue: () -> Unit = {},
) {
    ScreenColumn {
        SettingsMenuItem("Подробные отчёты", "День, месяц, год и разбивка по клиникам", onOpenReports)
        SettingsMenuItem("Нагрузка и восстановление", "Тренды, самочувствие, калибровка", onOpenFatigue)
        GpsSettingsCard(settingsState)
        OrderSourceCard()
        AppSettingsCard(
            appSettings = appSettings,
            onRefresh = workActions.onRefreshAppSettings,
            onSave = workActions.onSaveAppSettings,
        )
        SyncControlCard(
            syncState = syncState,
            onSync = onSync,
            onExportBackup = workActions.onExportBackup,
            onRefreshConflicts = workActions.onRefreshSyncConflicts,
            onCheckConnection = workActions.onCheckConnection,
            onClearCache = workActions.onClearCache,
            onImportBackup = workActions.onImportBackup,
            showImport = true,
        )
        CompactCard(
            title = "Что здесь важно",
            body = "Вход выполняется по вашему аккаунту — данные видны только вам. Адрес сервера подставлен автоматически и нужен для расчёта маршрутов, отчётов, нагрузки и синхронизации. Настройки экономики, авто, компаний и районов редактируются здесь и уходят на сервер.",
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun SettingsMenuItem(title: String, subtitle: String, onClick: () -> Unit) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        onClick = onClick,
    ) {
        Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
internal fun OrderSourceCard() {
    InputCard("Название источника заказов") {
        Text(
            "Как называть тех, от кого приходят заказы, под вашу сферу. Подписи в отчётах и формах подстроятся под выбранное слово.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OptionGrid(
            options = OrderSource.presets,
            selected = OrderSource.current,
            label = { it.nomSingle },
            onSelect = { OrderSource.current = it },
        )
    }
}

@Composable
internal fun AppSettingsCard(
    appSettings: AppSettingsUiState,
    onRefresh: () -> Unit,
    onSave: (Map<String, Any?>) -> Unit,
) {
    val snapshot = appSettings.snapshot
    // Локальное редактируемое состояние, пересобирается при новой загрузке с сервера.
    val textEdits = remember(snapshot) { mutableStateMapOf<String, String>() }
    val boolEdits = remember(snapshot) { mutableStateMapOf<String, Boolean>() }
    LaunchedEffect(snapshot) {
        if (snapshot != null) {
            textEdits.clear()
            boolEdits.clear()
            snapshot.sections.forEach { section ->
                section.fields.forEach { field ->
                    when (field.type) {
                        SettingType.Bool -> boolEdits[field.key] = field.boolValue
                        SettingType.ListValue -> textEdits[field.key] = field.listValue.joinToString(", ")
                        else -> textEdits[field.key] = field.textValue
                    }
                }
            }
        }
    }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Настройки приложения", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Экономика, авто, компании, базовые районы, маршрутизация, GPS и нагрузка. Значения хранятся на сервере и применяются к расчётам.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (appSettings.message.isNotBlank()) {
                Text(appSettings.message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            if (snapshot == null) {
                Button(modifier = Modifier.fillMaxWidth(), enabled = !appSettings.isLoading, onClick = onRefresh) {
                    Text(if (appSettings.isLoading) "Загружаю..." else "Загрузить настройки")
                }
            } else {
                snapshot.sections.forEach { section ->
                    AppSettingsSection(section = section, textEdits = textEdits, boolEdits = boolEdits)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        modifier = Modifier.weight(1f),
                        enabled = !appSettings.isLoading,
                        onClick = { onSave(collectSettingsChanges(snapshot.sections, textEdits, boolEdits)) },
                    ) {
                        Text(if (appSettings.isLoading) "Сохраняю..." else "Сохранить настройки")
                    }
                    OutlinedButton(modifier = Modifier.width(132.dp), enabled = !appSettings.isLoading, onClick = onRefresh) {
                        Text("Обновить")
                    }
                }
            }
        }
    }
}

@Composable
internal fun AppSettingsSection(
    section: SettingsSection,
    textEdits: MutableMap<String, String>,
    boolEdits: MutableMap<String, Boolean>,
) {
    SectionHeader(section.title)
    section.fields.forEach { field ->
        // Шаблоны адресов хранятся как JSON — вместо сырого текстового поля даём
        // нормальный редактор «название + адрес».
        if (field.key == "address_templates") {
            val raw = textEdits[field.key] ?: field.textValue
            AddressTemplatesEditor(
                label = field.label,
                templates = parseAddressTemplates(raw),
                onChange = { items -> textEdits[field.key] = serializeAddressTemplates(items) },
            )
            return@forEach
        }
        when (field.type) {
            SettingType.Bool -> {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(field.label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
                    Switch(
                        checked = boolEdits[field.key] ?: field.boolValue,
                        onCheckedChange = { boolEdits[field.key] = it },
                    )
                }
            }
            SettingType.Number -> {
                OutlinedTextField(
                    modifier = Modifier.fillMaxWidth(),
                    value = textEdits[field.key] ?: field.textValue,
                    onValueChange = { textEdits[field.key] = it },
                    singleLine = true,
                    label = { Text(field.label) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                )
            }
            SettingType.ListValue -> {
                val raw = textEdits[field.key] ?: field.listValue.joinToString(", ")
                val items = if (raw.isBlank()) emptyList() else raw.split(",").map { it.trim() }
                ListFieldEditor(
                    label = field.label,
                    items = items,
                    onItemsChange = { newItems -> textEdits[field.key] = newItems.joinToString(", ") },
                )
            }
            else -> {
                OutlinedTextField(
                    modifier = Modifier.fillMaxWidth(),
                    value = textEdits[field.key] ?: field.textValue,
                    onValueChange = { textEdits[field.key] = it },
                    singleLine = true,
                    label = { Text(field.label) },
                )
            }
        }
    }
}

/** Редактор шаблонов адресов: «название + адрес», выбираются потом в Ленте. */
@Composable
internal fun AddressTemplatesEditor(
    label: String,
    templates: List<AddressTemplate>,
    onChange: (List<AddressTemplate>) -> Unit,
) {
    var newName by rememberSaveable { mutableStateOf("") }
    var newAddress by rememberSaveable { mutableStateOf("") }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, style = MaterialTheme.typography.bodyLarge)
        Text(
            "Чтобы не печатать адреса каждый день: шаблон можно выбрать при смене Старта или Финиша в Ленте.",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        templates.forEachIndexed { index, template ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Column(Modifier.weight(1f)) {
                    Text(template.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(template.address, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                IconButton(onClick = { onChange(templates.filterIndexed { position, _ -> position != index }) }) {
                    Icon(Icons.Filled.Delete, contentDescription = "Удалить шаблон")
                }
            }
        }
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = newName,
            onValueChange = { newName = it },
            singleLine = true,
            label = { Text("Название (например, Дом)") },
        )
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = newAddress,
            onValueChange = { newAddress = it },
            singleLine = true,
            label = { Text("Адрес") },
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = newAddress.isNotBlank(),
            onClick = {
                val address = newAddress.trim()
                onChange(templates + AddressTemplate(newName.trim().ifBlank { address }, address))
                newName = ""
                newAddress = ""
            },
        ) {
            Text("Добавить шаблон")
        }
    }
}

@Composable
internal fun ListFieldEditor(
    label: String,
    items: List<String>,
    onItemsChange: (List<String>) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
        if (items.isEmpty()) {
            Text(
                "Список пуст. Нажмите «Добавить».",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        items.forEachIndexed { index, item ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    modifier = Modifier.weight(1f),
                    value = item,
                    onValueChange = { value -> onItemsChange(items.toMutableList().also { it[index] = value }) },
                    singleLine = true,
                )
                IconButton(onClick = { onItemsChange(items.toMutableList().also { it.removeAt(index) }) }) {
                    Icon(Icons.Filled.Delete, contentDescription = "Удалить")
                }
            }
        }
        OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = { onItemsChange(items + "") }) {
            Icon(Icons.Filled.Add, contentDescription = null)
            Spacer(Modifier.width(6.dp))
            Text("Добавить")
        }
    }
}

/** Собрать только изменённые поля в payload для `/api/settings`. */
@Composable
internal fun GpsControlCard(settingsState: GpsSettingsState) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("GPS и агрегаты вождения", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(
                        if (settingsState.gpsRunning) "Отправка включена" else "Отправка выключена",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Box(
                    modifier = Modifier
                        .size(12.dp)
                        .clip(CircleShape)
                        .background(if (settingsState.gpsRunning) Color(0xFF2E7D32) else Color(0xFF9E9E9E)),
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    modifier = Modifier.weight(1f),
                    onClick = settingsState.onStartGps,
                    enabled = !settingsState.gpsRunning,
                ) {
                    Text("Запустить")
                }
                OutlinedButton(
                    modifier = Modifier.weight(1f),
                    onClick = settingsState.onStopGps,
                    enabled = settingsState.gpsRunning,
                ) {
                    Text("Остановить")
                }
            }
        }
    }
}

@Composable
internal fun SyncControlCard(
    syncState: SyncUiState,
    onSync: () -> Unit,
    onExportBackup: () -> Unit,
    onRefreshConflicts: () -> Unit,
    onCheckConnection: () -> Unit,
    onClearCache: () -> Unit,
    onImportBackup: (String) -> Unit,
    showImport: Boolean = false,
) {
    var importJson by rememberSaveable { mutableStateOf("") }
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Синхронизация", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Отправляет локальные записи из очереди на backend `/api/sync`.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            ReportMetricGrid(
                metrics = listOf(
                    "Ожидают" to syncState.stats.pendingCount.toString(),
                    "Ошибки" to syncState.stats.failedCount.toString(),
                    "Отправлено" to syncState.stats.sentCount.toString(),
                    "Всего" to syncState.stats.totalCount.toString(),
                ),
            )
            if (syncState.message.isNotBlank()) {
                Text(
                    syncState.message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(modifier = Modifier.weight(1f), onClick = onSync) {
                    Text("Синхронизировать")
                }
                OutlinedButton(modifier = Modifier.weight(1f), onClick = onExportBackup) {
                    Text("Экспорт JSON")
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(modifier = Modifier.weight(1f), onClick = onCheckConnection) {
                    Text("Проверить связь")
                }
                OutlinedButton(modifier = Modifier.weight(1f), onClick = onRefreshConflicts) {
                    Text("Журнал конфликтов")
                }
            }
            OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = onClearCache) {
                Text("Очистить кэш адресов")
            }
            Text(
                "Удаляет офлайн-копии маршрута, отчётов и нагрузки. Свежие данные подтянутся при следующем обновлении со связью.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            syncState.conflicts.take(3).forEach { conflict ->
                CompactCard(
                    title = conflict.conflictType,
                    body = "${conflict.entityType}/${conflict.clientEntityId}: ${conflict.details.orEmpty()}",
                )
            }
            if (showImport) {
                OutlinedTextField(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp),
                    value = importJson,
                    onValueChange = { importJson = it },
                    label = { Text("JSON резервной копии") },
                    singleLine = false,
                )
                Button(
                    modifier = Modifier.fillMaxWidth(),
                    enabled = importJson.isNotBlank(),
                    onClick = {
                        onImportBackup(importJson)
                        importJson = ""
                    },
                ) {
                    Text("Импортировать backup")
                }
            }
        }
    }
}

@Composable
internal fun GpsSettingsCard(settingsState: GpsSettingsState) {
    var showDeleteConfirm by remember { mutableStateOf(false) }
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Аккаунт", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            if (settingsState.accountNickname.isNotBlank()) {
                Text(settingsState.accountNickname, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
            }
            if (settingsState.accountEmail.isNotBlank()) {
                Text(
                    settingsState.accountEmail,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(modifier = Modifier.weight(1f), onClick = settingsState.onLogout) {
                    Text("Выйти")
                }
                OutlinedButton(
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                    onClick = { showDeleteConfirm = true },
                ) {
                    Text("Удалить аккаунт")
                }
            }

            Text("Подключение к серверу", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = settingsState.serverUrl,
                onValueChange = settingsState.onServerUrlChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("URL сервера") },
                placeholder = { Text(MainActivity.DEFAULT_SERVER_URL) },
            )
            OutlinedTextField(
                value = settingsState.intervalSeconds,
                onValueChange = settingsState.onIntervalChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("Интервал GPS, сек") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(modifier = Modifier.weight(1f), onClick = settingsState.onSave) {
                    Text("Сохранить")
                }
                OutlinedButton(modifier = Modifier.width(132.dp), onClick = settingsState.onStartGps) {
                    Text("GPS")
                }
            }
        }
    }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text("Удалить аккаунт?") },
            text = { Text("Аккаунт и все связанные данные будут удалены безвозвратно. Это действие нельзя отменить.") },
            confirmButton = {
                TextButton(onClick = {
                    showDeleteConfirm = false
                    settingsState.onDeleteAccount()
                }) {
                    Text("Удалить", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) { Text("Отмена") }
            },
        )
    }
}

