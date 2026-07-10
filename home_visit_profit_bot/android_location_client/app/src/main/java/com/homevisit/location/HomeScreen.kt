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
internal fun HomeScreen(
    home: HomeUiState,
    shiftActive: Boolean,
    workActions: WorkActions,
    onOpenWork: () -> Unit,
    onOpenReports: () -> Unit,
) {
    // Тянем сводку при открытии и при смене статуса дня.
    LaunchedEffect(Unit) { workActions.onRefreshHome() }
    LaunchedEffect(shiftActive) { workActions.onRefreshHome() }

    val snapshot = home.snapshot
    var showStartSheet by rememberSaveable { mutableStateOf(false) }

    when {
        snapshot == null && home.loading -> HomeLoading()
        snapshot == null -> HomeError(onRetry = { workActions.onRefreshHome() })
        snapshot.firstRun -> HomeOnboarding(nickname = snapshot.nickname, onStart = { showStartSheet = true })
        else -> HomeDashboard(
            snapshot = snapshot,
            shiftActive = shiftActive,
            onStartShift = { showStartSheet = true },
            onOpenWork = onOpenWork,
            onOpenReports = onOpenReports,
        )
    }

    if (showStartSheet) {
        StartShiftSheet(
            startPrompt = snapshot?.startPrompt,
            onDismiss = { showStartSheet = false },
            onConfirm = { odometer, sleep, quality, breakHours ->
                workActions.onStartShift(odometer, sleep, quality, breakHours)
                showStartSheet = false
            },
        )
    }
}

@Composable
internal fun HomeLoading() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
    }
}

@Composable
internal fun HomeError(onRetry: () -> Unit) {
    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Нет связи с сервером", style = MaterialTheme.typography.titleMedium)
            Text(
                "Не удалось загрузить сводку. Проверь интернет и попробуй ещё раз.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
            Button(onClick = onRetry) { Text("Обновить") }
        }
    }
}

@Composable
internal fun HomeDashboard(
    snapshot: HomeSnapshot,
    shiftActive: Boolean,
    onStartShift: () -> Unit,
    onOpenWork: () -> Unit,
    onOpenReports: () -> Unit,
) {
    Box(Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Шапка: дата, приветствие, статус смены.
            val hello = if (snapshot.nickname.isNotBlank()) "Привет, ${snapshot.nickname}" else "Привет"
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        headerDate(snapshot.date),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(hello, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                }
                ShiftStatusPill(shiftActive)
            }
            if (snapshot.fromCache) {
                Text("Данные из кэша — обновятся при связи", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            snapshot.recovery?.let { RecoveryHeroCard(it, snapshot.debtVsPrev, snapshot.greenStreak) }

            MoneySection(snapshot, onOpenReports)

            if (snapshot.recommendations.isNotEmpty()) {
                SectionHeader("Рекомендации на сегодня")
                snapshot.recommendations.forEach { RecommendationCard(it) }
            }

            // Отступ под нижнюю кнопку, чтобы контент не прятался.
            Spacer(Modifier.height(88.dp))
        }

        // Нижняя центральная кнопка — старт/статус смены.
        Box(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(16.dp),
        ) {
            if (shiftActive) {
                Button(
                    onClick = onOpenWork,
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary),
                ) {
                    Text("Смена идёт · открыть работу", style = MaterialTheme.typography.titleMedium)
                }
            } else {
                Button(
                    onClick = onStartShift,
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
                ) {
                    Icon(Icons.Filled.PlayArrow, contentDescription = null, tint = Color.White)
                    Spacer(Modifier.width(8.dp))
                    Text("Начать смену", style = MaterialTheme.typography.titleMedium, color = Color.White)
                }
            }
        }
    }
}

/** Пилюля статуса смены в шапке: серый — не на смене, зелёный — идёт. */
@Composable
internal fun ShiftStatusPill(active: Boolean) {
    val dot = if (active) VerdictColors.go else MaterialTheme.colorScheme.onSurfaceVariant
    val text = if (active) "смена идёт" else "не на смене"
    Row(
        modifier = Modifier
            .background(MaterialTheme.colorScheme.surfaceContainerHigh, RoundedCornerShape(999.dp))
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box(Modifier.size(8.dp).background(dot, RoundedCornerShape(4.dp)))
        Text(text, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurface)
    }
}

