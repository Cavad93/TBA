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
import com.homevisit.location.domain.ProfileCalibration
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
internal fun ProfileScreen(
    profile: ProfileUiState,
    onRefresh: () -> Unit,
    onOpenSettings: () -> Unit,
    onConfirmIncome: () -> Unit,
    onLogout: () -> Unit,
) {
    LaunchedEffect(Unit) { onRefresh() }
    val snapshot = profile.snapshot
    when {
        snapshot == null && profile.loading -> HomeLoading()
        snapshot == null -> HomeError(onRetry = onRefresh)
        else -> Column(
            modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            ProfileUserCard(snapshot.user.nickname, snapshot.user.occupation, snapshot.user.daysInService)

            // Индексы идут первыми: это главное, ради чего человек сюда заходит.
            // Деньги за месяц он и так знает — а вот стоит ли сегодня вообще ехать,
            // и почему сегодня его минимум выше обычного, знаем только мы.
            if (snapshot.indices.hasData) {
                snapshot.pricing?.takeIf { it.changed }?.let { PricingCard(it) }

                SectionHeader("Индексы · по последней смене")
                snapshot.indices.recovery?.let { IndexCardView(it) }
                snapshot.indices.load?.let { IndexCardView(it) }
                snapshot.indices.economy?.let { IndexCardView(it) }
            } else {
                IndicesNotReadyCard(snapshot.indices.needMoreShifts)
            }

            // Оклад: подтверждение раз в месяц, одной кнопкой, без ввода.
            snapshot.income?.takeIf { it.needsConfirmation }?.let {
                SalaryCard(it, onConfirm = onConfirmIncome)
            }

            snapshot.vehicle?.let {
                SectionHeader("Машина · сколько стоит километр")
                VehicleCostCard(it)
            }

            SectionHeader("Показатели · за месяц")
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MoneyTile(Modifier.weight(1f), "Среднее на адресе", "${snapshot.month.avgOnSiteMin.toInt()} мин", null)
                MoneyTile(Modifier.weight(1f), "Среднее в пути", "${snapshot.month.avgRouteMin.toInt()} мин", null)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MoneyTile(Modifier.weight(1f), "Средний ₽/ч", money(snapshot.month.netHourly), null)
                MoneyTile(Modifier.weight(1f), "Выездов", snapshot.month.visits.toString(), null)
            }

            if (snapshot.wellbeing.hasData) {
                SectionHeader("Состояние · как ты держишься")
                WellbeingCard(snapshot.wellbeing)
            }

            snapshot.driving?.let {
                SectionHeader("Стиль вождения · по данным приложения")
                DrivingCard(it)
                it.withinDay?.let { trend -> WithinDayCard(trend) }
            }

            snapshot.calibration?.let {
                SectionHeader("Твой темп · приложение подстраивается под тебя")
                CalibrationCard(it)
            }

            Spacer(Modifier.height(4.dp))
            OutlinedButton(onClick = onOpenSettings, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Filled.Settings, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("Настройки расчёта и приложения")
            }
            TextButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) {
                Text("Выйти", color = MaterialTheme.colorScheme.error)
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
internal fun ProfileUserCard(nickname: String, occupation: String, days: Int?) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            Box(
                Modifier.size(52.dp).background(MaterialTheme.colorScheme.primary, RoundedCornerShape(26.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text(initials(nickname), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onPrimary)
            }
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(nickname.ifBlank { "Профиль" }, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                val sub = buildList {
                    if (occupation.isNotBlank()) add(occupation)
                    if (days != null) add("$days ${dayWord(days)} в деле")
                }.joinToString(" · ")
                if (sub.isNotBlank()) Text(sub, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
internal fun WellbeingCard(w: ProfileWellbeing) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                WellbeingDonut(w.recovery, "Восстановление", goodColor(w.recovery.percent))
                WellbeingDonut(w.load, "Индекс нагрузки", loadColor(w.load.percent))
                WellbeingDonut(w.reserve, "Запас сил", goodColor(w.reserve.percent))
            }
            if (w.note.isNotBlank()) {
                Text(w.note, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
internal fun WellbeingDonut(gauge: WellbeingGauge, title: String, color: Color) {
    val percent = gauge.percent ?: 0
    val track = MaterialTheme.colorScheme.surfaceContainerHighest
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Box(Modifier.size(78.dp), contentAlignment = Alignment.Center) {
            Canvas(Modifier.fillMaxSize()) {
                val stroke = 9.dp.toPx()
                val inset = stroke / 2
                val arc = androidx.compose.ui.geometry.Size(size.width - stroke, size.height - stroke)
                val topLeft = androidx.compose.ui.geometry.Offset(inset, inset)
                drawArc(color = track, startAngle = 0f, sweepAngle = 360f, useCenter = false, topLeft = topLeft, size = arc, style = Stroke(width = stroke, cap = StrokeCap.Round))
                drawArc(color = color, startAngle = -90f, sweepAngle = 360f * (percent / 100f), useCenter = false, topLeft = topLeft, size = arc, style = Stroke(width = stroke, cap = StrokeCap.Round))
            }
            Text("$percent%", fontFamily = JetBrainsMono, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        }
        Text(title, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold, maxLines = 1)
        Text(gauge.label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
    }
}

@Composable
internal fun DrivingCard(d: ProfileDriving) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.size(44.dp).background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(12.dp)), contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.Speed, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer, modifier = Modifier.size(24.dp))
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(drivingWord(d.score10), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    if (d.rating.text.isNotBlank()) Text(d.rating.text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    StarRow(d.rating.stars)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(oneDecimal(d.score10), fontFamily = JetBrainsMono, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = VerdictColors.go)
                    Text("из 10", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            MetricBar("Плавность разгона", "${d.smoothAccelPct}%", d.smoothAccelPct / 100f, VerdictColors.go)
            MetricBar("Плавность торможения", "${d.smoothBrakePct}%", d.smoothBrakePct / 100f, VerdictColors.go)
            MetricLine("Резких торможений", "${oneDecimal(d.harshBrakesPer100km)}/100 км", if (d.harshBrakesPer100km > 3) VerdictColors.edge else MaterialTheme.colorScheme.onSurfaceVariant)
            // Метрики «превышений скорости» здесь больше нет: она показывала
            // захардкоженный ноль. Чтобы знать превышение, нужен лимит дороги —
            // мы его ниоткуда не берём, а врать пользователю нельзя.
            MetricLine("Резких ускорений", "${oneDecimal(d.harshAccelPer100km)}/100 км", if (d.harshAccelPer100km > 3) VerdictColors.edge else MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/**
 * Видимое вложение (Ф7.6): личная калибровка темпа дороги. Пока смен мало — показываем
 * прогресс до личной нормы («ещё N смен»), это и есть накапливаемый вклад. Когда данных
 * хватило — крупно множитель дороги и объяснение словами, что он уже в расчётах.
 */
@Composable
internal fun CalibrationCard(c: ProfileCalibration) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            val factor = c.routeTimeFactor
            if (c.hasData && factor != null) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text("Твой темп дороги учтён", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Text(routeFactorWords(factor), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("×${oneDecimal(factor)}", fontFamily = JetBrainsMono, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = VerdictColors.go)
                        Text("по ${c.days} см.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            } else {
                val target = c.days + c.needMoreShifts
                Text("Приложение учит твой темп дороги", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(
                    "Ещё ${c.needMoreShifts} ${shiftsWord(c.needMoreShifts)} — и расчёт подстроится под то, насколько твоя дорога длиннее или короче карты. Это знание накапливается только у тебя.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                MetricBar("Собрано смен", "${c.days}/$target", if (target > 0) c.days.toFloat() / target else 0f, VerdictColors.go)
            }
        }
    }
}

private fun routeFactorWords(factor: Double): String {
    val pct = ((factor - 1.0) * 100).toInt()
    return when {
        pct >= 3 -> "Твоя дорога в среднем на $pct% дольше плана карт — уже в расчётах."
        pct <= -3 -> "Твоя дорога в среднем на ${-pct}% короче плана карт — уже в расчётах."
        else -> "Твоя дорога идёт почти ровно по плану карт."
    }
}

private fun shiftsWord(n: Int): String {
    val mod100 = n % 100
    val mod10 = n % 10
    return when {
        mod100 in 11..14 -> "смен"
        mod10 == 1 -> "смена"
        mod10 in 2..4 -> "смены"
        else -> "смен"
    }
}

@Composable
internal fun MetricBar(label: String, valueText: String, fraction: Float, color: Color) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(label, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
        LinearProgressIndicator(
            progress = { fraction.coerceIn(0f, 1f) },
            modifier = Modifier.weight(1.2f).height(6.dp).clip(RoundedCornerShape(3.dp)),
            color = color,
            trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
        )
        Text(valueText, style = MaterialTheme.typography.labelMedium, fontFamily = JetBrainsMono, modifier = Modifier.width(44.dp))
    }
}

@Composable
internal fun MetricLine(label: String, valueText: String, color: Color) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(valueText, style = MaterialTheme.typography.labelMedium, fontFamily = JetBrainsMono, color = color)
    }
}

@Composable
internal fun StarRow(stars: Int) {
    Row {
        repeat(5) { i ->
            Icon(
                if (i < stars) Icons.Filled.Star else Icons.Filled.StarBorder,
                contentDescription = null,
                tint = VerdictColors.edge,
                modifier = Modifier.size(16.dp),
            )
        }
    }
}

