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
internal fun ReportsScreen(reportState: ReportUiState, workActions: WorkActions) {
    var selectedMode by rememberSaveable { mutableStateOf(ReportMode.Active) }
    val snapshot = reportState.snapshot
    val refreshWithClinic: (String?) -> Unit = { clinic ->
        when (selectedMode) {
            ReportMode.Active -> workActions.onRefreshActiveReport(clinic)
            ReportMode.Day -> workActions.onRefreshStatsReport(ReportPeriod.Day, clinic)
            ReportMode.Month -> workActions.onRefreshStatsReport(ReportPeriod.Month, clinic)
            ReportMode.Year -> workActions.onRefreshStatsReport(ReportPeriod.Year, clinic)
        }
    }
    ScreenColumn {
        StatusCard(
            title = snapshot?.title ?: "Итоги",
            value = snapshot?.summary?.let { money(it.netHourlyIncome) + "/ч" } ?: "Выберите период",
            body = snapshot?.let {
                "Грязный доход ${money(it.summary.grossIncome)}, расходы ${money(it.summary.totalExpenses)}, чистый доход ${money(it.summary.netProfit)}."
            } ?: "Активный отчёт считает текущую смену до закрытия. День, месяц и год берут уже финализированную статистику.",
        )
        OptionGrid(
            options = ReportMode.entries.toList(),
            selected = selectedMode,
            label = { it.title },
            onSelect = { selectedMode = it },
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = !reportState.isLoading,
            // Смена периода сбрасывает фильтр по клинике на «Все».
            onClick = { refreshWithClinic(null) },
        ) {
            Text(if (reportState.isLoading) "Обновляю..." else "Обновить отчёт")
        }
        if (reportState.availableClinics.isNotEmpty()) {
            ClinicFilterCard(
                clinics = reportState.availableClinics,
                selectedClinic = reportState.selectedClinic,
                enabled = !reportState.isLoading,
                onSelect = { clinic -> refreshWithClinic(clinic) },
            )
        }
        if (reportState.message.isNotBlank()) {
            CompactCard(title = "Статус", body = reportState.message)
        }
        if (snapshot != null) {
            if (snapshot.fromCache) OfflineBadge()
            ReportSummaryCard(snapshot)
            ClinicBreakdownCard(snapshot.clinics)
            ExpenseBreakdownCard(snapshot.summary)
        }
    }
}

@Composable
internal fun ClinicFilterCard(
    clinics: List<String>,
    selectedClinic: String?,
    enabled: Boolean,
    onSelect: (String?) -> Unit,
) {
    // "Все" в списке = сброс фильтра (null). Пустая строка используется как маркер "Все".
    val allLabel = "Все"
    val options = listOf(allLabel) + clinics
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
            Text("Фильтр по ${OrderSource.current.datSingle}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OptionGrid(
                options = options,
                selected = selectedClinic ?: allLabel,
                label = { it },
                enabled = enabled,
                onSelect = { option -> onSelect(if (option == allLabel) null else option) },
            )
        }
    }
}

@Composable
internal fun ReportSummaryCard(snapshot: ReportSnapshot) {
    InputCard("Финансы и время") {
        ReportMetricGrid(
            metrics = listOf(
                "Грязный" to money(snapshot.summary.grossIncome),
                "Расходы" to money(snapshot.summary.totalExpenses),
                "Чистый" to money(snapshot.summary.netProfit),
                "Чистый/час" to "${money(snapshot.summary.netHourlyIncome)}/ч",
                "Заказы" to snapshot.summary.visitsCount.toString(),
                "Работа" to minutesText(snapshot.summary.totalWorkMinutes),
                "Дорога" to minutesText(snapshot.summary.totalRouteMinutes),
                "Км" to oneDecimal(snapshot.summary.actualKm),
            ),
        )
        ReportLine("Заказы", money(snapshot.summary.visitIncome))
        ReportLine("Удалённые заказы", money(snapshot.summary.telemedIncome))
        ReportLine("На точке", "${money(snapshot.summary.officeIncome)} / ${minutesText(snapshot.summary.officeMinutes)}")
        if (snapshot.summary.fatigueScore > 0 || snapshot.summary.recoveryDebt > 0) {
            ReportLine(
                "Нагрузка",
                "${oneDecimal(snapshot.summary.fatigueScore)}/100, долг ${oneDecimal(snapshot.summary.recoveryDebt)}",
            )
        }
    }
}

@Composable
internal fun ClinicBreakdownCard(rows: List<ClinicReportRow>) {
    InputCard("По ${OrderSource.current.datPlural}") {
        if (rows.isEmpty()) {
            Text(
                "Данных по ${OrderSource.current.datPlural} пока нет.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            rows.forEach { row ->
                ClinicReportItem(row)
            }
        }
    }
}

@Composable
internal fun ClinicReportItem(row: ClinicReportRow) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.06f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(row.clinic, modifier = Modifier.weight(1f), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text("${money(row.netHourlyIncome)}/ч", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
            }
            Text(
                "Грязный ${money(row.grossIncome)}, чистый ${money(row.netIncome)}, работа ${minutesText(row.workMinutes)}.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Заказы: ${row.visitsCount} / ${money(row.visitIncome)}. Удалённо: ${money(row.telemedIncome)}. На точке: ${money(row.officeIncome)}.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
internal fun ExpenseBreakdownCard(summary: ReportSummary) {
    InputCard("Расходы") {
        ReportLine("Топливо", money(summary.fuelExpenses))
        ReportLine("Амортизация", money(summary.amortizationExpenses))
        ReportLine("Парковка", money(summary.parkingExpenses))
        ReportLine("Еда", money(summary.foodMealExpenses + summary.foodExpenses))
        ReportLine("Кофе/энергетик", money(summary.coffeeExpenses))
        ReportLine("Вода/напитки", money(summary.drinksExpenses))
        ReportLine("Платные дороги", money(summary.tollExpenses))
        ReportLine("Прочее", money(summary.otherExpenses))
    }
}

@Composable
internal fun ReportMetricGrid(metrics: List<Pair<String, String>>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        metrics.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { metric ->
                    ReportMetric(metric.first, metric.second, Modifier.weight(1f))
                }
                if (row.size == 1) {
                    Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
internal fun ReportMetric(label: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
internal fun ReportLine(label: String, value: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}