/** «2026-07-10» → «ПЯТНИЦА, 10 ИЮЛЯ». */
@Composable
internal fun RecoveryHeroCard(recovery: HomeRecovery, debtVsPrev: Double?, streak: Int) {
    val style = homeVerdictStyle(recovery.verdict)
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = style.container),
        border = BorderStroke(1.5.dp, style.accent),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Состояние восстановления", style = MaterialTheme.typography.labelLarge, color = style.onContainer.copy(alpha = 0.8f))
            Text(style.phrase, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = style.onContainer)
            Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    oneDecimal(recovery.recoveryDebt),
                    fontFamily = JetBrainsMono,
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Text("долг восстановления", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 4.dp))
                debtVsPrev?.takeIf { it != 0.0 }?.let { delta ->
                    // Для долга: рост — плохо (красный), снижение — хорошо (зелёный).
                    val up = delta > 0
                    Text(
                        (if (up) "↑ " else "↓ ") + oneDecimal(kotlin.math.abs(delta)),
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = JetBrainsMono,
                        color = if (up) VerdictColors.skip else VerdictColors.go,
                        modifier = Modifier.padding(bottom = 4.dp),
                    )
                }
            }
            Text(
                "Индекс нагрузки: ${loadLevelWord(recovery.level)} · за неделю ${oneDecimal(recovery.weeklyAverage)}/100",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (streak >= 3) {
                Text("🟢 $streak ${dayWord(streak)} подряд в зелёной зоне", style = MaterialTheme.typography.bodyMedium, color = style.onContainer, fontWeight = FontWeight.Medium)
            }
        }
    }
}

@Composable
internal fun MoneySection(snapshot: HomeSnapshot, onOpenReports: () -> Unit) {
    SectionHeader("Деньги")
    val month = snapshot.monthMoney
    val yday = snapshot.yesterdayMoney
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
        MoneyTile(Modifier.weight(1f), "Доход за месяц", money(month.gross), "${month.days} ${dayWord(month.days)}")
        MoneyTile(Modifier.weight(1f), "Чистыми за месяц", money(month.net), null)
    }
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
        MoneyTile(Modifier.weight(1f), "₽/ч за месяц", money(month.netHourly), null)
        MoneyTile(
            Modifier.weight(1f),
            "₽/ч вчера",
            money(yday.netHourly),
            trendLabel(snapshot.hourlyVsMonth),
            trendColor(snapshot.hourlyVsMonth),
        )
    }
    TextButton(onClick = onOpenReports) { Text("Подробные отчёты →") }
}

@Composable
internal fun MoneyTile(modifier: Modifier, label: String, value: String, sub: String?, subColor: Color? = null) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(value, fontFamily = JetBrainsMono, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurface)
            sub?.let { Text(it, style = MaterialTheme.typography.bodySmall, fontFamily = JetBrainsMono, color = subColor ?: MaterialTheme.colorScheme.onSurfaceVariant) }
        }
    }
}

