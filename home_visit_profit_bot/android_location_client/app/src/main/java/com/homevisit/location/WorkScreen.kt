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
internal fun DayDetailsCard(uiState: HomeVisitUiState, workActions: WorkActions) {
    if (uiState.status == WorkDayStatus.Active) {
        var endOdometerText by rememberSaveable { mutableStateOf("") }
        val endOdometer = parseNumber(endOdometerText)
        InputCard("Параметры дня") {
            Text(
                "Старт: ${uiState.startAddress.ifBlank { "не указан" }}. Финиш: ${uiState.finishAddress.ifBlank { "не указан" }}.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Сон: ${oneDecimal(uiState.sleepHours)} ч, качество ${oneDecimal(uiState.sleepQuality)}/5. Одометр старт: ${oneDecimal(uiState.startOdometer)} км.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            MoneyField(value = endOdometerText, onValueChange = { endOdometerText = it }, label = "Одометр на конец")
            OutlinedButton(
                modifier = Modifier.fillMaxWidth(),
                onClick = { workActions.onEndDayWithOdometer(endOdometer) },
            ) {
                Text("Завершить день с одометром")
            }
        }
        EndDayDetailsCard(uiState = uiState, workActions = workActions)
        return
    }

    var startAddress by rememberSaveable { mutableStateOf("Дом") }
    var finishAddress by rememberSaveable { mutableStateOf("Дом") }
    var startOdometerText by rememberSaveable { mutableStateOf("") }
    var sleepHoursText by rememberSaveable { mutableStateOf("") }
    var sleepQualityText by rememberSaveable { mutableStateOf("") }
    var breakHoursText by rememberSaveable { mutableStateOf("") }
    val startOdometer = parseNumber(startOdometerText) ?: 0.0
    val sleepHours = parseNumber(sleepHoursText) ?: 0.0
    val sleepQuality = parseNumber(sleepQualityText) ?: 0.0
    val breakHours = parseNumber(breakHoursText) ?: 0.0

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
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(
                modifier = Modifier.weight(1f),
                value = startOdometerText,
                onValueChange = { startOdometerText = it },
                label = "Одометр",
            )
            MoneyField(
                modifier = Modifier.weight(1f),
                value = sleepHoursText,
                onValueChange = { sleepHoursText = it },
                label = "Сон, ч",
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(
                modifier = Modifier.weight(1f),
                value = sleepQualityText,
                onValueChange = { sleepQualityText = it },
                label = "Сон 0-5",
            )
            MoneyField(
                modifier = Modifier.weight(1f),
                value = breakHoursText,
                onValueChange = { breakHoursText = it },
                label = "Перерыв, ч",
            )
        }
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = startAddress.isNotBlank() && finishAddress.isNotBlank(),
            onClick = {
                workActions.onStartDayDetails(
                    startAddress,
                    finishAddress,
                    startOdometer,
                    sleepHours,
                    sleepQuality,
                    breakHours,
                )
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
    var fatigueText by rememberSaveable { mutableStateOf("") }

    val actualKm = parseNumber(actualKmText)
    val workHours = parseNumber(workHoursText)
    val routeHours = parseNumber(routeHoursText)
    val completedVisits = parseNumber(completedVisitsText)?.toInt()
    val endOdometer = parseNumber(endOdometerText)
    val userFatigue = parseNumber(fatigueText)?.coerceIn(0.0, 100.0)

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
            MoneyField(modifier = Modifier.weight(1f), value = fatigueText, onValueChange = { fatigueText = it }, label = "Нагрузка 0-100")
        }
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = actualKm != null && workHours != null && routeHours != null && completedVisits != null && endOdometer != null,
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
                        userFatigueScore = userFatigue,
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
    // Датчик выгоды всплывает, как только пришёл расчёт (или нужен ручной маршрут).
    LaunchedEffect(candidate.estimate, candidate.needsManualRoute, candidate.message) {
        if (candidate.estimate != null || candidate.needsManualRoute) showResult = true
    }

    ScreenColumn {
        EvaluateForm(
            candidate = candidate,
            clinics = uiState.clinics.all,
            // «Частый тариф» из настроек; если не задан — доход последнего заказа смены.
            frequentIncome = uiState.appSettings.settingNumber("frequent_income")
                ?: uiState.routeVisits.lastOrNull()?.income,
            onCalculate = workActions.onCalculateVisit,
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

/** Форма «Оценить заказ»: только адрес, доход (с частым тарифом) и опциональная компания. */
@Composable
internal fun EvaluateForm(
    candidate: CandidateUiState,
    clinics: List<String>,
    frequentIncome: Double?,
    onCalculate: (String, Double, String, Double?, Double?) -> Unit,
    onReopenResult: () -> Unit,
) {
    var address by rememberSaveable { mutableStateOf("") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    // Пусто = «Без компании» (общий учёт — минимализм для новичков).
    var clinic by rememberSaveable { mutableStateOf("") }
    // Ручной маршрут показываем только когда геокодер не справился.
    var routeKmText by rememberSaveable { mutableStateOf("") }
    var routeMinutesText by rememberSaveable { mutableStateOf("") }
    val income = parseNumber(incomeText)
    val routeKm = parseNumber(routeKmText)
    val routeMinutes = parseNumber(routeMinutesText)
    val hasManualRoute = routeKm != null && routeMinutes != null

    InputCard("Оценить заказ") {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = address,
            onValueChange = { address = it },
            label = { Text("Адрес") },
            singleLine = false,
        )
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Доход, ₽")
        if (frequentIncome != null && frequentIncome > 0 && incomeText.isBlank()) {
            OutlinedButton(onClick = { incomeText = frequentIncome.toLong().toString() }) {
                Text("Частый тариф: ${money(frequentIncome)}")
            }
        }
        CompanyPicker(clinics = clinics, value = clinic, onValue = { clinic = it })
        if (candidate.needsManualRoute) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MoneyField(modifier = Modifier.weight(1f), value = routeKmText, onValueChange = { routeKmText = it }, label = "Км вручную")
                MoneyField(modifier = Modifier.weight(1f), value = routeMinutesText, onValueChange = { routeMinutesText = it }, label = "Мин вручную")
            }
            Text(
                "Адрес не распознан по карте — укажите километраж и время вручную.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = address.isNotBlank() && income != null && !candidate.isLoading,
            onClick = {
                onCalculate(
                    address,
                    income ?: 0.0,
                    clinic,
                    if (hasManualRoute) routeKm else null,
                    if (hasManualRoute) routeMinutes else null,
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
    val display = when {
        manual -> "Вручную"
        value.isBlank() -> "Без компании"
        else -> value
    }
    Text(
        "Компания · необязательно",
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Box(Modifier.fillMaxWidth()) {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Text(display, modifier = Modifier.weight(1f), textAlign = TextAlign.Start, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Icon(Icons.Filled.ArrowDropDown, contentDescription = "Выбрать компанию")
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            DropdownMenuItem(
                text = { Text("Без компании") },
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
            label = { Text("Название компании (разовая)") },
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
                Text(
                    if (candidate.needsManualRoute) "Нужно уточнить маршрут" else "Не удалось рассчитать",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                if (candidate.message.isNotBlank()) {
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
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    GaugeTile(Modifier.weight(1f), money(estimate.afterHourly), "чистыми/ч")
                    GaugeTile(Modifier.weight(1f), "+${oneDecimal(estimate.extraKm)} км", "дорога")
                    GaugeTile(Modifier.weight(1f), "+${oneDecimal(estimate.extraDriveMinutes)} мин", "в пути")
                }
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
    var startText by rememberSaveable { mutableStateOf("") }
    var endText by rememberSaveable { mutableStateOf("") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    var clinic by rememberSaveable { mutableStateOf("") }

    val income = parseNumber(incomeText)
    val start = parseTimeOfDay(startText)
    val end = parseTimeOfDay(endText)
    val minutes = if (start != null && end != null) minutesBetween(start, end) else null

    InputCard("На точке") {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = address,
            onValueChange = { address = it },
            label = { Text("Адрес точки") },
            singleLine = false,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MoneyField(
                value = startText,
                onValueChange = { startText = it },
                label = "Начало, 9:00",
                modifier = Modifier.weight(1f),
            )
            MoneyField(
                value = endText,
                onValueChange = { endText = it },
                label = "Окончание, 13:00",
                modifier = Modifier.weight(1f),
            )
        }
        if (minutes != null) {
            Text(
                "Продолжительность: ${minutesText(minutes.toDouble())}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Стоимость, ₽")
        CompanyPicker(clinics = clinics, value = clinic, onValue = { clinic = it })
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = address.isNotBlank() && income != null && minutes != null && minutes > 0,
            onClick = {
                onSubmit(
                    address,
                    (minutes ?: 0L).toDouble(),
                    income ?: 0.0,
                    clinic,
                    start?.let { todayAtIso(it) },
                    end?.let { todayAtIso(it) },
                )
                address = ""
                startText = ""
                endText = ""
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

