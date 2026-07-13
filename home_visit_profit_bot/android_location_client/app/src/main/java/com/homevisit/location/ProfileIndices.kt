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
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.unit.sp
import com.homevisit.location.domain.DrivingWithinDay
import com.homevisit.location.domain.IndexCard
import com.homevisit.location.domain.IndexReason
import androidx.compose.material.icons.filled.LocalGasStation
import com.homevisit.location.domain.VehicleCost
import com.homevisit.location.domain.IncomeModel
import com.homevisit.location.domain.OverworkPricing
import kotlin.math.roundToInt


// Три индекса на экране Профиля.
//
// Каждый индекс — это отклонение от ЛИЧНОЙ нормы человека, а не абсолютный порог:
// двенадцать адресов — перегруз для одного и обычный вторник для другого. Поэтому под
// каждым баллом лежит объяснение «почему»: без него цифра «65 из 100» — приговор без
// суда, и верить ей никто не станет. А не веря индексу, никто не примет и главное —
// решение поднять сегодня минимальный тариф.

/** Пока смен мало, личной нормы нет, и любой индекс был бы цифрой из воздуха. */
@Composable
internal fun IndicesNotReadyCard(needMoreShifts: Int) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Индексы считаются", style = MaterialTheme.typography.titleMedium)
            Text(
                "Нужно ещё ${needMoreShifts} ${shiftWord(needMoreShifts)}. " +
                    "Пока историю не набрали, сравнивать твой день не с чем — " +
                    "а показывать цифру наугад мы не будем.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** Ради этой карточки всё и считалось: индекс, который не меняет решение, — украшение. */
@Composable
internal fun PricingCard(pricing: OverworkPricing) {
    val style = homeVerdictStyle(if (pricing.blocksOutsideZone) "skip" else "edge")
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = style.container),
        border = BorderStroke(1.5.dp, style.accent),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(
                "ЧТО ЭТО ЗНАЧИТ ДЛЯ ДЕНЕГ",
                style = MaterialTheme.typography.labelSmall,
                color = style.accent,
                letterSpacing = 0.8.sp,
            )
            Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Column {
                    Text(
                        "Обычный минимум",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        "${pricing.baseMinHourly} ₽/ч",
                        style = MaterialTheme.typography.titleMedium,
                        fontFamily = JetBrainsMono,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Icon(
                    Icons.AutoMirrored.Filled.TrendingUp,
                    contentDescription = null,
                    tint = style.accent,
                    modifier = Modifier.size(20.dp).padding(bottom = 4.dp),
                )
                Column {
                    Text("Сегодня", style = MaterialTheme.typography.bodySmall, color = style.accent)
                    Text(
                        "${pricing.effectiveMinHourly} ₽/ч",
                        style = MaterialTheme.typography.headlineSmall,
                        fontFamily = JetBrainsMono,
                        color = style.accent,
                    )
                }
            }
            Text(pricing.reason, style = MaterialTheme.typography.bodySmall)
        }
    }
}

/** Балл, уровень по матрице, совет — и раскрывающееся «почему». */
@Composable
internal fun IndexCardView(card: IndexCard) {
    var expanded by rememberSaveable(card.key) { mutableStateOf(false) }
    val style = homeVerdictStyle(card.tone)
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                IndexDial(card.score, style.accent)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(card.title, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(card.level, style = MaterialTheme.typography.titleSmall, color = style.accent)
                    Text(card.advice, style = MaterialTheme.typography.bodySmall)
                }
            }
            if (card.why.isNotEmpty()) {
                TextButton(onClick = { expanded = !expanded }, contentPadding = PaddingValues(horizontal = 4.dp, vertical = 2.dp)) {
                    Text(if (expanded) "Скрыть" else "Почему", style = MaterialTheme.typography.labelMedium)
                }
                if (expanded) {
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        card.why.forEach { reason -> IndexReasonRow(reason) }
                    }
                }
            }
        }
    }
}

@Composable
private fun IndexReasonRow(reason: IndexReason) {
    // Плюс — тянет вверх (тяжелее/лучше по смыслу индекса), минус — тянет вниз.
    val color = if (reason.points >= 0) VerdictColors.skip else VerdictColors.go
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(
            Modifier.padding(top = 6.dp).size(6.dp).clip(RoundedCornerShape(3.dp)).background(color)
        )
        Text(reason.text, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
    }
}

