@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.homevisit.location

import android.Manifest
import android.speech.SpeechRecognizer
import com.homevisit.location.voice.ServerVoiceRecorder
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.runtime.DisposableEffect
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
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.material.icons.filled.ArrowDropDown
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
import androidx.compose.material3.FilterChip
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
import com.homevisit.location.domain.AddressCandidate
import com.homevisit.location.domain.CandidateEstimate
import com.homevisit.location.domain.ClinicReportRow
import com.homevisit.location.domain.SettingField
import com.homevisit.location.domain.SettingType
import com.homevisit.location.domain.SettingsSection
import com.homevisit.location.domain.EndDayDetails
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
import com.homevisit.location.ui.PersonalTripUi
import com.homevisit.location.ui.ProfileUiState
import com.homevisit.location.ui.RouteVisitUi
import com.homevisit.location.ui.ShiftUiState
import com.homevisit.location.ui.SyncUiState
import java.util.Locale
import kotlinx.coroutines.launch
import com.homevisit.location.domain.ParkingHint

@Composable
internal fun DayDetailsCard(uiState: HomeVisitUiState, workActions: WorkActions) {
    if (uiState.status == WorkDayStatus.Active) {
        var endOdometerText by rememberSaveable { mutableStateOf("") }
        val endOdometer = parseNumber(endOdometerText)
        // Мусор в поле ≠ пустое поле: пустое — осознанное «без одометра», а опечатку
        // молча превращать в «без одометра» нельзя — человек уверен, что ввёл число.
        val endOdometerInvalid = endOdometerText.isNotBlank() && endOdometer == null
        InputCard("Параметры дня") {
            Text(
                "Старт: ${uiState.startAddress.ifBlank { "не указан" }}. Финиш: ${uiState.finishAddress.ifBlank { "не указан" }}.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Перерыв между сменами: ${oneDecimal(uiState.breakHoursBefore)} ч. Одометр старт: ${oneDecimal(uiState.startOdometer)} км.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            MoneyField(value = endOdometerText, onValueChange = { endOdometerText = it }, label = "Одометр на конец")
            if (endOdometerInvalid) {
                Text(
                    "Одометр не распознан — введите число или очистите поле.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            OutlinedButton(
                modifier = Modifier.fillMaxWidth(),
                enabled = !endOdometerInvalid,
                onClick = { workActions.onEndDayWithOdometer(endOdometer) },
            ) {
                Text("Завершить день с одометром")
            }
        }
        EndDayDetailsCard(uiState = uiState, workActions = workActions)
        return
    }

    // Дефолты — из настроек (default_start/finish_address); литерал «Дом» — лишь
    // последний фолбэк, и он срабатывает только у тех, кто завёл одноимённый шаблон.
    // Ключ rememberSaveable — сам дефолт: настройки догрузились → поле обновилось.
    val defaultStart = uiState.appSettings.settingText("default_start_address").ifBlank { "Дом" }
    val defaultFinish = uiState.appSettings.settingText("default_finish_address").ifBlank { "Дом" }
    var startAddress by rememberSaveable(defaultStart) { mutableStateOf(defaultStart) }
    var finishAddress by rememberSaveable(defaultFinish) { mutableStateOf(defaultFinish) }
    var startOdometerText by rememberSaveable { mutableStateOf("") }
    val startOdometer = parseNumber(startOdometerText) ?: 0.0
    // Опечатка в одометре молча стартовала смену с нулём — весь дневной пробег
    // потом считался неверно. Нераспознанный непустой ввод блокирует старт.
    val startOdometerInvalid = startOdometerText.isNotBlank() &&
        parseNumber(startOdometerText) == null

    InputCard("Начало дня") {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = startAddress,
            onValueChange = { startAddress = it },
            label = { Text("Старт") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = finishAddress,
            onValueChange = { finishAddress = it },
            label = { Text("Финиш") },
            singleLine = true,
        )
        // Ни сна, ни перерыва здесь не спрашиваем. Сон — физиологический показатель
        // (спецкатегория ПДн). Перерыв между сменами сервер вычисляет сам: он равен
        // промежутку между закрытием прошлой смены и стартом текущей.
        MoneyField(
            modifier = Modifier.fillMaxWidth(),
            value = startOdometerText,
            onValueChange = { startOdometerText = it },
            label = "Одометр",
        )
        if (startOdometerInvalid) {
            Text(
                "Одометр не распознан — введите число или очистите поле.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error,
            )
        }
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = startAddress.isNotBlank() && finishAddress.isNotBlank() && !startOdometerInvalid,
            onClick = {
                workActions.onStartDayDetails(startAddress, finishAddress, startOdometer)
            },
        ) {
            Text("Начать день с параметрами")
        }
    }
}

@Composable
internal fun EndDayDetailsCard(uiState: HomeVisitUiState, workActions: WorkActions) {
    var actualKmText by rememberSaveable { mutableStateOf("") }
    var workHoursText by rememberSaveable { mutableStateOf("") }
    var routeHoursText by rememberSaveable { mutableStateOf("") }
    var completedVisitsText by rememberSaveable { mutableStateOf(uiState.visitsCount.toString()) }
    var endOdometerText by rememberSaveable { mutableStateOf("") }
    var fuelExpensesText by rememberSaveable { mutableStateOf("") }
    var fuelLitersText by rememberSaveable { mutableStateOf("") }
    var fuelConsumptionText by rememberSaveable { mutableStateOf("") }
    var fuelCompensationText by rememberSaveable { mutableStateOf("") }
    var parkingCompensationText by rememberSaveable { mutableStateOf("") }
    var tollExpensesText by rememberSaveable { mutableStateOf("") }
    var tollCompensationText by rememberSaveable { mutableStateOf("") }
    var otherExpensesText by rememberSaveable { mutableStateOf("") }
    var workloadRatingText by rememberSaveable { mutableStateOf("") }

    val actualKm = parseNumber(actualKmText)
    val workHours = parseNumber(workHoursText)
    val routeHours = parseNumber(routeHoursText)
    val completedVisits = parseNumber(completedVisitsText)?.toInt()
    val endOdometer = parseNumber(endOdometerText)
    val userWorkload = parseNumber(workloadRatingText)?.coerceIn(0.0, 100.0)

    // Опечатка в любом поле — не «поля не было»: раньше необязательные поля с
    // мусором молча уходили нулями (та же потеря денег, что в мастере), а
    // загруженность 150 молча срезалась в 100. Отказ всегда виден.
    val unreadableFields = listOf(
        "Рабочие км" to actualKmText,
        "Заказов" to completedVisitsText,
        "Работа" to workHoursText,
        "Дорога" to routeHoursText,
        "Одометр" to endOdometerText,
        "Расход л/100" to fuelConsumptionText,
        "Заправка" to fuelExpensesText,
        "Литры" to fuelLitersText,
        "Комп. топлива" to fuelCompensationText,
        "Комп. парковки" to parkingCompensationText,
        "Платная дорога" to tollExpensesText,
        "Комп. дороги" to tollCompensationText,
        "Прочее" to otherExpensesText,
    ).filter { (_, text) -> text.isNotBlank() && parseNumber(text) == null }
        .map { (label, _) -> label } +
        listOfNotNull(
            "Загруженность 0-100".takeIf {
                workloadRatingText.isNotBlank() &&
                    (parseNumber(workloadRatingText) ?: 101.0) > 100.0
            },
        )

    InputCard("Полное завершение дня") {
        Text(
            "Для чистого дохода/час, топлива, личного коэффициента дороги и нагрузки.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        GpsEstimateControls(
            state = uiState.gpsEstimate,
            onRefresh = workActions.onRefreshGpsEstimate,
            onApply = {
                val estimate = uiState.gpsEstimate.estimate
                if (estimate != null) {
                    if (estimate.totalWorkMinutes > 0) {
                        workHoursText = hoursInput(estimate.totalWorkMinutes)
                    }
                    if (estimate.routeMinutes > 0) {
                        routeHoursText = hoursInput(estimate.routeMinutes)
                    }
                    if (estimate.detectedVisitsCount > 0) {
                        completedVisitsText = estimate.detectedVisitsCount.toString()
                    }
                }
            },
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(modifier = Modifier.weight(1f), value = actualKmText, onValueChange = { actualKmText = it }, label = "Рабочие км")
            MoneyField(modifier = Modifier.weight(1f), value = completedVisitsText, onValueChange = { completedVisitsText = it }, label = "Заказов")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(modifier = Modifier.weight(1f), value = workHoursText, onValueChange = { workHoursText = it }, label = "Работа, ч")
            MoneyField(modifier = Modifier.weight(1f), value = routeHoursText, onValueChange = { routeHoursText = it }, label = "Дорога, ч")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(modifier = Modifier.weight(1f), value = endOdometerText, onValueChange = { endOdometerText = it }, label = "Одометр конец")
            MoneyField(modifier = Modifier.weight(1f), value = fuelConsumptionText, onValueChange = { fuelConsumptionText = it }, label = "Расход л/100")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(modifier = Modifier.weight(1f), value = fuelExpensesText, onValueChange = { fuelExpensesText = it }, label = "Заправка ₽")
            MoneyField(modifier = Modifier.weight(1f), value = fuelLitersText, onValueChange = { fuelLitersText = it }, label = "Литры")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(modifier = Modifier.weight(1f), value = fuelCompensationText, onValueChange = { fuelCompensationText = it }, label = "Комп. топлива")
            MoneyField(modifier = Modifier.weight(1f), value = parkingCompensationText, onValueChange = { parkingCompensationText = it }, label = "Комп. парковки")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(modifier = Modifier.weight(1f), value = tollExpensesText, onValueChange = { tollExpensesText = it }, label = "Платная дорога")
            MoneyField(modifier = Modifier.weight(1f), value = tollCompensationText, onValueChange = { tollCompensationText = it }, label = "Комп. дороги")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(modifier = Modifier.weight(1f), value = otherExpensesText, onValueChange = { otherExpensesText = it }, label = "Прочее")
            MoneyField(modifier = Modifier.weight(1f), value = workloadRatingText, onValueChange = { workloadRatingText = it }, label = "Загруженность 0-100")
        }
        if (unreadableFields.isNotEmpty()) {
            Text(
                "Не распознано: ${unreadableFields.joinToString(", ")}. " +
                    "Поправьте число или очистите поле.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error,
            )
        }
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = actualKm != null && workHours != null && routeHours != null &&
                completedVisits != null && endOdometer != null && unreadableFields.isEmpty(),
            onClick = {
                workActions.onEndDayWithDetails(
                    EndDayDetails(
                        actualKm = actualKm ?: 0.0,
                        totalWorkMinutes = (workHours ?: 0.0) * 60.0,
                        actualRouteMinutes = (routeHours ?: 0.0) * 60.0,
                        completedVisitsCount = (completedVisits ?: 0).coerceAtLeast(0),
                        startOdometer = uiState.startOdometer,
                        endOdometer = endOdometer ?: 0.0,
                        fuelExpenses = parseNumber(fuelExpensesText) ?: 0.0,
                        fuelLiters = parseNumber(fuelLitersText) ?: 0.0,
                        fuelConsumptionLitersPer100Km = parseNumber(fuelConsumptionText) ?: 0.0,
                        fuelCompensation = parseNumber(fuelCompensationText) ?: 0.0,
                        parkingCompensation = parseNumber(parkingCompensationText) ?: 0.0,
                        tollExpenses = parseNumber(tollExpensesText) ?: 0.0,
                        tollCompensation = parseNumber(tollCompensationText) ?: 0.0,
                        otherExpenses = parseNumber(otherExpensesText) ?: 0.0,
                        userWorkloadIndex = userWorkload,
                    ),
                )
            },
        ) {
            Text("Завершить день с расчётом")
        }
    }
}

