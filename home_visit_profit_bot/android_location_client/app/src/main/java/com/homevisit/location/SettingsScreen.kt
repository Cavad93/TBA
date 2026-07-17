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
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
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
import androidx.compose.material.icons.filled.Info
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
import com.homevisit.location.domain.AddressCandidate
import com.homevisit.location.domain.AuthUser
import com.homevisit.location.ui.AuthFlow
import com.homevisit.location.ui.AuthViewModel
import com.homevisit.location.domain.ClinicReportRow
import com.homevisit.location.domain.SettingField
import com.homevisit.location.domain.SettingType
import com.homevisit.location.domain.SettingsSection
import com.homevisit.location.domain.EndDayDetails
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.WorkloadCorrelationCell
import com.homevisit.location.domain.WorkloadCorrelationReport
import com.homevisit.location.domain.WorkloadSnapshot
import com.homevisit.location.domain.WorkloadTrendPoint
import com.homevisit.location.domain.WorkloadTrendReport
import com.homevisit.location.domain.HomeRecommendation
import com.homevisit.location.domain.HomeOverwork
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
import com.homevisit.location.ui.WorkloadUiState
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
    appSettings: AppSettingsUiState,
    workActions: WorkActions,
    onOpenReports: () -> Unit = {},
    onOpenWorkload: () -> Unit = {},
    onOpenAppSettings: () -> Unit = {},
    onOpenZones: () -> Unit = {},
) {
    // Настройки — это меню, а не простыня полей: сами параметры живут на своих
    // страницах, а здесь только вход в них. Аккаунт — последним пунктом.
    //
    // Синхронизации здесь нет: она идёт сама (фоновая задача каждые 15 минут плюс
    // разовая при входе). Показывать её очередь, конфликты и кнопку «синхронизировать»
    // — значит грузить человека нашей внутренней кухней и намекать, что без него
    // данные не уйдут. Уйдут.
    ScreenColumn {
        SettingsMenuItem(
            "Параметры расчёта",
            "Деньги, машина, старт и финиш, компании, время и GPS",
            onOpenAppSettings,
        )
        SettingsMenuItem(
            "Зоны обслуживания",
            "Где вы работаете обычно: область, город, районы",
            onOpenZones,
        )
        SettingsMenuItem("Подробные отчёты", "День, месяц, год и разбивка по компаниям", onOpenReports)
        SettingsMenuItem("Режим труда", "Загруженность, переработка, опрос об условиях", onOpenWorkload)
        OrderSourceCard()
        AccountCard(settingsState)
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
    onSuggestAddress: (String, String) -> Unit = { _, _ -> },
) {
    val snapshot = appSettings.snapshot
    // ДЕЛЬТА-МОДЕЛЬ: карты хранят только то, что человек ТРОГАЛ; всё остальное
    // рисуется прямо из снапшота (рендер везде `edits[key] ?: field.value`).
    // Раньше карты заполнялись всеми значениями и ПЕРЕСОЗДАВАЛИСЬ на каждый новый
    // снапшот — а живой хинт extra_cost_per_km делает снапшоты неравными, и любой
    // фоновый refresh (в т.ч. запущенный входом на страницу) стирал начатый ввод:
    // «кнопка добавить не работает», «старт/финиш не сохраняются» — всё это была
    // одна гонка. Правка человека не может проигрывать асинхронному ответу сети.
    val textEdits = remember { mutableStateMapOf<String, String>() }
    val boolEdits = remember { mutableStateMapOf<String, Boolean>() }
    // Черновик шаблона «Название+Адрес» живёт на уровне экрана: раньше набранное
    // без нажатия «Добавить шаблон» молча пропадало при «Сохранить настройки».
    var templateDraftName by rememberSaveable { mutableStateOf("") }
    var templateDraftAddress by rememberSaveable { mutableStateOf("") }

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
                    AppSettingsSection(
                        section = section,
                        textEdits = textEdits,
                        boolEdits = boolEdits,
                        templateDraftName = templateDraftName,
                        templateDraftAddress = templateDraftAddress,
                        onTemplateDraftName = { templateDraftName = it },
                        onTemplateDraftAddress = { templateDraftAddress = it },
                        rejectedReasons = appSettings.rejected.associate { it.key to it.reason },
                        addressCandidates = appSettings.addressCandidates,
                        onSuggestAddress = onSuggestAddress,
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        modifier = Modifier.weight(1f),
                        enabled = !appSettings.isLoading,
                        onClick = {
                            // Недобавленный черновик шаблона — часть сохранения, а не потеря.
                            if (templateDraftAddress.isNotBlank()) {
                                val key = "address_templates"
                                val raw = textEdits[key]
                                    ?: snapshot.sections.flatMap { it.fields }
                                        .firstOrNull { it.key == key }?.textValue
                                    ?: "[]"
                                val address = templateDraftAddress.trim()
                                textEdits[key] = serializeAddressTemplates(
                                    parseAddressTemplates(raw) +
                                        AddressTemplate(templateDraftName.trim().ifBlank { address }, address),
                                )
                                templateDraftName = ""
                                templateDraftAddress = ""
                            }
                            onSave(collectSettingsChanges(snapshot.sections, textEdits, boolEdits))
                            // Дельта передана: дальше правда живёт в ответе сервера
                            // (applied → свежий снапшот, rejected → подсветка с причиной).
                            textEdits.clear()
                            boolEdits.clear()
                        },
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
    templateDraftName: String = "",
    templateDraftAddress: String = "",
    onTemplateDraftName: (String) -> Unit = {},
    onTemplateDraftAddress: (String) -> Unit = {},
    // Отвергнутое последним сохранением: ключ → причина. Ошибка показывается у
    // самого поля — «где ошибка и как исправить», а не только общим сообщением.
    rejectedReasons: Map<String, String> = emptyMap(),
    addressCandidates: Map<String, List<AddressCandidate>> = emptyMap(),
    onSuggestAddress: (String, String) -> Unit = { _, _ -> },
) {
    // Зоны обслуживания — не поле, а отдельная страница со своим объяснением.
    val fields = section.fields.filter { it.type != SettingType.Zones }
    if (fields.isEmpty()) return

    SectionHeader(section.title)
    // Шаблоны нужны Старту и Финишу как источник вариантов — берём их из текущего
    // состояния редактора, чтобы только что добавленный шаблон сразу был доступен.
    val templatesField = section.fields.firstOrNull { it.key == "address_templates" }
    val templates = templatesField?.let { parseAddressTemplates(textEdits[it.key] ?: it.textValue) }.orEmpty()

    fields.forEach { field ->
        // Причина отказа сервера у САМОГО поля: «где ошибка и как исправить»,
        // без технического ключа в начале строки.
        val rejectedReason = rejectedReasons[field.key]?.let { it.substringAfter(": ", it) }
        val errorSupport: (@Composable () -> Unit)? = rejectedReason?.let { reason -> { Text(reason) } }
        // Иные расходы на километр. Пояснение здесь — не мелкая подпись под полем, а
        // полноценная карточка: в нём стоят НАСТОЯЩИЕ цифры этого человека («сейчас
        // приложение считает столько-то на топливо и столько-то на износ»). Не понимая,
        // что уже посчитано, он либо задвоит расходы, либо не внесёт ничего.
        if (field.key == "extra_cost_per_km") {
            ExtraCostExplanation(field.hint)
            OutlinedTextField(
                modifier = Modifier.fillMaxWidth(),
                value = textEdits[field.key] ?: field.textValue,
                onValueChange = { textEdits[field.key] = it },
                label = { Text(field.label) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                isError = rejectedReason != null,
                supportingText = errorSupport,
            )
            return@forEach
        }

        // Шаблоны адресов хранятся как JSON — вместо сырого текстового поля даём
        // нормальный редактор «название + адрес».
        if (field.key == "address_templates") {
            val raw = textEdits[field.key] ?: field.textValue
            AddressTemplatesEditor(
                label = field.label,
                templates = parseAddressTemplates(raw),
                onChange = { items -> textEdits[field.key] = serializeAddressTemplates(items) },
                draftName = templateDraftName,
                draftAddress = templateDraftAddress,
                onDraftName = onTemplateDraftName,
                onDraftAddress = onTemplateDraftAddress,
            )
            SettingHint(field.hint)
            return@forEach
        }
        // Старт и финиш — не свободный текст, а выбор из своих же шаблонов: «Дом»
        // раньше был заглушкой, за которой не стояло адреса, и смена начиналась без
        // координат.
        if (field.key == "default_start_address" || field.key == "default_finish_address") {
            DefaultAddressField(
                label = field.label,
                value = textEdits[field.key] ?: field.textValue,
                touched = textEdits.containsKey(field.key),
                templates = templates,
                candidates = addressCandidates[field.key].orEmpty(),
                rejectedReason = rejectedReasons[field.key],
                onValue = { textEdits[field.key] = it },
                onSuggest = { query -> onSuggestAddress(field.key, query) },
            )
            SettingHint(field.hint)
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
            SettingType.Choice -> {
                ChoiceField(
                    field = field,
                    value = textEdits[field.key] ?: field.textValue,
                    onValue = { textEdits[field.key] = it },
                )
            }

            SettingType.Number -> {
                OutlinedTextField(
                    modifier = Modifier.fillMaxWidth(),
                    value = textEdits[field.key] ?: field.textValue,
                    onValueChange = { textEdits[field.key] = it },
                    singleLine = true,
                    label = { Text(field.label) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    isError = rejectedReason != null,
                    supportingText = errorSupport,
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
            SettingType.Date -> {
                // Дата — не свободный текст: без подсказки формата человек пишет
                // «16.07.2027», а раньше это молча топило весь батч сохранения.
                OutlinedTextField(
                    modifier = Modifier.fillMaxWidth(),
                    value = textEdits[field.key] ?: field.textValue,
                    onValueChange = { textEdits[field.key] = it },
                    singleLine = true,
                    label = { Text(field.label) },
                    placeholder = { Text("ДД.ММ.ГГГГ") },
                    isError = rejectedReason != null,
                    supportingText = errorSupport,
                )
            }
            else -> {
                OutlinedTextField(
                    modifier = Modifier.fillMaxWidth(),
                    value = textEdits[field.key] ?: field.textValue,
                    onValueChange = { textEdits[field.key] = it },
                    singleLine = true,
                    label = { Text(field.label) },
                    isError = rejectedReason != null,
                    supportingText = errorSupport,
                )
            }
        }
        SettingHint(field.hint)
    }
    if (section.key == "car") {
        FuelCostPerKmHint(textEdits = textEdits, fields = fields)
    }
}

/**
 * Старт или финиш по умолчанию: свободный ввод адреса + живые подсказки того же
 * серверного слоя, что при оценке заказа, + быстрый выбор из своих шаблонов.
 *
 * Прошлая версия была выпадающим списком ТОЛЬКО из шаблонов: на чистом аккаунте
 * шаблонов нет — и ввести адрес было физически невозможно («старт и финиш не
 * сохраняются»). Ввести руками — можно всегда; подсказки помогают попасть в
 * адрес, который геокодер точно знает.
 */
@Composable
internal fun DefaultAddressField(
    label: String,
    value: String,
    touched: Boolean,
    templates: List<AddressTemplate>,
    candidates: List<AddressCandidate>,
    rejectedReason: String?,
    onValue: (String) -> Unit,
    onSuggest: (String) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    // Подсказки — только по живому вводу человека, с паузой: сервер не дёргается
    // на каждую букву, а выбранная подсказка (текст равен label) не ищется заново.
    LaunchedEffect(value, touched) {
        if (!touched) return@LaunchedEffect
        if (value.isBlank() || candidates.any { it.label == value }) {
            onSuggest("")
            return@LaunchedEffect
        }
        kotlinx.coroutines.delay(500)
        onSuggest(value)
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        OutlinedTextField(
            modifier = Modifier.weight(1f),
            value = value,
            onValueChange = onValue,
            singleLine = true,
            label = { Text(label) },
            isError = rejectedReason != null,
            supportingText = rejectedReason?.let { reason ->
                { Text(reason.substringAfter(": ", reason)) }
            },
        )
        if (templates.isNotEmpty()) {
            Box {
                IconButton(onClick = { expanded = true }) {
                    Icon(Icons.Filled.ArrowDropDown, contentDescription = "Выбрать из шаблонов")
                }
                DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    templates.forEach { template ->
                        DropdownMenuItem(
                            text = { Text("${template.name} · ${template.address}", maxLines = 1, overflow = TextOverflow.Ellipsis) },
                            onClick = {
                                // В настройку кладём АДРЕС, а не название: координаты
                                // считаются по адресу, за которым закреплён шаблон.
                                onValue(template.address)
                                expanded = false
                            },
                        )
                    }
                    DropdownMenuItem(
                        text = { Text("Очистить") },
                        onClick = { onValue(""); expanded = false },
                    )
                }
            }
        }
    }
    // Кандидаты сервера — как при оценке адреса: тап подставляет точный вариант.
    candidates.forEach { candidate ->
        OutlinedButton(
            modifier = Modifier.fillMaxWidth(),
            onClick = { onValue(candidate.label); onSuggest("") },
        ) {
            Text(candidate.label, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
    val matchesTemplate = templates.any { it.address == value || it.name.equals(value, ignoreCase = true) }
    if (value.isNotBlank() && !matchesTemplate && !looksLikeAddress(value)) {
        Text(
            "«$value» не похоже на адрес и не совпадает ни с одним шаблоном — карта его не найдёт, " +
                "и смена начнётся без точки старта.",
            style = MaterialTheme.typography.bodySmall,
            color = VerdictColors.edge,
        )
    }
}

/**
 * Похоже ли это на адрес, который вообще можно найти на карте. «Дом» или «Офис» —
 * ярлык, а не адрес: признак настоящего — номер дома или запятая-разделитель.
 * Та же проверка есть на сервере (address_resolver.looks_like_address).
 */
internal fun looksLikeAddress(value: String): Boolean {
    val text = value.trim()
    if (text.length < 4) return false
    return text.any { it.isDigit() } || text.contains(',')
}

/** Одно предложение под полем: что это и зачем. Приходит с сервера вместе с настройкой. */
@Composable
private fun SettingHint(hint: String) {
    if (hint.isBlank()) return
    Text(
        hint,
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(bottom = 4.dp),
    )
}

/**
 * Стоимость километра пользователь не вводит — она считается из цены литра и расхода.
 * Показываем результат, чтобы было видно, во что превращаются введённые числа.
 */
@Composable
private fun FuelCostPerKmHint(textEdits: Map<String, String>, fields: List<SettingField>) {
    fun value(key: String): Double? {
        val field = fields.firstOrNull { it.key == key } ?: return null
        return parseNumber(textEdits[key] ?: field.textValue)
    }

    val price = value("fuel_price_per_liter") ?: return
    val consumption = value("fuel_consumption_l_per_100km") ?: return
    if (price <= 0 || consumption <= 0) return

    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = VerdictColors.goContainer),
    ) {
        Text(
            // Честно: это только топливная часть. Вердикт считается по полной цене
            // километра (топливо + износ), а измеренное по заправкам вытесняет модель.
            "Топливо: ${money(price * consumption / 100)} за километр. В оценке заказа " +
                "к этому добавляется износ, а при накопленных заправках и расходах " +
                "приложение считает по ним, а не по этой формуле.",
            modifier = Modifier.padding(12.dp),
            style = MaterialTheme.typography.bodySmall,
            color = VerdictColors.onGoContainer,
        )
    }
}

/** Редактор шаблонов адресов: «название + адрес», выбираются потом в Ленте. */
@Composable
internal fun AddressTemplatesEditor(
    label: String,
    templates: List<AddressTemplate>,
    onChange: (List<AddressTemplate>) -> Unit,
    // Черновик хранит родитель: «Сохранить настройки» обязан подхватить набранное
    // без «Добавить шаблон» — раньше такой черновик молча пропадал.
    draftName: String = "",
    draftAddress: String = "",
    onDraftName: (String) -> Unit = {},
    onDraftAddress: (String) -> Unit = {},
) {
    val newName = draftName
    val newAddress = draftAddress
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
            onValueChange = onDraftName,
            singleLine = true,
            label = { Text("Название (например, Дом)") },
        )
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = newAddress,
            onValueChange = onDraftAddress,
            singleLine = true,
            label = { Text("Адрес") },
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = newAddress.isNotBlank(),
            onClick = {
                val address = newAddress.trim()
                onChange(templates + AddressTemplate(newName.trim().ifBlank { address }, address))
                onDraftName("")
                onDraftAddress("")
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
                    // Запятая — разделитель хранения списка (и у сервера тоже):
                    // название с запятой молча разрезалось бы на два элемента.
                    onValueChange = { value ->
                        onItemsChange(items.toMutableList().also { it[index] = value.replace(",", "") })
                    },
                    singleLine = true,
                    supportingText = if (item.isEmpty()) {
                        { Text("Без запятых — это разделитель списка") }
                    } else {
                        null
                    },
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

/**
 * Аккаунт — в самом низу настроек: «Выйти» и «Удалить» не должны попадаться под руку
 * при обычной правке параметров.
 *
 * Адреса сервера и интервала GPS здесь больше нет. Это детали работы приложения:
 * менять их незачем, а ошибка в них молча ломает вообще всё — заказы перестают
 * оцениваться, отчёты не грузятся.
 */
@Composable
internal fun AccountCard(settingsState: GpsSettingsState) {
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
            Text(
                "Данные видны только вам.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
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



/**
 * Выбор из вариантов: тип транспорта, режим расчёта километра, кто платит за топливо.
 *
 * Список, а не текстовое поле: набирать «crossover» руками человек не должен, а ошибка
 * в таком значении молча испортила бы весь расчёт экономики.
 */
@Composable
private fun ChoiceField(field: SettingField, value: String, onValue: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val current = field.options.firstOrNull { it.value == value }?.title ?: value

    Box(Modifier.fillMaxWidth()) {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = current,
            onValueChange = {},
            readOnly = true,
            label = { Text(field.label) },
            trailingIcon = {
                IconButton(onClick = { expanded = true }) {
                    Icon(Icons.Filled.ArrowDropDown, contentDescription = "Выбрать")
                }
            },
        )
        // Прозрачная накладка: тап по всему полю открывает список, а не только по стрелке.
        Box(
            Modifier
                .matchParentSize()
                .clickable { expanded = true }
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            field.options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.title) },
                    onClick = {
                        onValue(option.value)
                        expanded = false
                    },
                )
            }
        }
    }
}


/**
 * Живое пояснение к «иным расходам на километр».
 *
 * Текст приходит с сервера и собран под конкретного человека: в нём стоят его цифры —
 * сколько приложение уже считает на топливо и на износ, и что остаётся добавить
 * («Платон» для грузовиков, платные дороги, мойка, стоянка, лизинг). Общими словами
 * здесь не обойтись: не понимая, что уже посчитано, человек либо задвоит расходы,
 * либо не внесёт ничего.
 */
@Composable
private fun ExtraCostExplanation(hint: String) {
    if (hint.isBlank()) return
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = VerdictColors.edgeContainer),
        border = BorderStroke(1.dp, VerdictColors.edge),
    ) {
        Row(
            Modifier.padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Icon(
                Icons.Filled.Info,
                contentDescription = null,
                tint = VerdictColors.edge,
                modifier = Modifier.size(18.dp),
            )
            Text(
                hint,
                style = MaterialTheme.typography.bodySmall,
                color = VerdictColors.onEdgeContainer,
            )
        }
    }
}