@Composable
internal fun RecommendationCard(rec: HomeRecommendation) {
    val tone = recTone(rec.tone)
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            // Цветная иконка-плитка по типу рекомендации.
            Box(
                Modifier
                    .size(40.dp)
                    .background(tone.container, RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(recIcon(rec.kind), contentDescription = null, tint = tone.accent, modifier = Modifier.size(22.dp))
            }
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(rec.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text(rec.text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
internal fun HomeOnboarding(nickname: String, onStart: () -> Unit) {
    Box(Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Spacer(Modifier.height(8.dp))
            Text(
                if (nickname.isNotBlank()) "Привет, $nickname 👋" else "Добро пожаловать 👋",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "Навигатор показывает, куда ехать. Визиторкрут показывает — стоит ли ехать.",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            OnboardingStep("1", "Начни смену", "Каждый рабочий день начинается с кнопки «Начать смену». Спросим только про сон — этого хватит для оценки восстановления.")
            OnboardingStep("2", "Добавляй заказы", "По каждому заказу покажем ₽/ч чистыми и вердикт: стоит ехать, на грани или не стоит.")
            OnboardingStep("3", "Следи за состоянием", "После первых смен на этом экране появятся доход за месяц, долг восстановления и персональные рекомендации.")
            Spacer(Modifier.height(72.dp))
        }
        Box(Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(16.dp)) {
            Button(
                onClick = onStart,
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
            ) {
                Text("Начать смену", style = MaterialTheme.typography.titleMedium, color = Color.White)
            }
        }
    }
}

@Composable
internal fun OnboardingStep(number: String, title: String, body: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        Box(
            Modifier.size(36.dp).background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(18.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Text(number, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onPrimaryContainer)
        }
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun StartShiftSheet(
    startPrompt: HomeStartPrompt?,
    onDismiss: () -> Unit,
    onConfirm: (Double, Double, Double, Double) -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var sleepHours by rememberSaveable { mutableStateOf(7) }
    var sleepQuality by rememberSaveable { mutableStateOf(3) } // 1 плохо / 3 норм / 5 отлично
    var odometerText by rememberSaveable {
        mutableStateOf(
            if (startPrompt?.hasLastOdometer == true) startPrompt.lastOdometer.toInt().toString() else "",
        )
    }
    val breakHours = startPrompt?.breakHours ?: 0.0
    val hasPrev = startPrompt?.prevEndedAt != null

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            Text("Начать смену", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)

            // Сон — обязательно. Степпер часов.
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Как спал этой ночью?", style = MaterialTheme.typography.titleSmall)
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedIconButton(onClick = { if (sleepHours > 0) sleepHours-- }) {
                        Icon(Icons.Filled.Remove, contentDescription = "Меньше")
                    }
                    Row(Modifier.weight(1f), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.Bottom) {
                        Text("$sleepHours", fontFamily = JetBrainsMono, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.width(6.dp))
                        Text(hoursWord(sleepHours), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 4.dp))
                    }
                    OutlinedIconButton(onClick = { if (sleepHours < 14) sleepHours++ }) {
                        Icon(Icons.Filled.Add, contentDescription = "Больше")
                    }
                }
                // Качество — три сегмента.
                val options = listOf("Плохо" to 1, "Норм" to 3, "Отлично" to 5)
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.surfaceContainerHigh, RoundedCornerShape(12.dp))
                        .padding(4.dp),
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    options.forEach { (label, value) ->
                        val active = sleepQuality == value
                        Box(
                            Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(9.dp))
                                .background(if (active) MaterialTheme.colorScheme.surface else Color.Transparent)
                                .clickable { sleepQuality = value }
                                .padding(vertical = 10.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                label,
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = if (active) FontWeight.SemiBold else FontWeight.Normal,
                                color = if (active) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }

            // Одометр — подтверждение вчерашнего значения или ввод при первом запуске.
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                OutlinedTextField(
                    value = odometerText,
                    onValueChange = { odometerText = it.filter { ch -> ch.isDigit() } },
                    label = { Text("Одометр — пробег сейчас") },
                    suffix = { Text("км") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                if (startPrompt?.hasLastOdometer == true) {
                    Text(
                        "Вчера было ${groupedInt(startPrompt.lastOdometer)} км. Столько сейчас? Поправь, если нет.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            // Перерыв — авто, синяя карточка.
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer),
            ) {
                Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Icon(Icons.Filled.Coffee, contentDescription = null, tint = MaterialTheme.colorScheme.onTertiaryContainer, modifier = Modifier.size(20.dp))
                    Text(
                        if (hasPrev) "Перерыв с прошлой смены — ${oneDecimal(breakHours)} ч. Посчитали сами по времени."
                        else "Первая смена — перерыв не считаем.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onTertiaryContainer,
                    )
                }
            }

            Button(
                onClick = {
                    val odometer = odometerText.toDoubleOrNull() ?: 0.0
                    onConfirm(odometer, sleepHours.toDouble(), sleepQuality.toDouble(), breakHours)
                },
                modifier = Modifier.fillMaxWidth().height(54.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
            ) {
                Icon(Icons.Filled.NearMe, contentDescription = null, tint = Color.White)
                Spacer(Modifier.width(8.dp))
                Text("Поехали", style = MaterialTheme.typography.titleMedium, color = Color.White)
            }
        }
    }
}

