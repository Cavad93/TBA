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
    var selectedForm by rememberSaveable { mutableStateOf(WorkForm.Visit) }

    ScreenColumn {
        StatusCard(
            title = "Состояние дня",
            value = uiState.status.title(),
            body = "Грязный доход: ${money(uiState.grossIncome)}. Расходы: ${money(uiState.expensesAmount)}. Записей: ${uiState.visitsCount + uiState.officeCount + uiState.telemedCount + uiState.expensesCount}.",
        )
        DayControlRow(uiState, workActions)
        SectionHeader("Ввод работы")
        WorkFormTabs(selectedForm = selectedForm, onSelect = { selectedForm = it })
        when (selectedForm) {
            WorkForm.Visit -> VisitInputCard(
                candidate = uiState.candidate,
                clinics = uiState.clinics.all,
                onCalculate = workActions.onCalculateVisit,
                onAccept = workActions.onAcceptCandidate,
                onReject = workActions.onRejectCandidate,
            )
            WorkForm.Office -> OfficeInputCard(uiState.clinics.all, workActions.onAddOffice)
            WorkForm.Telemed -> TelemedInputCard(uiState.clinics.telemed, workActions.onAddTelemed)
            WorkForm.Expense -> ExpenseInputCard(workActions.onAddExpense)
        }
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
internal fun DayControlRow(uiState: HomeVisitUiState, workActions: WorkActions) {
    val isActive = uiState.status == WorkDayStatus.Active
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        if (isActive) {
            Button(
                modifier = Modifier.weight(1f),
                onClick = workActions.onEndDay,
            ) {
                Text("Завершить день")
            }
        } else {
            Button(
                modifier = Modifier.weight(1f),
                onClick = workActions.onStartDay,
            ) {
                Text("Начать день")
            }
        }
        OutlinedButton(
            modifier = Modifier.weight(1f),
            onClick = workActions.onStartDay,
            enabled = !isActive,
        ) {
            Text("Новый день")
        }
    }
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

@Composable
internal fun VisitInputCard(
    candidate: CandidateUiState,
    clinics: List<String>,
    onCalculate: (String, Double, String, Double?, Double?) -> Unit,
    onAccept: () -> Unit,
    onReject: () -> Unit,
) {
    var address by rememberSaveable { mutableStateOf("") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    var routeKmText by rememberSaveable { mutableStateOf("") }
    var routeMinutesText by rememberSaveable { mutableStateOf("") }
    var clinic by rememberSaveable(clinics) { mutableStateOf(clinics.firstOrNull().orEmpty()) }
    val income = parseNumber(incomeText)
    val routeKm = parseNumber(routeKmText)
    val routeMinutes = parseNumber(routeMinutesText)
    val hasManualRoute = routeKm != null && routeMinutes != null

    InputCard("Выездной заказ") {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = address,
            onValueChange = { address = it },
            label = { Text("Адрес") },
            singleLine = false,
        )
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Стоимость")
        ClinicPicker(clinics = clinics, selected = clinic, onSelect = { clinic = it })
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MoneyField(
                modifier = Modifier.weight(1f),
                value = routeKmText,
                onValueChange = { routeKmText = it },
                label = "Км вручную",
            )
            MoneyField(
                modifier = Modifier.weight(1f),
                value = routeMinutesText,
                onValueChange = { routeMinutesText = it },
                label = "Мин вручную",
            )
        }
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = address.isNotBlank() && income != null && clinic.isNotBlank(),
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
            Text(if (candidate.isLoading) "Считаю..." else "Рассчитать заказ")
        }
        CandidateResultCard(candidate = candidate, onAccept = onAccept, onReject = onReject)
    }
}

