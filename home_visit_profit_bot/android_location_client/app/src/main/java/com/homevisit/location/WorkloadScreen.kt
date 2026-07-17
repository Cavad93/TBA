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
internal fun WorkloadScreen(workloadState: WorkloadUiState, workActions: WorkActions) {
    var manualScoreText by rememberSaveable { mutableStateOf("") }
    var selectedCorrelationDays by rememberSaveable { mutableStateOf(14) }
    var selectedTrendDays by rememberSaveable { mutableStateOf(30) }
    var showAllCorrelations by rememberSaveable { mutableStateOf(false) }
    var surveyAnswersText by rememberSaveable { mutableStateOf("") }
    val snapshot = workloadState.snapshot
    val summary = snapshot?.summary
    val surveyQuestions = snapshot?.survey?.questions.orEmpty()
    val surveyAnswers = parseSurveyAnswers(surveyAnswersText, surveyQuestions.size)
    ScreenColumn {
        StatusCard(
            title = "Нагрузка",
            value = summary?.let { "${oneDecimal(it.score)} / 100" } ?: "Нет данных",
            body = summary?.let {
                "${it.level}. 7 дней: ${oneDecimal(it.weeklyAverage)}, долг восстановления: ${oneDecimal(it.overworkIndex)}, Самочувствие: ${oneDecimal(it.workloadSurveyScore)}."
            } ?: "Обновите сводку после синхронизации. Активный день считается предварительно, закрытый день берётся из статистики.",
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = !workloadState.isLoading,
            onClick = workActions.onRefreshWorkload,
        ) {
            Text(if (workloadState.isLoading) "Обновляю..." else "Обновить нагрузку")
        }
        if (workloadState.message.isNotBlank()) {
            CompactCard(title = "Статус", body = workloadState.message)
        }
        if (snapshot != null) {
            if (snapshot.fromCache) OfflineBadge()
            WorkloadSummaryCard(snapshot)
            WorkloadFeedbackCard(
                snapshot = snapshot,
                manualScoreText = manualScoreText,
                onManualScoreChange = { manualScoreText = it },
                onSubmit = workActions.onSubmitWorkloadFeedback,
            )
            SurveyCard(
                questions = surveyQuestions,
                answers = surveyAnswers,
                latestScore = snapshot.survey.latestScore,
                latestLevel = snapshot.survey.level,
                onAnswer = { index, value ->
                    surveyAnswersText = updateSurveyAnswer(surveyAnswersText, surveyQuestions.size, index, value)
                },
                onSubmit = {
                    workActions.onSubmitSurvey(surveyAnswers)
                    surveyAnswersText = ""
                },
            )
        }
        WorkloadTrendCard(
            trend = workloadState.trend,
            selectedDays = selectedTrendDays,
            onDaysChange = { selectedTrendDays = it },
            onRefresh = { workActions.onRefreshWorkloadTrend(selectedTrendDays) },
        )
        WorkloadCorrelationCard(
            report = workloadState.correlation,
            selectedDays = selectedCorrelationDays,
            showAll = showAllCorrelations,
            onDaysChange = { selectedCorrelationDays = it },
            onToggleShowAll = { showAllCorrelations = !showAllCorrelations },
            onRefresh = { workActions.onRefreshWorkloadCorrelation(selectedCorrelationDays) },
        )
    }
}

