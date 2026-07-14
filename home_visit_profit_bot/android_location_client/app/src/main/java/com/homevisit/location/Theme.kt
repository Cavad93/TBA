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
import androidx.compose.material.icons.filled.Schedule
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

// Палитра дизайн-системы Визиторкрут: тёплая «бумага» + чернила, зелёный бренд,
// синий = маршрут/инфо. Светлая тема — источник истины DS; тёмную выводим согласованно.
internal val LightColors = lightColorScheme(
    primary = Color(0xFF12A150),            // green-500 — бренд, «стоит ехать»
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFC8EDD5),   // green-100
    onPrimaryContainer = Color(0xFF0B3E23), // green-900
    secondary = Color(0xFF0C8442),          // green-600
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFE9F8EF),  // green-50
    onSecondaryContainer = Color(0xFF0C532D),// green-800
    tertiary = Color(0xFF2F6FE0),           // blue-500 — маршрут/ссылки/инфо
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFEAF1FD),   // blue-50
    onTertiaryContainer = Color(0xFF163878), // blue-800
    error = Color(0xFFD93B3B),              // red-500 — «не стоит»
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFFDECEC),      // red-50
    onErrorContainer = Color(0xFF7C1B1B),    // red-800
    background = Color(0xFFF4F2EB),          // paper
    onBackground = Color(0xFF17160F),        // ink
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF17160F),
    onSurfaceVariant = Color(0xFF5E594F),    // neutral-600
    surfaceVariant = Color(0xFFEEEBE3),      // neutral-100
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFFFFFFF),  // карточки — белые на бумаге
    surfaceContainer = Color(0xFFF7F6F1),     // neutral-50
    surfaceContainerHigh = Color(0xFFEEEBE3), // neutral-100
    surfaceContainerHighest = Color(0xFFDEDACE), // neutral-200
    outline = Color(0xFFA39D8C),             // neutral-400
    outlineVariant = Color(0xFFDEDACE),      // neutral-200 — бордеры карточек
)

internal val DarkColors = darkColorScheme(
    primary = Color(0xFF5FCB8C),            // green-300
    onPrimary = Color(0xFF0B3E23),
    primaryContainer = Color(0xFF0C532D),   // green-800
    onPrimaryContainer = Color(0xFFC8EDD5),
    secondary = Color(0xFF5FCB8C),
    onSecondary = Color(0xFF0B3E23),
    secondaryContainer = Color(0xFF0C532D),
    onSecondaryContainer = Color(0xFFC8EDD5),
    tertiary = Color(0xFF75A0EC),           // blue-300
    onTertiary = Color(0xFF142E5C),
    tertiaryContainer = Color(0xFF163878),
    onTertiaryContainer = Color(0xFFCDDDFA),
    error = Color(0xFFEC8585),              // red-300
    onError = Color(0xFF5E1717),
    errorContainer = Color(0xFF7C1B1B),
    onErrorContainer = Color(0xFFFAD3D3),
    background = Color(0xFF100F0B),          // neutral-950 (тёплый near-black)
    onBackground = Color(0xFFEEEBE3),
    surface = Color(0xFF1B1914),             // neutral-900
    onSurface = Color(0xFFEEEBE3),
    onSurfaceVariant = Color(0xFFA39D8C),    // neutral-400
    surfaceVariant = Color(0xFF2E2B25),      // neutral-800
    surfaceContainerLowest = Color(0xFF100F0B),
    surfaceContainerLow = Color(0xFF1B1914),
    surfaceContainer = Color(0xFF2E2B25),
    surfaceContainerHigh = Color(0xFF46423A), // neutral-700
    surfaceContainerHighest = Color(0xFF46423A),
    outline = Color(0xFF7E786C),             // neutral-500
    outlineVariant = Color(0xFF46423A),
)

/** Вердикт-шкала DS (стоит/на грани/не стоит) — ядро продукта. Вне ColorScheme. */
object VerdictColors {
    val go = Color(0xFF12A150)
    val goContainer = Color(0xFFE9F8EF)
    val onGoContainer = Color(0xFF0B6A37)
    val edge = Color(0xFFF2A81E)
    val edgeContainer = Color(0xFFFEF5E4)
    val onEdgeContainer = Color(0xFF8E5B0A)
    val skip = Color(0xFFD93B3B)
    val skipContainer = Color(0xFFFDECEC)
    val onSkipContainer = Color(0xFF9C2020)