@Composable
internal fun CandidateResultCard(candidate: CandidateUiState, onAccept: () -> Unit, onReject: () -> Unit) {
    val estimate = candidate.estimate
    if (candidate.message.isBlank() && estimate == null && !candidate.isLoading) {
        return
    }
    val verdict = estimate?.let { verdictStyleFor(it.decision) }
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = verdict?.container ?: MaterialTheme.colorScheme.surfaceContainerLow,
        ),
        border = verdict?.let { BorderStroke(1.5.dp, it.accent) },
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (candidate.message.isNotBlank()) {
                Text(candidate.message, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
            }
            if (candidate.needsManualRoute) {
                Text(
                    "Заполните поля `Км вручную` и `Мин вручную`, затем нажмите `Рассчитать заказ` ещё раз.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (estimate != null && verdict != null) {
                Text(
                    estimate.decision,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = verdict.onContainer,
                )
                if (estimate.reason.isNotBlank()) {
                    Text(estimate.reason, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                // Главное число — крупно, моно, ведёт вёрстку.
                Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        money(estimate.afterHourly),
                        fontFamily = JetBrainsMono,
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    Text(
                        "/ч чистыми",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(bottom = 4.dp),
                    )
                }
                Text(
                    "Было ${money(estimate.beforeHourly)}/ч · маржинально ${money(estimate.marginalHourly)}/ч",
                    style = MaterialTheme.typography.bodySmall,
                    fontFamily = JetBrainsMono,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    "Добавится ${oneDecimal(estimate.extraKm)} км · ${oneDecimal(estimate.extraDriveMinutes)} мин · минимум ${money(estimate.requiredCandidateIncome)} · надбавка ${money(estimate.requiredExtraPayment)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (estimate.fatigueExtraPayment > 0 || estimate.fatigueLevel.isNotBlank()) {
                    Text(
                        "Нагрузка: ${estimate.fatigueLevel.ifBlank { "без отдельного уровня" }}, надбавка ${money(estimate.fatigueExtraPayment)}.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = verdict.accent),
                        enabled = !candidate.isLoading,
                        onClick = onAccept,
                    ) {
                        Text("Взять заказ")
                    }
                    OutlinedButton(
                        modifier = Modifier.weight(1f),
                        enabled = !candidate.isLoading,
                        onClick = onReject,
                    ) {
                        Text("Отклонить")
                    }
                }
            }
        }
    }
}

@Composable
internal fun OfficeInputCard(clinics: List<String>, onSubmit: (String, Double, Double, String) -> Unit) {
    var address by rememberSaveable { mutableStateOf("") }
    var minutesText by rememberSaveable { mutableStateOf("") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    var clinic by rememberSaveable(clinics) { mutableStateOf(clinics.firstOrNull().orEmpty()) }
    val minutes = parseNumber(minutesText)
    val income = parseNumber(incomeText)

    InputCard("На точке") {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = address,
            onValueChange = { address = it },
            label = { Text("Адрес предприятия") },
            singleLine = false,
        )
        MoneyField(value = minutesText, onValueChange = { minutesText = it }, label = "Продолжительность, мин")
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Стоимость")
        ClinicPicker(clinics = clinics, selected = clinic, onSelect = { clinic = it })
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = address.isNotBlank() && minutes != null && income != null && clinic.isNotBlank(),
            onClick = {
                onSubmit(address, minutes ?: 0.0, income ?: 0.0, clinic)
                address = ""
                minutesText = ""
                incomeText = ""
            },
        ) {
            Text("Сохранить заказ на точке")
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

@Composable
internal fun ExpenseInputCard(onSubmit: (ExpenseCategory, Double, String) -> Unit) {
    var category by rememberSaveable { mutableStateOf(ExpenseCategory.Meal) }
    var amountText by rememberSaveable { mutableStateOf("") }
    var comment by rememberSaveable { mutableStateOf("") }
    val amount = parseNumber(amountText)

    InputCard("Расход") {
        OptionGrid(
            options = ExpenseCategory.entries.toList(),
            selected = category,
            label = { it.title },
            onSelect = { category = it },
        )
        MoneyField(value = amountText, onValueChange = { amountText = it }, label = "Сумма")
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = comment,
            onValueChange = { comment = it },
            label = { Text("Комментарий") },
            singleLine = true,
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = amount != null,
            onClick = {
                onSubmit(category, amount ?: 0.0, comment)
                amountText = ""
                comment = ""
            },
        ) {
            Text("Сохранить расход")
        }
    }
}

