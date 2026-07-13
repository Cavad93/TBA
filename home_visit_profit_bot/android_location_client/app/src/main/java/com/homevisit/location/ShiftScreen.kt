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
internal fun ShiftScreen(shift: ShiftUiState, onRefresh: (String) -> Unit) {
    var period by rememberSaveable { mutableStateOf("week") }
    LaunchedEffect(period) { onRefresh(period) }
    val snapshot = shift.snapshot
    when {
        snapshot == null && shift.loading -> HomeLoading()
        snapshot == null -> HomeError(onRetry = { onRefresh(period) })
        else -> Column(
            modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            ShiftEarningsCard(snapshot.today, snapshot.goal)
            PeriodSegment(period) { period = it }
            ShiftBarChart(snapshot.bars)
            if (snapshot.recent.isNotEmpty()) {
                SectionHeader("Последние")
                snapshot.recent.forEach { OrderRow(it) }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
internal fun ShiftEarningsCard(today: ShiftToday, goal: com.homevisit.location.domain.ShiftGoal) {
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("ЗАРАБОТАНО СЕГОДНЯ", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(money(today.net), fontFamily = JetBrainsMono, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold, color = VerdictColors.go)
            val daily = goal.daily
            if (daily != null && daily > 0) {
                val progress = (today.net / daily).coerceIn(0.0, 1.0).toFloat()
                LinearProgressIndicator(
                    progress = { progress },
                    modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
                    color = VerdictColors.go,
                    trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
                )
                val left = (daily - today.net).coerceAtLeast(0.0)
                Text(
                    if (left > 0) "Цель на день — ${money(daily)}. Осталось ${money(left)}." else "Цель на день выполнена — ${money(daily)}. 🎉",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else if (goal.suggested != null) {
                Text("Совет: поставь цель ~${money(goal.suggested)}/день (в настройках) — покажем прогресс.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Row(Modifier.fillMaxWidth().padding(top = 4.dp), horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                MiniStat("Выездов", today.visits.toString())
                MiniStat("Часов", oneDecimal(today.workHours))
                MiniStat("Чистыми/ч", money(today.netHourly))
            }
        }
    }
}

@Composable
internal fun MiniStat(label: String, value: String) {
    Column {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontFamily = JetBrainsMono, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
internal fun PeriodSegment(selected: String, onSelect: (String) -> Unit) {
    val options = listOf("День" to "day", "Неделя" to "week", "Месяц" to "month")
    Row(
        Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surfaceContainerHigh, RoundedCornerShape(12.dp)).padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        options.forEach { (label, value) ->
            val active = selected == value
            Box(
                Modifier.weight(1f).clip(RoundedCornerShape(9.dp))
                    .background(if (active) MaterialTheme.colorScheme.surface else Color.Transparent)
                    .clickable { onSelect(value) }.padding(vertical = 10.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(label, style = MaterialTheme.typography.labelLarge, fontWeight = if (active) FontWeight.SemiBold else FontWeight.Normal, color = if (active) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
internal fun ShiftBarChart(bars: List<ShiftBar>) {
    if (bars.isEmpty()) {
        CompactCard("Пока пусто", "Закрой первую смену — здесь появится график заработка.")
        return
    }
    val maxValue = bars.maxOf { it.value }.coerceAtLeast(1.0)
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Row(
            Modifier.fillMaxWidth().height(150.dp).padding(14.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            bars.forEach { bar ->
                val frac = (bar.value / maxValue).toFloat().coerceIn(0f, 1f)
                Column(Modifier.weight(1f).fillMaxHeight(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(shortMoney(bar.value), style = MaterialTheme.typography.labelSmall, fontFamily = JetBrainsMono, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
                    Box(
                        Modifier.fillMaxWidth().weight(1f, fill = true),
                        contentAlignment = Alignment.BottomCenter,
                    ) {
                        Box(
                            Modifier.fillMaxWidth().fillMaxHeight(frac.coerceAtLeast(0.02f))
                                .clip(RoundedCornerShape(topStart = 6.dp, topEnd = 6.dp))
                                .background(if (frac >= 0.999f) VerdictColors.go else MaterialTheme.colorScheme.primaryContainer),
                        )
                    }
                    Text(bar.label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
                }
            }
        }
    }
}

@Composable
internal fun OrderRow(order: ShiftOrder) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            VerdictPill(order.verdict)
            Text(order.label, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f), maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text("+${money(order.income)}", fontFamily = JetBrainsMono, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, color = VerdictColors.go)
        }
    }
}

@Composable
internal fun VerdictPill(verdict: String) {
    val (bg, fg, text) = when (verdict) {
        "go" -> Triple(VerdictColors.go, Color.White, "Стоит ехать")
        "edge" -> Triple(VerdictColors.edge, Color.White, "На грани")
        "skip" -> Triple(VerdictColors.skip, Color.White, "Не стоит")
        else -> Triple(MaterialTheme.colorScheme.surfaceContainerHighest, MaterialTheme.colorScheme.onSurface, "—")
    }
    Box(Modifier.background(bg, RoundedCornerShape(999.dp)).padding(horizontal = 10.dp, vertical = 5.dp)) {
        Text(text, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold, color = fg, maxLines = 1)
    }
}

/** Короткая денежная подпись для столбцов: 4820 → «4.8к». */