@Composable
internal fun GpsEstimateControls(state: GpsEstimateUiState, onRefresh: () -> Unit, onApply: () -> Unit) {
    val estimate = state.estimate
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (state.message.isNotBlank()) {
            Text(
                state.message,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (estimate != null) {
            Text(
                "GPS: работа ${minutesText(estimate.totalWorkMinutes)}, дорога ${minutesText(estimate.routeMinutes)}, адрес ${oneDecimal(estimate.avgServiceMinutes)} мин, распознано ${estimate.detectedVisitsCount}.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                modifier = Modifier.weight(1f),
                enabled = !state.isLoading,
                onClick = onRefresh,
            ) {
                Text(if (state.isLoading) "Обновляю" else "GPS-оценка")
            }
            Button(
                modifier = Modifier.weight(1f),
                enabled = estimate != null,
                onClick = onApply,
            ) {
                Text("Подставить GPS")
            }
        }
    }
}

@Composable
internal fun WorkScreen(uiState: HomeVisitUiState, workActions: WorkActions) {
    val candidate = uiState.candidate
    var showResult by rememberSaveable { mutableStateOf(false) }
    // Датчик выгоды всплывает, как только пришёл расчёт (или нужен ручной маршрут), и
    // сам уходит, когда заказ принят/отклонён: считать больше нечего. Раньше лист на
    // терминальном состоянии не закрывался — приём переоткрывал его (у промежуточного
    // «Принимаю адрес…» расчёт ещё был), и человек оставался с «Адрес принят» на экране.
    LaunchedEffect(candidate.estimate, candidate.needsManualRoute, candidate.message, candidate.done) {
        when {
            candidate.estimate != null || candidate.needsManualRoute -> showResult = true
            candidate.done -> showResult = false
        }
    }

    ScreenColumn {
        EvaluateForm(
            candidate = candidate,
            clinics = uiState.clinics.all,
            // «Частый тариф» из настроек; если не задан — доход последнего заказа смены.
            frequentIncome = uiState.appSettings.settingNumber("frequent_income")
                ?: uiState.routeVisits.lastOrNull()?.income,
            templates = uiState.appSettings.addressTemplates(),
            recentAddresses = uiState.recentAddresses,
            personalTrip = uiState.personalTrip,
            onCalculate = workActions.onCalculateVisit,
            onPersonalEstimate = workActions.onPersonalEstimate,
            onClearPersonal = workActions.onClearPersonalEstimate,
            onServerVoiceTranscribe = workActions.onServerVoiceTranscribe,
            onPickCandidate = workActions.onPickAddressCandidate,
            onReopenResult = { showResult = true },
        )
        OtherEntriesSection(uiState, workActions)
    }

    if (showResult) {
        ModalBottomSheet(
            onDismissRequest = { showResult = false },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        ) {
            CandidateGauge(
                candidate = candidate,
                onAccept = {
                    workActions.onAcceptCandidate()
                    showResult = false
                },
                onReject = {
                    workActions.onRejectCandidate()
                    showResult = false
                },
            )
        }
    }
}

/**
 * Чипы недавних адресов (Ф13.1): самый быстрый ввод — тап по адресу из истории дня.
 * Горизонтальный ряд, чтобы длинные адреса не ломали вёрстку.
 */
@Composable
internal fun RecentAddressChips(addresses: List<String>, onPick: (String) -> Unit) {
    androidx.compose.foundation.layout.Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        addresses.forEach { addr ->
            androidx.compose.material3.SuggestionChip(
                onClick = { onPick(addr) },
                label = {
                    Text(addr, maxLines = 1, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                },
            )
        }
    }
}

/** Форма «Оценить заказ»: только адрес, доход (с частым тарифом) и опциональная компания. */
@Composable
internal fun EvaluateForm(
    candidate: CandidateUiState,
    clinics: List<String>,
    frequentIncome: Double?,
    templates: List<AddressTemplate>,
    recentAddresses: List<String> = emptyList(),
    personalTrip: PersonalTripUi = PersonalTripUi(),
    onCalculate: (String, Double, String, Double?, Double?, String?, Double?) -> Unit,
    onPersonalEstimate: (String) -> Unit = {},
    onClearPersonal: () -> Unit = {},
    onServerVoiceTranscribe: (ByteArray, (String?) -> Unit) -> Unit = { _, cb -> cb(null) },
    onPickCandidate: (AddressCandidate) -> Unit,
    onReopenResult: () -> Unit,
) {
    // Рубильник «Работа / Личная поездка» (Ф11.5). В личном режиме нет дохода и вердикта:
    // человек не зарабатывает, а хочет знать, во сколько обойдётся съездить туда-обратно.
    var personalMode by rememberSaveable { mutableStateOf(false) }
    var address by rememberSaveable { mutableStateOf("") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    // Пусто = «Без компании» (общий учёт — минимализм для новичков).
    var clinic by rememberSaveable { mutableStateOf("") }
    // Ручной маршрут показываем только когда геокодер не справился.
    var routeKmText by rememberSaveable { mutableStateOf("") }
    var routeMinutesText by rememberSaveable { mutableStateOf("") }
    // Адрес последнего расчёта: к нему привязана плашка ручного км/мин. Исправили
    // адрес — плашка и старые ручные значения не должны пережить исправление.
    var lastCalculatedAddress by rememberSaveable { mutableStateOf("") }
    val income = parseNumber(incomeText)
    val routeKm = parseNumber(routeKmText)
    val routeMinutes = parseNumber(routeMinutesText)
    val hasManualRoute = routeKm != null && routeMinutes != null

    // Голосовой ввод адреса (Ф14.4): системный распознаватель телефона — мгновенно, на
    // устройстве, без нашего сервера. Распознанный текст ложится в поле и правится до
    // подтверждения (контроль у человека).
    val voiceLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            val spoken = result.data
                ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                ?.firstOrNull()
            if (!spoken.isNullOrBlank()) address = spoken
        }
    }

    // Серверный ASR-фолбэк (Ф14.4) — ТОЛЬКО когда системного распознавателя нет (телефоны
    // без Google-сервисов). Тогда микрофон-кнопка сама пишет короткое аудио и шлёт на наш
    // сервер по шифрованному каналу. На телефонах с Google этот путь не используется.
    val context = LocalContext.current
    val hasSystemRecognizer = remember { SpeechRecognizer.isRecognitionAvailable(context) }
    val recorder = remember { ServerVoiceRecorder(context) }
    var recording by remember { mutableStateOf(false) }
    var transcribing by remember { mutableStateOf(false) }
    // Запись живёт секунды: если экран уходит во время записи — обрубаем и удаляем файл.
    DisposableEffect(Unit) { onDispose { recorder.cancel() } }
    val micPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> if (granted) recording = recorder.start() }
    // Остановить запись и распознать на сервере; результат — в поле адреса.
    fun stopAndTranscribe() {
        recording = false
        val audio = recorder.stop() ?: return
        transcribing = true
        onServerVoiceTranscribe(audio) { text ->
            transcribing = false
            if (!text.isNullOrBlank()) address = text
        }
    }
    // Тап по микрофону: системный распознаватель — если есть; иначе наша запись (старт/стоп).
    fun onMicTap() {
        if (hasSystemRecognizer) {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
                putExtra(RecognizerIntent.EXTRA_PROMPT, "Назовите адрес")
            }
            runCatching { voiceLauncher.launch(intent) }
            return
        }
        if (transcribing) return
        if (recording) {
            stopAndTranscribe()
        } else if (context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            recording = recorder.start()
        } else {
            micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    InputCard(if (personalMode) "Личная поездка" else "Оценить заказ") {
        // Рубильник режима: тап переключает и сбрасывает прошлый результат личной поездки,
        // чтобы старая цифра не висела над новым адресом.
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = !personalMode,
                onClick = { personalMode = false; onClearPersonal() },
                label = { Text("Работа") },
            )
            FilterChip(
                selected = personalMode,
                onClick = { personalMode = true },
                label = { Text("Личная поездка") },
            )
        }
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = address,
            onValueChange = { address = it },
            label = { Text("Адрес") },
            singleLine = false,
            trailingIcon = {
                when {
                    transcribing -> CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                    recording -> IconButton(onClick = { onMicTap() }) {
                        Icon(Icons.Filled.Stop, contentDescription = "Остановить запись", tint = MaterialTheme.colorScheme.error)
                    }
                    else -> IconButton(onClick = { onMicTap() }) {
                        Icon(Icons.Filled.Mic, contentDescription = "Голосовой ввод адреса")
                    }
                }
            },
        )
        // Подсказка во время записи: человек видит, что идёт запись и как её завершить.
        if (recording) {
            Text(
                "Идёт запись — назовите адрес и нажмите ■",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.error,
            )
        }
        // Чипы недавних адресов (Ф13.1): тап = адрес в один тап, повторный резолвится
        // мгновенно из learned-кеша (Ф13.2). Показываем, только когда поле пустое.
        if (address.isBlank() && recentAddresses.isNotEmpty()) {
            RecentAddressChips(recentAddresses) { address = it }
        }
        // Набрали название шаблона — показываем, какой адрес за ним стоит.
        val resolved = resolveAddressTemplate(address, templates)
        if (resolved != address.trim() && address.isNotBlank()) {
            Text(
                "Шаблон «${address.trim()}» → $resolved",
                style = MaterialTheme.typography.labelMedium,
                color = VerdictColors.go,
            )
        }
        if (!personalMode) {
            MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Доход, ₽")
            if (frequentIncome != null && frequentIncome > 0 && incomeText.isBlank()) {
                OutlinedButton(onClick = { incomeText = frequentIncome.toLong().toString() }) {
                    Text("Частый тариф: ${money(frequentIncome)}")
                }
            }
            CompanyPicker(clinics = clinics, value = clinic, onValue = { clinic = it })
            // Поля «Источник заказа» и «Цена отклика» (Ф11.2) временно убраны из формы по
            // просьбе — проводка на бэкенде (order_source/response_cost) сохранена, вернуть
            // = добавить сюда два поля и передать их в onCalculate вместо null.
            // Сервер не уверен в адресе — предлагаем 2–3 варианта. Тап = подтверждение,
            // координаты выбранного уходят в расчёт как ручная точка. Молча ничего не
            // берём. Адрес исправили — старый список неактуален и прячется.
            if (candidate.addressCandidates.isNotEmpty() && resolved == candidate.candidatesForAddress) {
                AddressCandidatesList(candidate.addressCandidates, onPickCandidate)
            }
            // Плашка живёт, пока в поле тот же адрес, что не распознался. Исправили
            // адрес — плашка исчезает, «Оценить заказ» снова пробует геокодер, а не
            // требует вносить километраж руками.
            if (candidate.needsManualRoute && resolved == lastCalculatedAddress) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    MoneyField(modifier = Modifier.weight(1f), value = routeKmText, onValueChange = { routeKmText = it }, label = "Км вручную")
                    MoneyField(modifier = Modifier.weight(1f), value = routeMinutesText, onValueChange = { routeMinutesText = it }, label = "Мин вручную")
                }
                // Заполнено, но не распозналось (или только одно из двух) — раньше оба
                // значения молча выбрасывались, уходили null,null, и сервер снова просил
                // «уточните маршрут». Человек «всё заполнил» и ходил по кругу без слов.
                val manualRouteBroken =
                    (routeKmText.isNotBlank() || routeMinutesText.isNotBlank()) && !hasManualRoute
                if (manualRouteBroken) {
                    Text(
                        "Км и мин не распознаны: нужны оба числа, без минусов и букв.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                } else {
                    Text(
                        // Не «адрес не распознан»: сюда попадают и случаи, когда адрес найден,
                        // а не построился МАРШРУТ (нет старта смены, вне покрытия карт).
                        "Маршрут не построился автоматически — укажите километраж и время вручную.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
        if (personalMode) {
            // Сервер не уверен в адресе (опечатка, два похожих проспекта) — те же
            // 2–3 кандидата одним тапом, что и в рабочем режиме. Молча не подставляем.
            // Адрес исправили — старый список неактуален и прячется.
            if (personalTrip.addressCandidates.isNotEmpty() && resolved == personalTrip.candidatesForAddress) {
                AddressCandidatesList(personalTrip.addressCandidates, onPickCandidate)
            }
            Button(
                modifier = Modifier.fillMaxWidth(),
                enabled = address.isNotBlank() && !personalTrip.isLoading,
                onClick = { onPersonalEstimate(resolveAddressTemplate(address, templates)) },
            ) {
                Text(if (personalTrip.isLoading) "Считаю…" else "Сколько обойдётся?")
            }
        } else {
            Button(
                modifier = Modifier.fillMaxWidth(),
                enabled = address.isNotBlank() && income != null && !candidate.isLoading,
                onClick = {
                    // Набрали название шаблона («Дом») — отправляем сохранённый за ним
                    // адрес: геокодер по названию ничего не найдёт.
                    val submitted = resolveAddressTemplate(address, templates)
                    // Адрес исправили после неудачи — ручные км/мин относились к старому
                    // адресу и не переносятся: сначала снова пробуем геокодер.
                    val sameAddress = submitted == lastCalculatedAddress
                    if (!sameAddress) {
                        routeKmText = ""
                        routeMinutesText = ""
                    }
                    lastCalculatedAddress = submitted
                    onCalculate(
                        submitted,
                        income ?: 0.0,
                        clinic,
                        if (sameAddress && hasManualRoute) routeKm else null,
                        if (sameAddress && hasManualRoute) routeMinutes else null,
                        null,
                        null,
                    )
                },
            ) {
                Text(if (candidate.isLoading) "Считаю…" else "Оценить заказ")
            }
            if (candidate.estimate != null) {
                TextButton(onClick = onReopenResult, modifier = Modifier.fillMaxWidth()) {
                    Text("Показать оценку снова")
                }
            }
        }
    }
    // Результат личной поездки — отдельной карточкой под формой (Ф11.5).
    if (personalMode && (personalTrip.isLoading || personalTrip.result != null || personalTrip.message.isNotBlank())) {
        PersonalTripCard(personalTrip)
    }
}

/**
 * Список 2–3 кандидатов адреса, когда сервер не уверен (Фаза 2). Компактно, одним
 * тапом: подпись адреса и — мелко — откуда вариант. Выбор координат уходит в расчёт
 * как ручная точка; сервер молча ничего не подставлял.
 */
@Composable
internal fun AddressCandidatesList(
    candidates: List<AddressCandidate>,
    onPick: (AddressCandidate) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            "Уточните адрес — какой из этих?",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        candidates.forEach { candidate ->
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onPick(candidate) },
                shape = MaterialTheme.shapes.medium,
                tonalElevation = 2.dp,
            ) {
                Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                    Text(candidate.label, style = MaterialTheme.typography.bodyLarge)
                    val hint = addressSourceHint(candidate.source)
                    if (hint.isNotBlank()) {
                        Text(
                            hint,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}

/** Человеческая подпись, откуда взялся вариант адреса. */
private fun addressSourceHint(source: String): String = when (source) {
    "dadata" -> "по подсказкам"
    "osm" -> "по карте"
    "nominatim" -> "по карте"
    else -> ""
}

/**
 * Свёрнутый блок прочих записей — вне основного потока оценки: работа на точке и
 * удалённая работа. Расходы отсюда убраны: их спрашивает мастер завершения смены,
 * одним списком и по памяти всего дня, а не по одному в течение смены.
 */
@Composable
internal fun OtherEntriesSection(uiState: HomeVisitUiState, workActions: WorkActions) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    var form by rememberSaveable { mutableStateOf(WorkForm.Office) }
    Spacer(Modifier.height(2.dp))
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .clickable { expanded = !expanded }
            .padding(horizontal = 6.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("Другие записи", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
        Icon(
            imageVector = if (expanded) Icons.Filled.Remove else Icons.Filled.Add,
            contentDescription = if (expanded) "Скрыть" else "Показать",
            tint = MaterialTheme.colorScheme.primary,
        )
    }
    if (expanded) {
        OptionGrid(
            options = listOf(WorkForm.Office, WorkForm.Telemed),
            selected = form,
            label = { it.title() },
            onSelect = { form = it },
        )
        when (form) {
            WorkForm.Office -> OfficeInputCard(uiState.clinics.all, workActions.onAddOffice)
            WorkForm.Telemed -> TelemedInputCard(uiState.clinics.telemed, workActions.onAddTelemed)
            WorkForm.Expense, WorkForm.Visit -> Unit
        }
    }
}

/**
 * Выбор компании для заказа — выпадающий список (строкой, не кнопками):
 * «Без компании» по умолчанию, затем компании пользователя из настроек, а в конце
 * «Ввести вручную…» для разовой акции (произвольное название, не попадает в общий
 * список, но отдельно учитывается по строке). Пусто = «Без компании».
 */
@Composable
internal fun CompanyPicker(clinics: List<String>, value: String, onValue: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    var manual by rememberSaveable { mutableStateOf(false) }
    // Подписи берём из выбранного пресета: сменил человек «Компания» на «Клиника» —
    // и здесь должно стать «Без клиники». Раньше эти строки были захардкожены, и
    // переключение источника заказов на самом заметном месте ничего не меняло.
    val source = OrderSource.current
    val none = "Без ${source.genSingle}"
    val display = when {
        manual -> "Вручную"
        value.isBlank() -> none
        else -> value
    }
    Text(
        "${source.nomSingle} · необязательно",
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Box(Modifier.fillMaxWidth()) {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Text(display, modifier = Modifier.weight(1f), textAlign = TextAlign.Start, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Icon(Icons.Filled.ArrowDropDown, contentDescription = "Выбрать: ${source.nomSingle.lowercase()}")
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            DropdownMenuItem(
                text = { Text(none) },
                onClick = { manual = false; onValue(""); expanded = false },
            )
            clinics.forEach { name ->
                DropdownMenuItem(
                    text = { Text(name) },
                    onClick = { manual = false; onValue(name); expanded = false },
                )
            }
            DropdownMenuItem(
                text = { Text("Ввести вручную…") },
                onClick = { manual = true; onValue(""); expanded = false },
            )
        }
    }
    if (manual) {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = value,
            onValueChange = onValue,
            label = { Text("Название: ${source.nomSingle.lowercase()} (разовая)") },
            singleLine = true,
        )
    }
}

@Composable
internal fun QuickActions(onOpenWork: () -> Unit) {
    SectionHeader("Быстрые действия")
    ActionGrid(
        actions = listOf(
            "+ Адрес" to "Выездной заказ с расчетом.",
            "На точке" to "Заказ на точке (офис/пункт).",
            "Удалённо" to "Онлайн-заказ без выезда.",
            "Расход" to "Еда, кофе, парковка.",
        ),
        onClick = onOpenWork,
    )
}

@Composable
internal fun WorkFormTabs(selectedForm: WorkForm, onSelect: (WorkForm) -> Unit) {
    OptionGrid(
        options = WorkForm.entries.toList(),
        selected = selectedForm,
        label = { it.title() },
        onSelect = onSelect,
    )
}

/**
 * Датчик выгоды (вариант «кольцо») в нижнем листе: кольцо «Выгодность 0–100» +
 * ₽/ч и три плитки, ниже — «Отказаться» / «Принять». Семантика цвета кнопок:
 * невыгодно (score<34) → «Отказаться» красная; выгодно (score≥67) → «Принять»
 * зелёная; вторая кнопка нейтральная.
 */
@Composable
internal fun CandidateGauge(candidate: CandidateUiState, onAccept: () -> Unit, onReject: () -> Unit) {
    val estimate = candidate.estimate
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp)
            .padding(bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        when {
            candidate.isLoading -> {
                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                Text("Считаю выгодность…", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            estimate == null -> {
                // Заголовок — по СМЫСЛУ состояния, а не по тому, что расчёта нет.
                // «Адрес принят» тоже приходит без расчёта (считать больше нечего), и
                // раньше успех показывался под заголовком «Не удалось рассчитать».
                val title = when {
                    candidate.done -> candidate.message
                    candidate.needsManualRoute -> "Нужно уточнить маршрут"
                    else -> "Не удалось рассчитать"
                }
                Text(
                    title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                // При done текст уже стоит в заголовке — второй раз не повторяем.
                if (!candidate.done && candidate.message.isNotBlank()) {
                    Text(candidate.message, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
                }
                if (candidate.needsManualRoute) {
                    Text(
                        "Заполните «Км вручную» и «Мин вручную» в форме и нажмите «Оценить» снова.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center,
                    )
                }
                EstimateWarnings(candidate.warnings)
            }
            else -> {
                val score = estimate.score
                val accent = when {
                    score >= 67 -> VerdictColors.go
                    score < 34 -> VerdictColors.skip
                    else -> VerdictColors.edge
                }
                val track = MaterialTheme.colorScheme.surfaceContainerHighest
                Box(Modifier.size(156.dp), contentAlignment = Alignment.Center) {
                    Canvas(Modifier.fillMaxSize()) {
                        val stroke = 15.dp.toPx()
                        val inset = stroke / 2
                        val arc = androidx.compose.ui.geometry.Size(size.width - stroke, size.height - stroke)
                        val topLeft = Offset(inset, inset)
                        drawArc(color = track, startAngle = 0f, sweepAngle = 360f, useCenter = false, topLeft = topLeft, size = arc, style = Stroke(width = stroke, cap = StrokeCap.Round))
                        drawArc(color = accent, startAngle = -90f, sweepAngle = 360f * (score / 100f), useCenter = false, topLeft = topLeft, size = arc, style = Stroke(width = stroke, cap = StrokeCap.Round))
                    }
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("$score", fontFamily = JetBrainsMono, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold, color = accent)
                        Text("выгодность", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Text(estimate.decision, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = accent, textAlign = TextAlign.Center)
                if (estimate.reason.isNotBlank()) {
                    Text(estimate.reason, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
                }
                EstimateWarnings(candidate.warnings)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    GaugeTile(Modifier.weight(1f), money(estimate.afterHourly), "чистыми/ч")
                    // Деньги на километр — рядом с деньгами на час. Порознь они обманчивы:
                    // короткий дорогой заказ в соседнем доме даёт огромные ₽/км и нулевые
                    // ₽/ч. У городского курьера ограничивает время, у межгорода — километры.
                    GaugeTile(Modifier.weight(1f), money(estimate.marginalPerKm), "чистыми/км")
                    GaugeTile(Modifier.weight(1f), "${oneDecimal(estimate.costPerKm)} ₽", "км стоит")
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    GaugeTile(Modifier.weight(1f), "+${oneDecimal(estimate.extraKm)} км", "дорога")
                    GaugeTile(Modifier.weight(1f), "+${oneDecimal(estimate.extraDriveMinutes)} мин", "в пути")
                }
                // Состояние подняло минимальный тариф — вердикт выше уже посчитан по
                // новому порогу, и человек должен понимать, почему сегодня строже.
                if (estimate.tariffRaised) {
                    RaisedTariffRow(estimate)
                }
                // Платная зона — самостоятельный факт про адрес, к поднятому тарифу
                // отношения не имеющий. Раньше карточка стояла ВНУТРИ ветки
                // tariffRaised, и заметка «адрес в зоне платной парковки» показывалась
                // только в те дни, когда сработала надбавка за переработку. В обычный
                // день человек про платную зону не узнавал вовсе.
                ParkingHintCard(candidate.parking)
                Row(Modifier.fillMaxWidth().padding(top = 4.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(
                        modifier = Modifier.weight(1f),
                        onClick = onReject,
                        colors = if (score < 34)
                            ButtonDefaults.buttonColors(containerColor = VerdictColors.skip, contentColor = Color.White)
                        else
                            ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh, contentColor = MaterialTheme.colorScheme.onSurface),
                    ) { Text("Отказаться") }
                    Button(
                        modifier = Modifier.weight(1f),
                        onClick = onAccept,
                        colors = if (score >= 67)
                            ButtonDefaults.buttonColors(containerColor = VerdictColors.go, contentColor = Color.White)
                        else
                            ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh, contentColor = MaterialTheme.colorScheme.onSurface),
                    ) { Text("Принять") }
                }
            }
        }
    }
}

/**
 * Оговорки честности оценки (нет старта смены, мало заказов в ленте) — жёлтым,
 * над кнопками: человек должен увидеть их ДО того, как поверил цифре.
 */
@Composable
private fun EstimateWarnings(warnings: List<String>) {
    warnings.forEach { warning ->
        Text(
            warning,
            style = MaterialTheme.typography.bodySmall,
            color = VerdictColors.edge,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun GaugeTile(modifier: Modifier, value: String, caption: String) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.surfaceContainerLow)
            .padding(vertical = 10.dp, horizontal = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Text(value, fontFamily = JetBrainsMono, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, maxLines = 1)
        Text(caption, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
    }
}

/**
 * Работа на точке: адрес с фиксированным временем. Попадает в Ленту заказом-якорем —
 * дорога до неё считается, а оптимизатор её не переставляет. Продолжительность не
 * спрашиваем: она выводится из начала и окончания.
 */
@Composable
internal fun OfficeInputCard(
    clinics: List<String>,
    onSubmit: (String, Double, Double, String, String?, String?) -> Unit,
) {
    var address by rememberSaveable { mutableStateOf("") }
    // Время храним минутами от полуночи: барабан крутит именно их. По умолчанию —
    // типовой приём с 9:00 до 13:00, чтобы обычный случай не требовал вообще ничего.
    var startMinutes by rememberSaveable { mutableStateOf(9 * 60) }
    var endMinutes by rememberSaveable { mutableStateOf(13 * 60) }
    var incomeText by rememberSaveable { mutableStateOf("") }
    var clinic by rememberSaveable { mutableStateOf("") }

    val income = parseNumber(incomeText)
    val minutes = durationMinutes(startMinutes, endMinutes)

    InputCard("На точке") {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = address,
            onValueChange = { address = it },
            label = { Text("Адрес точки") },
            singleLine = false,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Column(Modifier.weight(1f)) {
                LabeledTimeWheel(
                    label = "Начало",
                    minutesOfDay = startMinutes,
                    onChange = { startMinutes = it },
                )
            }
            Column(Modifier.weight(1f)) {
                LabeledTimeWheel(
                    label = "Окончание",
                    minutesOfDay = endMinutes,
                    onChange = { endMinutes = it },
                )
            }
        }
        Text(
            "Продолжительность: ${minutesText(minutes.toDouble())}",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Стоимость, ₽")
        CompanyPicker(clinics = clinics, value = clinic, onValue = { clinic = it })
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = address.isNotBlank() && income != null && minutes > 0,
            onClick = {
                onSubmit(
                    address,
                    minutes.toDouble(),
                    income ?: 0.0,
                    clinic,
                    todayAtIso(minutesToLocalTime(startMinutes)),
                    todayAtIso(minutesToLocalTime(endMinutes)),
                )
                address = ""
                startMinutes = 9 * 60
                endMinutes = 13 * 60
                incomeText = ""
            },
        ) {
            Text("Добавить в Ленту")
        }
    }
}

@Composable
internal fun TelemedInputCard(clinics: List<String>, onSubmit: (Double, Double, String) -> Unit) {
    var minutesText by rememberSaveable { mutableStateOf("3") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    var clinic by rememberSaveable(clinics) { mutableStateOf(clinics.firstOrNull().orEmpty()) }
    val minutes = parseNumber(minutesText)
    val income = parseNumber(incomeText)

    InputCard("Удалённые заказы") {
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Стоимость")
        MoneyField(value = minutesText, onValueChange = { minutesText = it }, label = "Минуты")
        ClinicPicker(clinics = clinics, selected = clinic, onSelect = { clinic = it })
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = minutes != null && income != null && clinic.isNotBlank(),
            onClick = {
                onSubmit(minutes ?: 3.0, income ?: 0.0, clinic)
                incomeText = ""
            },
        ) {
            Text("Сохранить удалённый заказ")
        }
    }
}


/**
 * «Обычный минимум 900 ₽/ч → сегодня 1 150 ₽/ч».
 *
 * Это и есть смысл всех индексов: состояние меняет экономическое решение. Раньше
 * усталость считалась на сервере, доезжала до телефона и нигде не показывалась —
 * то есть не влияла ни на что.
 */
/**
 * «Адрес в зоне платной парковки».
 *
 * Стоит рядом с вердиктом, а не после согласия ехать: человек должен узнать о парковке
 * ДО того, как нажал «Принять». Расход в вердикт не входит — платит он в приложении
 * своего города, и цена там своя (у резидентов и по абонементу другая). Мы
 * предупреждаем, а не считаем за него.
 */
@Composable
private fun ParkingHintCard(parking: ParkingHint?) {
    if (parking == null) return
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = VerdictColors.edgeContainer),
        border = BorderStroke(1.dp, VerdictColors.edge),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                Modifier
                    .size(26.dp)
                    .clip(RoundedCornerShape(7.dp))
                    .background(VerdictColors.edge),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "P",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF3A2A05),
                )
            }
            Column {
                Text(
                    parking.headline,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = VerdictColors.onEdgeContainer,
                )
                Text(
                    parking.details,
                    style = MaterialTheme.typography.bodySmall,
                    color = VerdictColors.onEdgeContainer,
                )
            }
        }
    }
}

@Composable
private fun RaisedTariffRow(estimate: CandidateEstimate) {
    val tone = if (estimate.overworkBlocksOutsideZone) VerdictColors.skip else VerdictColors.edge
    val container = if (estimate.overworkBlocksOutsideZone) VerdictColors.skipContainer else VerdictColors.edgeContainer
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(container)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Filled.Bolt, contentDescription = null, tint = tone, modifier = Modifier.size(18.dp))
        Column {
            Text(
                "Сегодня твой минимум выше",
                style = MaterialTheme.typography.labelMedium,
                color = tone,
            )
            Text(
                "${money(estimate.baseMinHourly)} → ${money(estimate.effectiveMinHourly)} " +
                    "(+${estimate.overworkMarkupPercent}%) — по долгу восстановления",
                style = MaterialTheme.typography.bodySmall,
                fontFamily = JetBrainsMono,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