@Composable
internal fun WorkloadTrendCard(
    trend: WorkloadTrendReport?,
    selectedDays: Int,
    onDaysChange: (Int) -> Unit,
    onRefresh: () -> Unit,
) {
    InputCard("Тренд нагрузки") {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(14, 30, 60).forEach { days ->
                if (selectedDays == days) {
                    Button(modifier = Modifier.weight(1f), onClick = { onDaysChange(days) }) { Text("$days дн.") }
                } else {
                    OutlinedButton(modifier = Modifier.weight(1f), onClick = { onDaysChange(days) }) { Text("$days дн.") }
                }
            }
        }
        Button(modifier = Modifier.fillMaxWidth(), onClick = onRefresh) {
            Text("Показать тренд")
        }
        val points = trend?.points.orEmpty()
        if (points.isEmpty()) {
            Text(
                "График появится после нескольких закрытых дней. Линия — индекс нагрузки, пунктирная — 7-дневная средняя.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            if (trend?.fromCache == true) OfflineBadge()
            Text(
                "Индекс нагрузки (сплошная) и 7-дневная средняя (светлая). Точек: ${points.size}.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            WorkloadTrendChart(points)
            val last = points.last()
            ReportLine("Последний индекс", "${oneDecimal(last.score)}/100")
            ReportLine("7-дневная средняя", "${oneDecimal(last.weeklyAverage)}/100")
            ReportLine("Долг восстановления", "${oneDecimal(last.overworkIndex)}/100")
        }
    }
}

@Composable
internal fun WorkloadTrendChart(points: List<WorkloadTrendPoint>) {
    val scoreColor = MaterialTheme.colorScheme.primary
    val avgColor = MaterialTheme.colorScheme.tertiary
    val gridColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.2f)
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(160.dp)
            .padding(vertical = 8.dp),
    ) {
        val n = points.size
        val w = size.width
        val h = size.height
        fun px(i: Int): Float = if (n <= 1) w / 2f else w * i / (n - 1)
        fun py(v: Double): Float = h - (v.coerceIn(0.0, 100.0) / 100.0).toFloat() * h
        // Горизонтальная сетка 0/25/50/75/100
        listOf(0.0, 25.0, 50.0, 75.0, 100.0).forEach { level ->
            val y = py(level)
            drawLine(gridColor, Offset(0f, y), Offset(w, y), strokeWidth = 1f)
        }
        // Линия 7-дневной средней (светлее, тоньше)
        val avgPath = Path()
        points.forEachIndexed { i, p ->
            val x = px(i)
            val y = py(p.weeklyAverage)
            if (i == 0) avgPath.moveTo(x, y) else avgPath.lineTo(x, y)
        }
        drawPath(avgPath, color = avgColor, style = Stroke(width = 3f))
        // Линия индекса усталости (основная)
        val scorePath = Path()
        points.forEachIndexed { i, p ->
            val x = px(i)
            val y = py(p.score)
            if (i == 0) scorePath.moveTo(x, y) else scorePath.lineTo(x, y)
        }
        drawPath(scorePath, color = scoreColor, style = Stroke(width = 5f))
        points.forEachIndexed { i, p ->
            drawCircle(scoreColor, radius = 5f, center = Offset(px(i), py(p.score)))
        }
    }
}

@Composable
internal fun WorkloadSummaryCard(snapshot: WorkloadSnapshot) {
    val summary = snapshot.summary ?: return
    InputCard("Нагрузка и восстановление") {
        ReportMetricGrid(
            metrics = listOf(
                "Индекс" to "${oneDecimal(summary.score)}/100",
                "7 дней" to "${oneDecimal(summary.weeklyAverage)}/100",
                "Долг" to "${oneDecimal(summary.overworkIndex)}/100",
                "Самочувствие" to "${oneDecimal(summary.workloadSurveyScore)}/100",
                "Перерыв" to "${oneDecimal(summary.breakHoursBefore)} ч",
                "Работа ночью" to minutesText(summary.nightWorkMinutes),
            ),
        )
        ReportLine("Длинные остановки", summary.longStopCount.toString())
        ReportLine("Вероятные паузы", minutesText(summary.pauseMinutes))
        ReportLine("Тяжёлые GPS-заказы", summary.heavyVisitCount.toString())
        ReportLine("Источник", if (snapshot.source == "active") "Активный день" else "Последний закрытый день")
    }
}