    // Синий — это дорога, а не вердикт. Кнопка «Поехали» намеренно не зелёная:
    // зелёный в приложении значит «стоит ехать», и путать его с «поехали» нельзя.
    val route = Color(0xFF2F6FE0)
    val routeContainer = Color(0xFFEAF1FD)
    val onRouteContainer = Color(0xFF18449B)
}

@Composable
internal fun HomeVisitTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        typography = AppTypography,
        content = content,
    )
}

@Composable
internal fun goodColor(percent: Int?): Color = when {
    percent == null -> MaterialTheme.colorScheme.outline
    percent >= 66 -> VerdictColors.go
    percent >= 40 -> VerdictColors.edge
    else -> VerdictColors.skip
}

@Composable
internal fun loadColor(percent: Int?): Color = when {
    percent == null -> MaterialTheme.colorScheme.outline
    percent >= 66 -> VerdictColors.skip
    percent >= 40 -> VerdictColors.edge
    else -> VerdictColors.go
}

internal data class HomeVerdictStyle(val accent: Color, val container: Color, val onContainer: Color, val phrase: String)

internal fun homeVerdictStyle(verdict: String): HomeVerdictStyle = when (verdict) {
    "skip" -> HomeVerdictStyle(VerdictColors.skip, VerdictColors.skipContainer, VerdictColors.onSkipContainer, "Ресурс на исходе")
    "edge" -> HomeVerdictStyle(VerdictColors.edge, VerdictColors.edgeContainer, VerdictColors.onEdgeContainer, "Восстановление на грани")
    else -> HomeVerdictStyle(VerdictColors.go, VerdictColors.goContainer, VerdictColors.onGoContainer, "Ты хорошо отдохнул")
}

internal fun recTone(tone: String): HomeVerdictStyle = when (tone) {
    "skip" -> HomeVerdictStyle(VerdictColors.skip, VerdictColors.skipContainer, VerdictColors.onSkipContainer, "")
    "edge" -> HomeVerdictStyle(VerdictColors.edge, VerdictColors.edgeContainer, VerdictColors.onEdgeContainer, "")
    "go" -> HomeVerdictStyle(VerdictColors.go, VerdictColors.goContainer, VerdictColors.onGoContainer, "")
    else -> HomeVerdictStyle(VerdictColors.edge, VerdictColors.edgeContainer, VerdictColors.onEdgeContainer, "")
}

internal fun recIcon(kind: String) = when (kind) {
    "recovery" -> Icons.Filled.Bolt
    "pricing" -> Icons.Filled.Bolt
    "workload" -> Icons.Filled.Schedule
    "streak" -> Icons.Filled.CheckCircle
    "planning" -> Icons.Filled.WbSunny
    else -> Icons.AutoMirrored.Filled.TrendingUp
}

/** Нейтральные словесные уровни индекса нагрузки (без «стоп-зон» и медицины). */
internal fun loadLevelWord(level: String): String = when (level) {
    "стоп-зона" -> "на пределе"
    "красная зона" -> "очень высокая"
    "перегрузка" -> "высокая"
    "повышенная нагрузка" -> "повышенная"
    "норма" -> "спокойно"
    else -> level.ifBlank { "—" }
}

internal data class VerdictStyle(val accent: Color, val container: Color, val onContainer: Color)

/** Классифицируем решение сервера в вердикт-шкалу DS (стоит / на грани / не стоит). */
internal fun verdictStyleFor(decision: String): VerdictStyle {
    val d = decision.lowercase()
    return when {
        d.contains("не стоит") || d.contains("невыгод") || d.contains("отказ") || d.contains("минус") ->
            VerdictStyle(VerdictColors.skip, VerdictColors.skipContainer, VerdictColors.onSkipContainer)
        d.contains("грани") || d.contains("осторож") || d.contains("порог") || d.contains("край") ->
            VerdictStyle(VerdictColors.edge, VerdictColors.edgeContainer, VerdictColors.onEdgeContainer)
        else ->
            VerdictStyle(VerdictColors.go, VerdictColors.goContainer, VerdictColors.onGoContainer)
    }
}