/** Кольцевой датчик балла: 0–100, цвет — по тону вердикта. */
@Composable
private fun IndexDial(score: Double, accent: Color) {
    val track = MaterialTheme.colorScheme.surfaceContainerHighest
    Box(Modifier.size(64.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val stroke = 7.dp.toPx()
            val inset = stroke / 2
            drawArc(
                color = track,
                startAngle = 135f,
                sweepAngle = 270f,
                useCenter = false,
                topLeft = Offset(inset, inset),
                size = Size(size.width - stroke, size.height - stroke),
                style = Stroke(width = stroke, cap = StrokeCap.Round),
            )
            drawArc(
                color = accent,
                startAngle = 135f,
                sweepAngle = 270f * (score.coerceIn(0.0, 100.0) / 100.0).toFloat(),
                useCenter = false,
                topLeft = Offset(inset, inset),
                size = Size(size.width - stroke, size.height - stroke),
                style = Stroke(width = stroke, cap = StrokeCap.Round),
            )
        }
        Text(
            "${score.roundToInt()}",
            style = MaterialTheme.typography.titleMedium,
            fontFamily = JetBrainsMono,
            color = accent,
        )
    }
}

/** «После 5-го адреса стиль вождения стал менее стабильным» — этого дневной агрегат не видел. */
@Composable
internal fun WithinDayCard(trend: DrivingWithinDay) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = VerdictColors.edgeContainer),
        border = BorderStroke(1.dp, VerdictColors.edge),
    ) {
        Row(
            Modifier.padding(14.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Filled.Bolt, contentDescription = null, tint = VerdictColors.edge, modifier = Modifier.size(20.dp))
            Text(
                trend.text,
                style = MaterialTheme.typography.bodySmall,
                color = VerdictColors.onEdgeContainer,
            )
        }
    }
}

private fun shiftWord(count: Int): String {
    val mod100 = count % 100
    val mod10 = count % 10
    return when {
        mod100 in 11..14 -> "смен"
        mod10 == 1 -> "смена"
        mod10 in 2..4 -> "смены"
        else -> "смен"
    }
}


/**
 * Сколько стоит километр — и что из этого посчитано, а что измерено.
 *
 * Считать один бензин — значит обманывать себя: машина ещё изнашивается, требует шин,
 * масла и ремонта. Коэффициент нужен ровно для этого — оценить реальную рентабельность
 * заказа. Это приблизительная модель, и мы честно её так и называем: как только человек
 * начнёт вносить расходы на машину, приложение посчитает его настоящий рубль за
 * километр и покажет, насколько таблица ошибалась.
 */
@Composable
internal fun VehicleCostCard(cost: VehicleCost) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Icon(
                    Icons.Filled.LocalGasStation,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(22.dp),
                )
                Column {
                    Text("Километр стоит", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(
                        "${oneDecimal(cost.total)} ₽",
                        style = MaterialTheme.typography.headlineSmall,
                        fontFamily = JetBrainsMono,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }

            MetricLine(
                if (cost.fuelMeasured) "Топливо (по вашим заправкам)" else "Топливо (из настроек)",
                "${oneDecimal(cost.fuelPerKm)} ₽/км",
                MaterialTheme.colorScheme.onSurfaceVariant,
            )
            MetricLine(
                if (cost.maintenanceMeasured) "Обслуживание (по вашим расходам)" else "Обслуживание (по коэффициенту)",
                "${oneDecimal(cost.maintenancePerKm)} ₽/км",
                MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Text(
                cost.explanation,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            // Самое ценное: показать, насколько таблица ошибалась.
            val measured = cost.measuredCoefficient
            if (measured != null && !cost.maintenanceMeasured) {
                MeasuredHint(
                    "Ваш реальный коэффициент за ${cost.measuredKm.roundToInt()} км — " +
                        "${oneDecimal(measured)}. В таблице стояло ${oneDecimal(cost.wearCoefficient)}."
                )
            }
            cost.measuredConsumption?.let {
                MeasuredHint("Реальный расход по вашим заправкам: ${oneDecimal(it)} л/100 км.")
            }
        }
    }
}

@Composable
private fun MeasuredHint(text: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(VerdictColors.goContainer)
            .padding(horizontal = 10.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = VerdictColors.go, modifier = Modifier.size(16.dp))
        Text(text, style = MaterialTheme.typography.bodySmall, color = VerdictColors.onGoContainer)
    }
}

/** У окладника лишний заказ не приносит денег — он только тратит топливо и время. */
@Composable
internal fun SalaryCard(income: IncomeModel, onConfirm: () -> Unit) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = VerdictColors.edgeContainer),
        border = BorderStroke(1.dp, VerdictColors.edge),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Оклад", style = MaterialTheme.typography.titleSmall, color = VerdictColors.onEdgeContainer)
            Text(
                income.confirmText,
                style = MaterialTheme.typography.bodyMedium,
                color = VerdictColors.onEdgeContainer,
            )
            Text(
                "Ваш час по окладу — ${money(income.hourlyRate)}. С этой ставкой и сравниваются заказы.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Button(onClick = onConfirm, modifier = Modifier.fillMaxWidth()) {
                Text("Всё так же")
            }
        }
    }
}