@Composable
internal fun WorkloadFeedbackCard(
    snapshot: WorkloadSnapshot,
    manualScoreText: String,
    onManualScoreChange: (String) -> Unit,
    onSubmit: (String, Double?) -> Unit,
) {
    val summary = snapshot.summary
    InputCard("Вечерняя калибровка") {
        if (summary == null || snapshot.source != "latest_closed") {
            Text(
                "Обратную связь лучше давать после закрытия дня, когда есть финальная статистика.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            Text(
                "Оценка бота: ${oneDecimal(summary.score)}/100. Согласны?",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(modifier = Modifier.weight(1f), onClick = { onSubmit("agree", null) }) { Text("Согласен") }
                OutlinedButton(modifier = Modifier.weight(1f), onClick = { onSubmit("higher", null) }) { Text("Выше") }
                OutlinedButton(modifier = Modifier.weight(1f), onClick = { onSubmit("lower", null) }) { Text("Ниже") }
            }
            // 150 раньше молча срезалось в 100 и отправлялось — человек не узнавал,
            // что его число подменили. Вне шкалы — это отказ, а не тихий кламп.
            val manualRaw = parseNumber(manualScoreText)
            val manualOutOfRange = manualRaw != null && manualRaw > 100.0
            val manualScore = manualRaw?.takeIf { it <= 100.0 }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                MoneyField(
                    modifier = Modifier.weight(1f),
                    value = manualScoreText,
                    onValueChange = onManualScoreChange,
                    label = "Своя оценка 0-100",
                )
                Button(
                    enabled = manualScore != null,
                    onClick = { onSubmit("manual", manualScore) },
                ) {
                    Text("Сохранить")
                }
            }
            if (manualOutOfRange) {
                Text(
                    "Шкала — от 0 до 100.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            snapshot.latestFeedback?.let {
                Text(
                    "Последняя оценка: ${oneDecimal(it.userScore)}/100, ошибка ${oneDecimal(it.error)}.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
internal fun SurveyCard(
    questions: List<String>,
    answers: List<Int>,
    latestScore: Double,
    latestLevel: String,
    onAnswer: (Int, Int) -> Unit,
    onSubmit: () -> Unit,
) {
    InputCard("Самочувствие") {
        Text(
            "Последний индекс восст.: ${oneDecimal(latestScore)}/100, $latestLevel.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (questions.isEmpty()) {
            Text("Нажмите `Обновить нагрузку`, чтобы загрузить вопросы.", style = MaterialTheme.typography.bodyMedium)
        } else {
            questions.forEachIndexed { index, question ->
                Text("${index + 1}. $question", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    (0..4).forEach { value ->
                        val selected = answers.getOrNull(index) == value
                        if (selected) {
                            Button(modifier = Modifier.weight(1f), onClick = { onAnswer(index, value) }) { Text(value.toString()) }
                        } else {
                            OutlinedButton(modifier = Modifier.weight(1f), onClick = { onAnswer(index, value) }) { Text(value.toString()) }
                        }
                    }
                }
            }
            Button(
                modifier = Modifier.fillMaxWidth(),
                enabled = answers.isNotEmpty() && answers.all { it in 0..4 },
                onClick = onSubmit,
            ) {
                Text("Сохранить индекс восст.")
            }
        }
    }
}

@Composable
internal fun WorkloadCorrelationCard(
    report: WorkloadCorrelationReport?,
    selectedDays: Int,
    showAll: Boolean,
    onDaysChange: (Int) -> Unit,
    onToggleShowAll: () -> Unit,
    onRefresh: () -> Unit,
) {
    InputCard("Корреляции") {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(14, 28).forEach { days ->
                if (selectedDays == days) {
                    Button(modifier = Modifier.weight(1f), onClick = { onDaysChange(days) }) { Text("$days дней") }
                } else {
                    OutlinedButton(modifier = Modifier.weight(1f), onClick = { onDaysChange(days) }) { Text("$days дней") }
                }
            }
        }
        Button(modifier = Modifier.fillMaxWidth(), onClick = onRefresh) {
            Text("Показать корреляции")
        }
        if (report == null) {
            Text(
                "Матрица станет полезной после 2-4 недель данных по нагрузке, вождению, сну и расходам.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            if (report.fromCache) OfflineBadge()
            Text(
                "Дней: ${report.days}, строк данных: ${report.rowsUsed}. Чем ближе коэффициент к +1/-1, тем сильнее связь.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            val allCells = sortedCorrelationCells(report.cells)
            val visibleCells = if (showAll) allCells else allCells.take(8)
            visibleCells.forEach { cell ->
                CorrelationRow(cell)
            }
            if (allCells.size > 8) {
                OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = onToggleShowAll) {
                    Text(if (showAll) "Свернуть до топ-8" else "Показать все (${allCells.size})")
                }
            }
        }
    }
}

@Composable
internal fun CorrelationRow(cell: WorkloadCorrelationCell) {
    val value = cell.pearson ?: cell.spearman ?: 0.0
    ReportLine(
        "${workloadFeatureTitle(cell.feature)} -> ${workloadTargetTitle(cell.target)}",
        "${oneDecimal(value)} (${cell.n})",
    )
}

