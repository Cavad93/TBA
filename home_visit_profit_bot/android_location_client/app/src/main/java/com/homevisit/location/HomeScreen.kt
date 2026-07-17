@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.homevisit.location

import android.Manifest
import android.content.Intent
import android.net.Uri
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
import androidx.compose.material.icons.filled.Schedule
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
import com.homevisit.location.domain.HomeBreakeven
import com.homevisit.location.domain.HomeOsago
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
internal fun HomeScreen(
    home: HomeUiState,
    shiftActive: Boolean,
    workActions: WorkActions,
    onOpenWork: () -> Unit,
    onOpenReports: () -> Unit,
) {
    // Тянем сводку при открытии и при смене статуса дня. Один эффект, а не два:
    // LaunchedEffect(shiftActive) сам срабатывает при первом запуске, поэтому пара с
    // LaunchedEffect(Unit) давала ДВЕ параллельные загрузки — и обе приходились ровно
    // на анимацию перехода после закрытия смены, добавляя ей заметный фриз.
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
            onConfirm = { odometer, firstBreakHours ->
                workActions.onStartShift(odometer, firstBreakHours)
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

            snapshot.osago?.let { OsagoCard(it) }

            snapshot.breakeven?.let { BreakevenCard(it) }

            if (snapshot.savedSkips > 0) {
                SavedSkipsCard(snapshot.savedSkips)
            }

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
internal fun RecoveryHeroCard(recovery: HomeOverwork, debtVsPrev: Double?, streak: Int) {
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
                    oneDecimal(recovery.overworkIndex),
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

/**
 * Карточка отсчёта ОСАГО (Фаза 5). Тон заботы, без паники: за 14 дней — напоминание,
 * после истечения — прямее (езда без полиса это штрафы, уже про деньги). Кнопка
 * «Продлить» появляется, только если сервер прислал партнёрскую ссылку.
 */
@Composable
internal fun OsagoCard(osago: HomeOsago) {
    val context = LocalContext.current
    val accent = if (osago.expired) VerdictColors.skip else VerdictColors.edge
    val title = when {
        osago.expired -> "Полис ОСАГО истёк"
        osago.daysLeft == 0 -> "ОСАГО истекает сегодня"
        else -> "ОСАГО истекает через ${osago.daysLeft} ${dayWord(osago.daysLeft)}"
    }
    val subtitle = if (osago.expired) {
        "Без действующего полиса штрафуют. Стоит продлить как можно скорее."
    } else {
        "Полис действует до ${osago.expiresAt}. Напомним заранее — можно продлить спокойно."
    }
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = accent.copy(alpha = 0.10f)),
        border = BorderStroke(1.5.dp, accent),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("ОСАГО", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
            Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            osago.partnerUrl?.let { url ->
                Button(
                    onClick = {
                        runCatching {
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = accent),
                ) {
                    Text("Продлить со скидкой", color = Color.White)
                }
            }
        }
    }
}

/**
 * Точка безубыточности смены (Фаза 10.2): арендник видит момент «смена отбита» без
 * лишнего тапа. Пока обязательные расходы не покрыты — сколько ещё до нуля; как
 * покрыты — «в плюс». Блока нет, если аренда/фикс-расходы не заданы (у своего авто — 0).
 */
@Composable
internal fun BreakevenCard(breakeven: HomeBreakeven) {
    val accent = if (breakeven.isPaidOff) VerdictColors.go else VerdictColors.edge
    val title = if (breakeven.isPaidOff) {
        "Смена отбита — дальше в плюс"
    } else {
        "До нуля осталось ${money(breakeven.remainingToBreakeven)}"
    }
    val subtitle = if (breakeven.isPaidOff) {
        "Обязательные расходы смены (${money(breakeven.fixedCosts)}) покрыты. Всё сверху — чистая прибыль."
    } else {
        "Обязательные расходы ${money(breakeven.fixedCosts)}, уже покрыто ${money(breakeven.accumulatedNet)}."
    }
    val progress = if (breakeven.fixedCosts > 0) {
        (breakeven.accumulatedNet / breakeven.fixedCosts).coerceIn(0.0, 1.0).toFloat()
    } else {
        1f
    }
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = accent.copy(alpha = 0.10f)),
        border = BorderStroke(1.5.dp, accent),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Безубыточность смены", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth(),
                color = accent,
            )
            Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/**
 * «Уберёг» (Ф7.5): сколько невыгодных заказов приложение помогло НЕ взять — переменная
 * награда петли удержания. Показываем, только когда есть что показать.
 */
@Composable
internal fun SavedSkipsCard(count: Int) {
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = VerdictColors.go.copy(alpha = 0.10f)),
        border = BorderStroke(1.5.dp, VerdictColors.go),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text("Уберегли", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "$count невыгодных заказов не взято в этом месяце",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Text(
                "Приложение помогло сказать «нет» тому, что съело бы время и деньги.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
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
    onConfirm: (Double, Double) -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var odometerText by rememberSaveable {
        mutableStateOf(
            if (startPrompt?.hasLastOdometer == true) startPrompt.lastOdometer.toInt().toString() else "",
        )
    }
    // Перерыв спрашиваем ТОЛЬКО на первой смене: дальше он вычисляется от времени, когда
    // закрыли прошлую. Спрашивать у человека то, что система знает точно, — лишний вопрос
    // и повод ответить не глядя.
    var firstBreakText by rememberSaveable { mutableStateOf("") }
    val hasPrev = startPrompt?.hasPreviousShift == true

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            Text("Начать смену", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)

            if (hasPrev) {
                BreakCard(startPrompt!!)
            } else {
                FirstShiftBreakInput(value = firstBreakText, onValue = { firstBreakText = it })
                // «2,5ч» с буквой молча превращался в 0 — и перерыв «исчезал».
                if (firstBreakText.isNotBlank() && parseNumber(firstBreakText) == null) {
                    Text(
                        "Перерыв не распознан — введите число часов или очистите поле.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }

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

            Button(
                enabled = hasPrev || firstBreakText.isBlank() || parseNumber(firstBreakText) != null,
                onClick = {
                    val odometer = odometerText.toDoubleOrNull() ?: 0.0
                    // На повторных сменах перерыв считает сервер — с телефона не шлём ничего.
                    val firstBreak = if (hasPrev) 0.0 else (parseNumber(firstBreakText) ?: 0.0)
                    onConfirm(odometer, firstBreak)
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

/** Перерыв между сменами — посчитан, а не спрошен. Показываем и объясняем. */
@Composable
private fun BreakCard(prompt: HomeStartPrompt) {
    val tone = if (prompt.isShort) VerdictColors.edge else MaterialTheme.colorScheme.tertiary
    val container =
        if (prompt.isShort) VerdictColors.edgeContainer else MaterialTheme.colorScheme.tertiaryContainer
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = container),
    ) {
        Row(
            Modifier.padding(14.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Icon(Icons.Filled.Schedule, contentDescription = null, tint = tone, modifier = Modifier.size(20.dp))
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    "Перерыв между сменами — ${oneDecimal(prompt.breakHours)} ч",
                    style = MaterialTheme.typography.titleSmall,
                    color = tone,
                )
                Text(
                    prompt.explanation,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

/**
 * Первая смена — считать перерыв не от чего. Спрашиваем один раз и объясняем зачем:
 * дальше приложение будет считать его само, по времени закрытия прошлой смены.
 */
@Composable
private fun FirstShiftBreakInput(value: String, onValue: (String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(
            value = value,
            onValueChange = onValue,
            label = { Text("Сколько часов отдыхали перед сменой?") },
            suffix = { Text("ч") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
        )
        Text(
            "Спрашиваем только сейчас: это первая смена, и считать перерыв не от чего. " +
                "Дальше приложение посчитает его само — по времени, когда вы закроете смену. " +
                "Перерыв между сменами нужен, чтобы правильно учитывать режим труда и отдыха.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

