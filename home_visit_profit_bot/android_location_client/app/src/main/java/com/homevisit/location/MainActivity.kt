// Клиники динамические: список приходит из настроек сервера (см. ClinicPicker/uiState.clinics).
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
import androidx.compose.foundation.Canvas
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
import androidx.compose.ui.graphics.drawscope.Stroke
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

class MainActivity : ComponentActivity() {
    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        OrderSource.current = OrderSource.byKey(prefs.getString(KEY_ORDER_SOURCE, null))
        SyncScheduler.schedule(this)
        setContent {
            HomeVisitTheme {
                var sessionToken by rememberSaveable {
                    mutableStateOf(prefs.getString(KEY_SESSION_TOKEN, "").orEmpty())
                }
                if (sessionToken.isBlank()) {
                    val authViewModel: AuthViewModel = viewModel()
                    authViewModel.serverUrl = DEFAULT_SERVER_URL
                    AuthFlow(
                        viewModel = authViewModel,
                        onAuthenticated = { token, user ->
                            persistSession(token, user)
                            sessionToken = token
                        },
                    )
                } else {
                val viewModel: HomeVisitViewModel = viewModel()
                val uiState by viewModel.uiState.collectAsStateWithLifecycle()
                // Персист выбранного пресета источника заказов при его смене.
                LaunchedEffect(OrderSource.current) {
                    prefs.edit().putString(KEY_ORDER_SOURCE, OrderSource.current.key).apply()
                }
                HomeVisitApp(
                    uiState = uiState,
                    initialServerUrl = prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL).orEmpty(),
                    initialApiKey = sessionToken,
                    initialInterval = prefs.getInt(KEY_INTERVAL_SECONDS, 60).toString(),
                    accountEmail = prefs.getString(KEY_USER_EMAIL, "").orEmpty(),
                    accountNickname = prefs.getString(KEY_USER_NICKNAME, "").orEmpty(),
                    onLogout = { signOut(sessionToken) { sessionToken = "" } },
                    onDeleteAccount = { deleteAccountAndSignOut(sessionToken) { sessionToken = "" } },
                    onSaveSettings = ::saveSettings,
                    onStartGps = ::startTracking,
                    onStopGps = ::stopTracking,
                    onStartDay = viewModel::startDay,
                    onStartDayDetails = viewModel::startDayWithDetails,
                    onStartShift = viewModel::startShift,
                    onRefreshHome = viewModel::refreshHome,
                    onRefreshShift = viewModel::refreshShift,
                    onRefreshProfile = viewModel::refreshProfile,
                    onEndDay = viewModel::endDay,
                    onEndDayWithOdometer = viewModel::endDayWithOdometer,
                    onEndDayWithDetails = viewModel::endDayWithDetails,
                    onCalculateVisit = viewModel::calculateVisitCandidate,
                    onAcceptCandidate = viewModel::acceptCandidate,
                    onRejectCandidate = viewModel::rejectCandidate,
                    onCompleteCurrentVisit = viewModel::completeCurrentVisit,
                    onCancelCurrentVisit = viewModel::cancelCurrentVisit,
                    onRefreshRoute = viewModel::refreshRoute,
                    onUpdateFinish = viewModel::updateFinish,
                    onRefreshGpsHint = viewModel::refreshGpsHint,
                    onClassifyCurrentStop = viewModel::classifyCurrentStop,
                    onRefreshGpsEstimate = viewModel::refreshGpsEstimate,
                    onRefreshActiveReport = viewModel::refreshActiveReport,
                    onRefreshStatsReport = viewModel::refreshStatsReport,
                    onRefreshFatigue = viewModel::refreshFatigue,
                    onSubmitFatigueFeedback = viewModel::submitFatigueFeedback,
                    onRefreshFatigueCorrelation = viewModel::refreshFatigueCorrelation,
                    onRefreshFatigueTrend = viewModel::refreshFatigueTrend,
                    onSubmitCbi = viewModel::submitCbi,
                    onExportBackup = viewModel::exportBackup,
                    onBackupExportHandled = viewModel::clearBackupExport,
                    onRefreshSyncConflicts = viewModel::refreshSyncConflicts,
                    onCheckConnection = viewModel::checkConnection,
                    onClearCache = viewModel::clearCache,
                    onImportBackup = viewModel::importBackup,
                    onAddOffice = viewModel::addOffice,
                    onAddTelemed = viewModel::addTelemed,
                    onAddExpense = viewModel::addExpense,
                    onSync = viewModel::syncPending,
                    onRefreshAppSettings = viewModel::refreshAppSettings,
                    onSaveAppSettings = viewModel::saveAppSettings,
                    onRefreshClinics = viewModel::refreshClinics,
                )
                }
            }
        }
    }

    private fun saveSettings(serverUrl: String, apiKey: String, intervalSecondsText: String) {
        val intervalSeconds = intervalSecondsText.toIntOrNull()?.coerceAtLeast(60) ?: 60
        prefs.edit()
            .putString(KEY_SERVER_URL, serverUrl.trim())
            .putString(KEY_API_KEY, apiKey.trim())
            .putInt(KEY_INTERVAL_SECONDS, intervalSeconds)
            .apply()
        Toast.makeText(this, "Настройки сохранены", Toast.LENGTH_SHORT).show()
    }

    private fun startTracking(serverUrl: String, apiKey: String, intervalSecondsText: String) {
        if (!hasRequiredPermissions()) {
            requestRequiredPermissions()
            return
        }
        if (serverUrl.isBlank() || apiKey.isBlank()) {
            Toast.makeText(this, "Заполните URL сервера и API ключ", Toast.LENGTH_LONG).show()
            return
        }
        saveSettings(serverUrl, apiKey, intervalSecondsText)
        val intent = Intent(this, LocationUploadService::class.java).apply {
            action = LocationUploadService.ACTION_START
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        Toast.makeText(this, "GPS и агрегаты вождения запущены", Toast.LENGTH_SHORT).show()
    }

    private fun stopTracking() {
        val intent = Intent(this, LocationUploadService::class.java).apply {
            action = LocationUploadService.ACTION_STOP
        }
        startService(intent)
        Toast.makeText(this, "Отправка GPS остановлена", Toast.LENGTH_SHORT).show()
    }

    /** Сохраняет токен сессии как Bearer для всех запросов + данные аккаунта. */
    private fun persistSession(token: String, user: AuthUser?) {
        prefs.edit()
            .putString(KEY_SESSION_TOKEN, token)
            .putString(KEY_API_KEY, token)
            .putString(KEY_SERVER_URL, DEFAULT_SERVER_URL)
            .putString(KEY_USER_EMAIL, user?.email.orEmpty())
            .putString(KEY_USER_NICKNAME, user?.nickname.orEmpty())
            .apply()
    }

    private fun clearSession() {
        prefs.edit()
            .remove(KEY_SESSION_TOKEN)
            .remove(KEY_API_KEY)
            .remove(KEY_USER_EMAIL)
            .remove(KEY_USER_NICKNAME)
            .apply()
    }

    /** Выход: гасит GPS, отзывает сессию на сервере (best-effort), чистит prefs. */
    private fun signOut(token: String, onSignedOut: () -> Unit) {
        stopTracking()
        lifecycleScope.launch {
            runCatching { HomeVisitRepository.create(applicationContext).logout(DEFAULT_SERVER_URL, token) }
            clearSession()
            onSignedOut()
        }
    }

    /** Удаление аккаунта: только при успехе на сервере чистим prefs и выходим. */
    private fun deleteAccountAndSignOut(token: String, onSignedOut: () -> Unit) {
        lifecycleScope.launch {
            val ok = runCatching {
                HomeVisitRepository.create(applicationContext).deleteAccount(DEFAULT_SERVER_URL, token)
            }.getOrDefault(false)
            if (ok) {
                stopTracking()
                clearSession()
                Toast.makeText(this@MainActivity, "Аккаунт и данные удалены", Toast.LENGTH_LONG).show()
                onSignedOut()
            } else {
                Toast.makeText(this@MainActivity, "Не удалось удалить аккаунт. Проверьте интернет.", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun hasRequiredPermissions(): Boolean {
        val locationGranted = checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val notificationsGranted = Build.VERSION.SDK_INT < 33 ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        return locationGranted && notificationsGranted
    }

    private fun requestRequiredPermissions() {
        val permissions = if (Build.VERSION.SDK_INT >= 33) {
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.POST_NOTIFICATIONS)
        } else {
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        requestPermissions(permissions, PERMISSION_REQUEST)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST && hasRequiredPermissions()) {
            Toast.makeText(this, "Разрешения выданы. Теперь можно включить GPS.", Toast.LENGTH_SHORT).show()
        } else if (requestCode == PERMISSION_REQUEST) {
            Toast.makeText(this, "Нужны разрешения на точную геолокацию и уведомление", Toast.LENGTH_LONG).show()
        }
    }

    companion object {
        const val PREFS = "location_client"
        const val KEY_SERVER_URL = "server_url"
        const val KEY_API_KEY = "api_key"
        const val KEY_INTERVAL_SECONDS = "interval_seconds"
        const val KEY_ORDER_SOURCE = "order_source"
        const val KEY_SESSION_TOKEN = "session_token"
        const val KEY_USER_EMAIL = "user_email"
        const val KEY_USER_NICKNAME = "user_nickname"
        const val DEFAULT_SERVER_URL = "https://api.vizitorkrut.ru"
        private const val PERMISSION_REQUEST = 1001
    }
}

private enum class AppDestination(
    val label: String,
    val icon: ImageVector,
    val title: String,
) {
    Home("Главная", Icons.Filled.Home, "Штурвал"),
    Work("Оценка", Icons.Filled.Speed, "Оценка заказа"),
    Route("Лента", Icons.AutoMirrored.Filled.FormatListBulleted, "Лента"),
    Shift("Смена", Icons.Filled.AccountBalanceWallet, "Смена"),
    Profile("Профиль", Icons.Filled.Person, "Профиль"),
}

private enum class WorkForm {
    Visit,
    Office,
    Telemed,
    Expense,
}

private enum class ReportMode(val title: String) {
    Active("Активный"),
    Day("День"),
    Month("Месяц"),
    Year("Год"),
}

private data class WorkActions(
    val onStartDay: () -> Unit,
    val onStartDayDetails: (String, String, Double, Double, Double, Double) -> Unit,
    val onStartShift: (Double, Double, Double, Double) -> Unit,
    val onRefreshHome: () -> Unit,
    val onRefreshShift: (String) -> Unit,
    val onRefreshProfile: () -> Unit,
    val onEndDay: () -> Unit,
    val onEndDayWithOdometer: (Double?) -> Unit,
    val onEndDayWithDetails: (EndDayDetails) -> Unit,
    val onCalculateVisit: (String, Double, String, Double?, Double?) -> Unit,
    val onAcceptCandidate: () -> Unit,
    val onRejectCandidate: () -> Unit,
    val onCompleteCurrentVisit: () -> Unit,
    val onCancelCurrentVisit: () -> Unit,
    val onRefreshRoute: () -> Unit,
    val onUpdateFinish: (String) -> Unit,
    val onRefreshGpsHint: () -> Unit,
    val onClassifyCurrentStop: (StopLabel) -> Unit,
    val onRefreshGpsEstimate: () -> Unit,
    val onRefreshActiveReport: (String?) -> Unit,
    val onRefreshStatsReport: (ReportPeriod, String?) -> Unit,
    val onRefreshFatigue: () -> Unit,
    val onSubmitFatigueFeedback: (String, Double?) -> Unit,
    val onRefreshFatigueCorrelation: (Int) -> Unit,
    val onRefreshFatigueTrend: (Int) -> Unit,
    val onSubmitCbi: (List<Int>) -> Unit,
    val onExportBackup: () -> Unit,
    val onRefreshSyncConflicts: () -> Unit,
    val onCheckConnection: () -> Unit,
    val onClearCache: () -> Unit,
    val onImportBackup: (String) -> Unit,
    val onAddOffice: (String, Double, Double, String) -> Unit,
    val onAddTelemed: (Double, Double, String) -> Unit,
    val onAddExpense: (ExpenseCategory, Double, String) -> Unit,
    val onRefreshAppSettings: () -> Unit,
    val onSaveAppSettings: (Map<String, Any?>) -> Unit,
)

// Палитра дизайн-системы Визиторкрут: тёплая «бумага» + чернила, зелёный бренд,
// синий = маршрут/инфо. Светлая тема — источник истины DS; тёмную выводим согласованно.
private val LightColors = lightColorScheme(
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

private val DarkColors = darkColorScheme(
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
}

@Composable
private fun HomeVisitTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        typography = AppTypography,
        content = content,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun HomeVisitApp(
    uiState: HomeVisitUiState,
    initialServerUrl: String,
    initialApiKey: String,
    initialInterval: String,
    accountEmail: String,
    accountNickname: String,
    onLogout: () -> Unit,
    onDeleteAccount: () -> Unit,
    onSaveSettings: (String, String, String) -> Unit,
    onStartGps: (String, String, String) -> Unit,
    onStopGps: () -> Unit,
    onStartDay: () -> Unit,
    onStartDayDetails: (String, String, Double, Double, Double, Double) -> Unit,
    onStartShift: (Double, Double, Double, Double) -> Unit,
    onRefreshHome: (String, String) -> Unit,
    onRefreshShift: (String, String, String) -> Unit,
    onRefreshProfile: (String, String) -> Unit,
    onEndDay: () -> Unit,
    onEndDayWithOdometer: (Double?) -> Unit,
    onEndDayWithDetails: (EndDayDetails) -> Unit,
    onCalculateVisit: (String, String, String, Double, String, Double?, Double?) -> Unit,
    onAcceptCandidate: (String, String) -> Unit,
    onRejectCandidate: (String, String) -> Unit,
    onCompleteCurrentVisit: (String, String) -> Unit,
    onCancelCurrentVisit: (String, String) -> Unit,
    onRefreshRoute: (String, String) -> Unit,
    onUpdateFinish: (String, String, String) -> Unit,
    onRefreshGpsHint: (String, String) -> Unit,
    onClassifyCurrentStop: (String, String, StopLabel) -> Unit,
    onRefreshGpsEstimate: (String, String) -> Unit,
    onRefreshActiveReport: (String, String, String?) -> Unit,
    onRefreshStatsReport: (String, String, ReportPeriod, String?) -> Unit,
    onRefreshFatigue: (String, String) -> Unit,
    onSubmitFatigueFeedback: (String, String, String, Double?) -> Unit,
    onRefreshFatigueCorrelation: (String, String, Int) -> Unit,
    onRefreshFatigueTrend: (String, String, Int) -> Unit,
    onSubmitCbi: (String, String, List<Int>) -> Unit,
    onExportBackup: () -> Unit,
    onBackupExportHandled: () -> Unit,
    onRefreshSyncConflicts: (String, String) -> Unit,
    onCheckConnection: (String, String) -> Unit,
    onClearCache: () -> Unit,
    onImportBackup: (String) -> Unit,
    onAddOffice: (String, Double, Double, String) -> Unit,
    onAddTelemed: (Double, Double, String) -> Unit,
    onAddExpense: (ExpenseCategory, Double, String) -> Unit,
    onSync: (String, String) -> Unit,
    onRefreshAppSettings: (String, String) -> Unit,
    onSaveAppSettings: (String, String, Map<String, Any?>) -> Unit,
    onRefreshClinics: (String, String) -> Unit,
) {
    var selected by rememberSaveable { mutableStateOf(AppDestination.Home) }
    var showSettings by rememberSaveable { mutableStateOf(false) }
    var serverUrl by rememberSaveable { mutableStateOf(initialServerUrl) }
    var apiKey by rememberSaveable { mutableStateOf(initialApiKey) }
    var intervalSeconds by rememberSaveable { mutableStateOf(initialInterval) }
    var gpsRunning by rememberSaveable { mutableStateOf(false) }
    val context = LocalContext.current

    val settingsState = GpsSettingsState(
        serverUrl = serverUrl,
        apiKey = apiKey,
        intervalSeconds = intervalSeconds,
        accountEmail = accountEmail,
        accountNickname = accountNickname,
        onServerUrlChange = { serverUrl = it },
        onApiKeyChange = { apiKey = it },
        onIntervalChange = { intervalSeconds = it },
        onSave = { onSaveSettings(serverUrl, apiKey, intervalSeconds) },
        onStartGps = {
            onStartGps(serverUrl, apiKey, intervalSeconds)
            gpsRunning = true
        },
        onStopGps = {
            onStopGps()
            gpsRunning = false
        },
        onLogout = onLogout,
        onDeleteAccount = onDeleteAccount,
        gpsRunning = gpsRunning,
    )
    val workActions = WorkActions(
        onStartDay = onStartDay,
        onStartDayDetails = onStartDayDetails,
        onStartShift = onStartShift,
        onRefreshHome = { onRefreshHome(serverUrl, apiKey) },
        onRefreshShift = { period -> onRefreshShift(serverUrl, apiKey, period) },
        onRefreshProfile = { onRefreshProfile(serverUrl, apiKey) },
        onEndDay = onEndDay,
        onEndDayWithOdometer = onEndDayWithOdometer,
        onEndDayWithDetails = onEndDayWithDetails,
        onCalculateVisit = { address, income, clinic, routeKm, routeMinutes ->
            onCalculateVisit(serverUrl, apiKey, address, income, clinic, routeKm, routeMinutes)
        },
        onAcceptCandidate = { onAcceptCandidate(serverUrl, apiKey) },
        onRejectCandidate = { onRejectCandidate(serverUrl, apiKey) },
        onCompleteCurrentVisit = { onCompleteCurrentVisit(serverUrl, apiKey) },
        onCancelCurrentVisit = { onCancelCurrentVisit(serverUrl, apiKey) },
        onRefreshRoute = { onRefreshRoute(serverUrl, apiKey) },
        onUpdateFinish = { address -> onUpdateFinish(serverUrl, apiKey, address) },
        onRefreshGpsHint = { onRefreshGpsHint(serverUrl, apiKey) },
        onClassifyCurrentStop = { label -> onClassifyCurrentStop(serverUrl, apiKey, label) },
        onRefreshGpsEstimate = { onRefreshGpsEstimate(serverUrl, apiKey) },
        onRefreshActiveReport = { clinic -> onRefreshActiveReport(serverUrl, apiKey, clinic) },
        onRefreshStatsReport = { period, clinic -> onRefreshStatsReport(serverUrl, apiKey, period, clinic) },
        onRefreshFatigue = { onRefreshFatigue(serverUrl, apiKey) },
        onSubmitFatigueFeedback = { action, score -> onSubmitFatigueFeedback(serverUrl, apiKey, action, score) },
        onRefreshFatigueCorrelation = { days -> onRefreshFatigueCorrelation(serverUrl, apiKey, days) },
        onRefreshFatigueTrend = { days -> onRefreshFatigueTrend(serverUrl, apiKey, days) },
        onSubmitCbi = { answers -> onSubmitCbi(serverUrl, apiKey, answers) },
        onExportBackup = onExportBackup,
        onRefreshSyncConflicts = { onRefreshSyncConflicts(serverUrl, apiKey) },
        onCheckConnection = { onCheckConnection(serverUrl, apiKey) },
        onClearCache = onClearCache,
        onImportBackup = onImportBackup,
        onAddOffice = onAddOffice,
        onAddTelemed = onAddTelemed,
        onAddExpense = onAddExpense,
        onRefreshAppSettings = { onRefreshAppSettings(serverUrl, apiKey) },
        onSaveAppSettings = { values -> onSaveAppSettings(serverUrl, apiKey, values) },
    )
    val syncNow = { onSync(serverUrl, apiKey) }
    // Подтягиваем список клиник из настроек, когда есть URL и ключ (для форм).
    LaunchedEffect(serverUrl, apiKey) {
        if (serverUrl.isNotBlank() && apiKey.isNotBlank()) {
            onRefreshClinics(serverUrl, apiKey)
        }
    }
    LaunchedEffect(uiState.sync.backupJson) {
        val backup = uiState.sync.backupJson ?: return@LaunchedEffect
        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = "application/json"
            putExtra(Intent.EXTRA_SUBJECT, "home_visit_backup.json")
            putExtra(Intent.EXTRA_TEXT, backup)
        }
        context.startActivity(Intent.createChooser(shareIntent, "Экспорт резервной копии"))
        onBackupExportHandled()
    }

    if (showSettings) {
        SettingsOverlay(
            settingsState = settingsState,
            syncState = uiState.sync,
            appSettings = uiState.appSettings,
            workActions = workActions,
            onSync = syncNow,
            onBack = { showSettings = false },
        )
        return
    }

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
    ) {
        val wide = maxWidth >= 720.dp
        if (wide) {
            Row(Modifier.fillMaxSize()) {
                AppNavigationRail(selected = selected, onSelect = { selected = it })
                AppScaffold(
                    selected = selected,
                    uiState = uiState,
                    workActions = workActions,
                    settingsState = settingsState,
                    onSync = syncNow,
                    onSelectDestination = { selected = it },
                    onOpenSettings = { showSettings = true },
                    bottomBar = {},
                )
            }
        } else {
            AppScaffold(
                selected = selected,
                uiState = uiState,
                workActions = workActions,
                settingsState = settingsState,
                onSync = syncNow,
                onSelectDestination = { selected = it },
                onOpenSettings = { showSettings = true },
                bottomBar = {
                    AppNavigationBar(selected = selected, onSelect = { selected = it })
                },
            )
        }
    }
}

/** Экран настроек как оверлей (открывается шестерёнкой), с кнопкой «назад». */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SettingsOverlay(
    settingsState: GpsSettingsState,
    syncState: SyncUiState,
    appSettings: AppSettingsUiState,
    workActions: WorkActions,
    onSync: () -> Unit,
    onBack: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Настройки") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
            )
        },
    ) { padding ->
        Surface(
            modifier = Modifier.fillMaxSize().padding(padding),
            color = MaterialTheme.colorScheme.background,
        ) {
            SettingsScreen(settingsState, syncState, appSettings, workActions, onSync)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AppScaffold(
    selected: AppDestination,
    uiState: HomeVisitUiState,
    workActions: WorkActions,
    settingsState: GpsSettingsState,
    onSync: () -> Unit,
    onSelectDestination: (AppDestination) -> Unit,
    onOpenSettings: () -> Unit,
    bottomBar: @Composable () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(selected.title, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Настройки")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
            )
        },
        bottomBar = bottomBar,
    ) { padding ->
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            color = MaterialTheme.colorScheme.background,
        ) {
            when (selected) {
                AppDestination.Home -> HomeScreen(
                    home = uiState.home,
                    shiftActive = uiState.status == WorkDayStatus.Active,
                    workActions = workActions,
                    onOpenWork = { onSelectDestination(AppDestination.Work) },
                    onOpenReports = { onSelectDestination(AppDestination.Shift) },
                )
                AppDestination.Work -> WorkScreen(uiState, workActions)
                AppDestination.Route -> RouteScreen(uiState, workActions, settingsState)
                AppDestination.Shift -> ShiftScreen(uiState.shift, workActions.onRefreshShift)
                AppDestination.Profile -> ProfileScreen(
                    profile = uiState.profile,
                    onRefresh = workActions.onRefreshProfile,
                    onOpenSettings = onOpenSettings,
                    onLogout = settingsState.onLogout,
                )
            }
        }
    }
}

// ======================= Экран «Смена» (статистика) =======================

@Composable
private fun ShiftScreen(shift: ShiftUiState, onRefresh: (String) -> Unit) {
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
private fun ShiftEarningsCard(today: ShiftToday, goal: com.homevisit.location.domain.ShiftGoal) {
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
private fun MiniStat(label: String, value: String) {
    Column {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontFamily = JetBrainsMono, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun PeriodSegment(selected: String, onSelect: (String) -> Unit) {
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
private fun ShiftBarChart(bars: List<ShiftBar>) {
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
private fun OrderRow(order: ShiftOrder) {
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
private fun VerdictPill(verdict: String) {
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
private fun shortMoney(value: Double): String {
    return if (value >= 1000) String.format(Locale("ru", "RU"), "%.0fк", value / 1000) else value.toInt().toString()
}

// ======================= Экран «Профиль» (состояние) =======================

@Composable
private fun ProfileScreen(profile: ProfileUiState, onRefresh: () -> Unit, onOpenSettings: () -> Unit, onLogout: () -> Unit) {
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
private fun ProfileUserCard(nickname: String, occupation: String, days: Int?) {
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
private fun WellbeingCard(w: ProfileWellbeing) {
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
private fun WellbeingDonut(gauge: WellbeingGauge, title: String, color: Color) {
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
private fun DrivingCard(d: ProfileDriving) {
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
            MetricLine("Превышений скорости", "${oneDecimal(d.speedingPer100km)}/100 км", if (d.speedingPer100km > 1) VerdictColors.edge else MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun MetricBar(label: String, valueText: String, fraction: Float, color: Color) {
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
private fun MetricLine(label: String, valueText: String, color: Color) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(valueText, style = MaterialTheme.typography.labelMedium, fontFamily = JetBrainsMono, color = color)
    }
}

@Composable
private fun StarRow(stars: Int) {
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

private fun initials(name: String): String {
    val parts = name.trim().split(" ", ".").filter { it.isNotBlank() }
    return when {
        parts.isEmpty() -> "?"
        parts.size == 1 -> parts[0].take(1).uppercase()
        else -> (parts[0].take(1) + parts[1].take(1)).uppercase()
    }
}

private fun drivingWord(score: Double): String = when {
    score >= 8 -> "Ровный"
    score >= 6 -> "Аккуратный"
    score >= 4 -> "Средний"
    else -> "Резкий"
}

@Composable
private fun goodColor(percent: Int?): Color = when {
    percent == null -> MaterialTheme.colorScheme.outline
    percent >= 66 -> VerdictColors.go
    percent >= 40 -> VerdictColors.edge
    else -> VerdictColors.skip
}

@Composable
private fun loadColor(percent: Int?): Color = when {
    percent == null -> MaterialTheme.colorScheme.outline
    percent >= 66 -> VerdictColors.skip
    percent >= 40 -> VerdictColors.edge
    else -> VerdictColors.go
}

@Composable
private fun AppNavigationBar(selected: AppDestination, onSelect: (AppDestination) -> Unit) {
    NavigationBar(containerColor = MaterialTheme.colorScheme.surfaceContainer) {
        AppDestination.entries.forEach { destination ->
            NavigationBarItem(
                selected = selected == destination,
                onClick = { onSelect(destination) },
                icon = { DestinationIcon(destination) },
                label = { Text(destination.label, maxLines = 1) },
            )
        }
    }
}

@Composable
private fun AppNavigationRail(selected: AppDestination, onSelect: (AppDestination) -> Unit) {
    NavigationRail(
        modifier = Modifier.fillMaxHeight(),
        containerColor = MaterialTheme.colorScheme.surfaceContainer,
    ) {
        Spacer(Modifier.height(12.dp))
        AppDestination.entries.forEach { destination ->
            NavigationRailItem(
                selected = selected == destination,
                onClick = { onSelect(destination) },
                icon = { DestinationIcon(destination) },
                label = { Text(destination.label) },
            )
        }
    }
}

@Composable
private fun DestinationIcon(destination: AppDestination) {
    Icon(
        imageVector = destination.icon,
        contentDescription = destination.label,
    )
}

// --- Главный экран «Штурвал» -------------------------------------------------

/** Стиль вердикта состояния: цвет + короткая фраза «стоит ли впахивать». */
private data class HomeVerdictStyle(val accent: Color, val container: Color, val onContainer: Color, val phrase: String)

private fun homeVerdictStyle(verdict: String): HomeVerdictStyle = when (verdict) {
    "skip" -> HomeVerdictStyle(VerdictColors.skip, VerdictColors.skipContainer, VerdictColors.onSkipContainer, "Ресурс на исходе")
    "edge" -> HomeVerdictStyle(VerdictColors.edge, VerdictColors.edgeContainer, VerdictColors.onEdgeContainer, "Восстановление на грани")
    else -> HomeVerdictStyle(VerdictColors.go, VerdictColors.goContainer, VerdictColors.onGoContainer, "Ты хорошо отдохнул")
}

private fun recTone(tone: String): HomeVerdictStyle = when (tone) {
    "skip" -> HomeVerdictStyle(VerdictColors.skip, VerdictColors.skipContainer, VerdictColors.onSkipContainer, "")
    "edge" -> HomeVerdictStyle(VerdictColors.edge, VerdictColors.edgeContainer, VerdictColors.onEdgeContainer, "")
    "go" -> HomeVerdictStyle(VerdictColors.go, VerdictColors.goContainer, VerdictColors.onGoContainer, "")
    else -> HomeVerdictStyle(VerdictColors.edge, VerdictColors.edgeContainer, VerdictColors.onEdgeContainer, "")
}

@Composable
private fun HomeScreen(
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
private fun HomeLoading() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
    }
}

@Composable
private fun HomeError(onRetry: () -> Unit) {
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
private fun HomeDashboard(
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
private fun ShiftStatusPill(active: Boolean) {
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
private fun headerDate(iso: String): String {
    return try {
        val d = java.time.LocalDate.parse(iso)
        val days = arrayOf("ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ")
        val months = arrayOf("ЯНВАРЯ", "ФЕВРАЛЯ", "МАРТА", "АПРЕЛЯ", "МАЯ", "ИЮНЯ", "ИЮЛЯ", "АВГУСТА", "СЕНТЯБРЯ", "ОКТЯБРЯ", "НОЯБРЯ", "ДЕКАБРЯ")
        "${days[d.dayOfWeek.value - 1]}, ${d.dayOfMonth} ${months[d.monthValue - 1]}"
    } catch (_: Exception) {
        iso
    }
}

@Composable
private fun RecoveryHeroCard(recovery: HomeRecovery, debtVsPrev: Double?, streak: Int) {
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
private fun MoneySection(snapshot: HomeSnapshot, onOpenReports: () -> Unit) {
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
private fun MoneyTile(modifier: Modifier, label: String, value: String, sub: String?, subColor: Color? = null) {
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
private fun RecommendationCard(rec: HomeRecommendation) {
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

private fun recIcon(kind: String) = when (kind) {
    "recovery" -> Icons.Filled.Bolt
    "fatigue" -> Icons.Filled.Bedtime
    "streak" -> Icons.Filled.CheckCircle
    "planning" -> Icons.Filled.WbSunny
    else -> Icons.AutoMirrored.Filled.TrendingUp
}

/** Нейтральные словесные уровни индекса нагрузки (без «стоп-зон» и медицины). */
private fun loadLevelWord(level: String): String = when (level) {
    "стоп-зона" -> "на пределе"
    "красная зона" -> "очень высокая"
    "перегрузка" -> "высокая"
    "повышенная нагрузка" -> "повышенная"
    "норма" -> "спокойно"
    else -> level.ifBlank { "—" }
}

@Composable
private fun HomeOnboarding(nickname: String, onStart: () -> Unit) {
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
private fun OnboardingStep(number: String, title: String, body: String) {
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
private fun StartShiftSheet(
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

private fun hoursWord(n: Int): String {
    val nn = n % 100
    val d = n % 10
    return when {
        nn in 11..14 -> "часов"
        d == 1 -> "час"
        d in 2..4 -> "часа"
        else -> "часов"
    }
}

private fun trendLabel(delta: Double): String? {
    if (delta == 0.0) return null
    return (if (delta > 0) "↑ " else "↓ ") + money(kotlin.math.abs(delta)) + "/ч к среднему"
}

private fun trendColor(delta: Double): Color = if (delta >= 0) VerdictColors.go else VerdictColors.skip

private fun dayWord(count: Int): String {
    val n = kotlin.math.abs(count) % 100
    val d = n % 10
    return when {
        n in 11..14 -> "дней"
        d == 1 -> "день"
        d in 2..4 -> "дня"
        else -> "дней"
    }
}

private fun qualityWord(value: Int): String = when (value) {
    0 -> "не спал"
    1 -> "плохо"
    2 -> "так себе"
    3 -> "нормально"
    4 -> "хорошо"
    else -> "отлично"
}

@Composable
private fun TodayScreen(uiState: HomeVisitUiState, workActions: WorkActions, settingsState: GpsSettingsState, onSync: () -> Unit, onOpenWork: () -> Unit) {
    val fatigueText = uiState.fatigue.snapshot?.summary?.let { ", нагрузка ${oneDecimal(it.score)}/100" }.orEmpty()
    val syncText = if (uiState.sync.stats.pendingCount + uiState.sync.stats.failedCount > 0) {
        ", sync: ${uiState.sync.stats.pendingCount} ждут / ${uiState.sync.stats.failedCount} ошибок"
    } else {
        ", sync чисто"
    }
    ScreenColumn {
        StatusCard(
            title = "Рабочий день",
            value = uiState.status.title(),
            body = "Адресов: ${uiState.visitsCount}, на точке: ${uiState.officeCount}, удалённо: ${uiState.telemedCount}$fatigueText$syncText. Доход: ${money(uiState.grossIncome)}, чистыми после расходов: ${money(uiState.netIncome)}.",
        )
        DayDetailsCard(uiState, workActions)
        DayControlRow(uiState, workActions)
        QuickActions(onOpenWork)
        GpsControlCard(settingsState)
        SyncControlCard(
            syncState = uiState.sync,
            onSync = onSync,
            onExportBackup = workActions.onExportBackup,
            onRefreshConflicts = workActions.onRefreshSyncConflicts,
            onCheckConnection = workActions.onCheckConnection,
            onClearCache = workActions.onClearCache,
            onImportBackup = workActions.onImportBackup,
        )
        CompactCard(
            title = "Локальное сохранение",
            body = "Данные пишутся в Room на телефоне, попадают в очередь и могут отправляться на backend через кнопку синхронизации.",
        )
    }
}

@Composable
private fun DayDetailsCard(uiState: HomeVisitUiState, workActions: WorkActions) {
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
private fun EndDayDetailsCard(uiState: HomeVisitUiState, workActions: WorkActions) {
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
private fun GpsEstimateControls(state: GpsEstimateUiState, onRefresh: () -> Unit, onApply: () -> Unit) {
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
private fun WorkScreen(uiState: HomeVisitUiState, workActions: WorkActions) {
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
private fun RouteScreen(uiState: HomeVisitUiState, workActions: WorkActions, settingsState: GpsSettingsState) {
    ScreenColumn {
        GpsControlCard(settingsState)
        ActiveVisitCard(
            activeVisit = uiState.activeVisit,
            gpsHint = uiState.gpsHint,
            onRefreshGpsHint = workActions.onRefreshGpsHint,
            onComplete = workActions.onCompleteCurrentVisit,
            onCancel = workActions.onCancelCurrentVisit,
        )
        ServerRouteCard(
            route = uiState.serverRoute,
            onRefresh = workActions.onRefreshRoute,
        )
        ChangeFinishCard(
            isLoading = uiState.serverRoute.isLoading,
            onUpdateFinish = workActions.onUpdateFinish,
        )
        RouteListCard(uiState.routeVisits)
        StopClassificationCard(
            activeVisit = uiState.activeVisit,
            isLoading = uiState.serverRoute.isLoading,
            onSelect = workActions.onClassifyCurrentStop,
        )
    }
}

@Composable
private fun ChangeFinishCard(isLoading: Boolean, onUpdateFinish: (String) -> Unit) {
    var finishAddress by rememberSaveable { mutableStateOf("") }
    InputCard("Изменить финиш") {
        Text(
            "Смените конечную точку среди дня — сервер геокодирует адрес и пересчитает маршрут.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = finishAddress,
            onValueChange = { finishAddress = it },
            singleLine = true,
            label = { Text("Новый адрес финиша") },
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading && finishAddress.isNotBlank(),
            onClick = {
                onUpdateFinish(finishAddress.trim())
                finishAddress = ""
            },
        ) {
            Text("Применить финиш")
        }
    }
}

@Composable
private fun ActiveVisitCard(
    activeVisit: RouteVisitUi?,
    gpsHint: GpsHintUiState,
    onRefreshGpsHint: () -> Unit,
    onComplete: () -> Unit,
    onCancel: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Текущий адрес", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            if (activeVisit == null) {
                Text(
                    "Нет принятого адреса. После расчёта и принятия заказа он появится здесь.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                Text(activeVisit.address, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
                Text(
                    "${activeVisit.clinic}, ${money(activeVisit.income)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                GpsHintBlock(
                    gpsHint = gpsHint,
                    onRefresh = onRefreshGpsHint,
                    onComplete = onComplete,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        modifier = Modifier.weight(1f),
                        enabled = activeVisit.serverId != null,
                        onClick = onComplete,
                    ) {
                        Text("Завершить")
                    }
                    OutlinedButton(
                        modifier = Modifier.weight(1f),
                        enabled = activeVisit.serverId != null,
                        onClick = onCancel,
                    ) {
                        Text("Отменить")
                    }
                }
            }
        }
    }
}

@Composable
private fun GpsHintBlock(gpsHint: GpsHintUiState, onRefresh: () -> Unit, onComplete: () -> Unit) {
    val hint = gpsHint.hint
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (gpsHint.message.isNotBlank()) {
            Text(
                gpsHint.message,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (hint != null) {
            Text(
                "Стоянка: ${oneDecimal(hint.dwellMinutes)} мин из ${oneDecimal(hint.requiredDwellMinutes)}. Дистанция: ${oneDecimal(hint.distanceMeters)} м.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                modifier = Modifier.weight(1f),
                enabled = !gpsHint.isLoading,
                onClick = onRefresh,
            ) {
                Text(if (gpsHint.isLoading) "Проверяю" else "GPS-подсказка")
            }
            Button(
                modifier = Modifier.weight(1f),
                enabled = hint?.readyToComplete == true,
                onClick = onComplete,
            ) {
                Text("Закрыть по GPS")
            }
        }
    }
}

@Composable
private fun ServerRouteCard(route: RouteUiState, onRefresh: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Серверный маршрут", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                OutlinedButton(
                    enabled = !route.isLoading,
                    onClick = onRefresh,
                ) {
                    Text(if (route.isLoading) "Обновляю" else "Обновить")
                }
            }

            if (route.message.isNotBlank()) {
                Text(
                    route.message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            val snapshot = route.snapshot
            if (snapshot == null) {
                Text(
                    "Пока нет серверного порядка адресов. Нажмите обновить после принятия заказа.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                if (snapshot.fromCache) OfflineBadge()
                Text(
                    "Адресов: ${snapshot.visitsCount}. Всего: ${oneDecimal(snapshot.totalKm)} км, ${oneDecimal(snapshot.totalMinutes)} мин.",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                )

                if (snapshot.legs.isEmpty()) {
                    Text(
                        "Плеч маршрута пока нет.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else {
                    snapshot.legs.forEachIndexed { index, leg ->
                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(
                                "${index + 1}. ${leg.fromLabel} -> ${leg.toLabel}",
                                style = MaterialTheme.typography.bodyMedium,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                "${oneDecimal(leg.km)} км, ${oneDecimal(leg.minutes)} мин",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StopClassificationCard(activeVisit: RouteVisitUi?, isLoading: Boolean, onSelect: (StopLabel) -> Unit) {
    var selected by rememberSaveable { mutableStateOf(StopLabel.Normal) }
    InputCard("Тип GPS-остановки") {
        Text(
            "Уточнение влияет только на нагрузку и долг восстановления, экономический расчёт не меняет.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OptionGrid(
            options = StopLabel.entries.toList(),
            selected = selected,
            label = { it.title },
            enabled = activeVisit?.serverId != null && !isLoading,
            onSelect = {
                selected = it
                onSelect(it)
            },
        )
        if (activeVisit?.serverId == null) {
            Text(
                "Сначала должен быть текущий адрес, принятый через сервер.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun RouteListCard(routeVisits: List<RouteVisitUi>) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Очередь адресов", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            if (routeVisits.isEmpty()) {
                Text(
                    "Принятых адресов пока нет.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                routeVisits.forEachIndexed { index, visit ->
                    Text(
                        "${index + 1}. ${visit.address}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = if (index == 0) FontWeight.SemiBold else FontWeight.Normal,
                    )
                    Text(
                        "${visit.clinic}, ${money(visit.income)}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
private fun ReportsScreen(reportState: ReportUiState, workActions: WorkActions) {
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
private fun ClinicFilterCard(
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
private fun ReportSummaryCard(snapshot: ReportSnapshot) {
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
private fun ClinicBreakdownCard(rows: List<ClinicReportRow>) {
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
private fun ClinicReportItem(row: ClinicReportRow) {
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
private fun ExpenseBreakdownCard(summary: ReportSummary) {
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
private fun ReportMetricGrid(metrics: List<Pair<String, String>>) {
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
private fun ReportMetric(label: String, value: String, modifier: Modifier = Modifier) {
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
private fun ReportLine(label: String, value: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun FatigueScreen(fatigueState: FatigueUiState, workActions: WorkActions) {
    var manualScoreText by rememberSaveable { mutableStateOf("") }
    var selectedCorrelationDays by rememberSaveable { mutableStateOf(14) }
    var selectedTrendDays by rememberSaveable { mutableStateOf(30) }
    var showAllCorrelations by rememberSaveable { mutableStateOf(false) }
    var cbiAnswersText by rememberSaveable { mutableStateOf("") }
    val snapshot = fatigueState.snapshot
    val summary = snapshot?.summary
    val cbiQuestions = snapshot?.cbi?.questions.orEmpty()
    val cbiAnswers = parseCbiAnswers(cbiAnswersText, cbiQuestions.size)
    ScreenColumn {
        StatusCard(
            title = "Нагрузка",
            value = summary?.let { "${oneDecimal(it.score)} / 100" } ?: "Нет данных",
            body = summary?.let {
                "${it.level}. 7 дней: ${oneDecimal(it.weeklyAverage)}, долг восстановления: ${oneDecimal(it.recoveryDebt)}, Индекс восст.: ${oneDecimal(it.burnoutScore)}."
            } ?: "Обновите сводку после синхронизации. Активный день считается предварительно, закрытый день берётся из статистики.",
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = !fatigueState.isLoading,
            onClick = workActions.onRefreshFatigue,
        ) {
            Text(if (fatigueState.isLoading) "Обновляю..." else "Обновить нагрузку")
        }
        if (fatigueState.message.isNotBlank()) {
            CompactCard(title = "Статус", body = fatigueState.message)
        }
        if (snapshot != null) {
            if (snapshot.fromCache) OfflineBadge()
            FatigueSummaryCard(snapshot)
            FatigueFeedbackCard(
                snapshot = snapshot,
                manualScoreText = manualScoreText,
                onManualScoreChange = { manualScoreText = it },
                onSubmit = workActions.onSubmitFatigueFeedback,
            )
            CbiCard(
                questions = cbiQuestions,
                answers = cbiAnswers,
                latestScore = snapshot.cbi.latestScore,
                latestLevel = snapshot.cbi.level,
                onAnswer = { index, value ->
                    cbiAnswersText = updateCbiAnswer(cbiAnswersText, cbiQuestions.size, index, value)
                },
                onSubmit = {
                    workActions.onSubmitCbi(cbiAnswers)
                    cbiAnswersText = ""
                },
            )
        }
        FatigueTrendCard(
            trend = fatigueState.trend,
            selectedDays = selectedTrendDays,
            onDaysChange = { selectedTrendDays = it },
            onRefresh = { workActions.onRefreshFatigueTrend(selectedTrendDays) },
        )
        FatigueCorrelationCard(
            report = fatigueState.correlation,
            selectedDays = selectedCorrelationDays,
            showAll = showAllCorrelations,
            onDaysChange = { selectedCorrelationDays = it },
            onToggleShowAll = { showAllCorrelations = !showAllCorrelations },
            onRefresh = { workActions.onRefreshFatigueCorrelation(selectedCorrelationDays) },
        )
    }
}

@Composable
private fun FatigueTrendCard(
    trend: FatigueTrendReport?,
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
            FatigueTrendChart(points)
            val last = points.last()
            ReportLine("Последний индекс", "${oneDecimal(last.score)}/100")
            ReportLine("7-дневная средняя", "${oneDecimal(last.weeklyAverage)}/100")
            ReportLine("Долг восстановления", "${oneDecimal(last.recoveryDebt)}/100")
        }
    }
}

@Composable
private fun FatigueTrendChart(points: List<FatigueTrendPoint>) {
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
private fun FatigueSummaryCard(snapshot: FatigueSnapshot) {
    val summary = snapshot.summary ?: return
    InputCard("Нагрузка и восстановление") {
        ReportMetricGrid(
            metrics = listOf(
                "Индекс" to "${oneDecimal(summary.score)}/100",
                "7 дней" to "${oneDecimal(summary.weeklyAverage)}/100",
                "Долг" to "${oneDecimal(summary.recoveryDebt)}/100",
                "Индекс восст." to "${oneDecimal(summary.burnoutScore)}/100",
                "Сон" to "${oneDecimal(summary.sleepHours)} ч",
                "Качество" to "${oneDecimal(summary.sleepQuality)}/5",
                "Перерыв" to "${oneDecimal(summary.breakHoursBefore)} ч",
                "Циркадный риск" to minutesText(summary.circadianRiskMinutes),
            ),
        )
        ReportLine("Длинные остановки", summary.longStopCount.toString())
        ReportLine("Вероятные паузы", minutesText(summary.pauseMinutes))
        ReportLine("Тяжёлые GPS-заказы", summary.heavyVisitCount.toString())
        ReportLine("Источник", if (snapshot.source == "active") "Активный день" else "Последний закрытый день")
    }
}

@Composable
private fun FatigueFeedbackCard(
    snapshot: FatigueSnapshot,
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
            val manualScore = parseNumber(manualScoreText)?.coerceIn(0.0, 100.0)
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
private fun CbiCard(
    questions: List<String>,
    answers: List<Int>,
    latestScore: Double,
    latestLevel: String,
    onAnswer: (Int, Int) -> Unit,
    onSubmit: () -> Unit,
) {
    InputCard("Индекс восстановления") {
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
private fun FatigueCorrelationCard(
    report: FatigueCorrelationReport?,
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
private fun CorrelationRow(cell: FatigueCorrelationCell) {
    val value = cell.pearson ?: cell.spearman ?: 0.0
    ReportLine(
        "${fatigueFeatureTitle(cell.feature)} -> ${fatigueTargetTitle(cell.target)}",
        "${oneDecimal(value)} (${cell.n})",
    )
}

@Composable
private fun SettingsScreen(
    settingsState: GpsSettingsState,
    syncState: SyncUiState,
    appSettings: AppSettingsUiState,
    workActions: WorkActions,
    onSync: () -> Unit,
) {
    ScreenColumn {
        GpsSettingsCard(settingsState)
        OrderSourceCard()
        AppSettingsCard(
            appSettings = appSettings,
            onRefresh = workActions.onRefreshAppSettings,
            onSave = workActions.onSaveAppSettings,
        )
        SyncControlCard(
            syncState = syncState,
            onSync = onSync,
            onExportBackup = workActions.onExportBackup,
            onRefreshConflicts = workActions.onRefreshSyncConflicts,
            onCheckConnection = workActions.onCheckConnection,
            onClearCache = workActions.onClearCache,
            onImportBackup = workActions.onImportBackup,
            showImport = true,
        )
        CompactCard(
            title = "Что здесь важно",
            body = "Вход выполняется по вашему аккаунту — данные видны только вам. Адрес сервера подставлен автоматически и нужен для расчёта маршрутов, отчётов, нагрузки и синхронизации. Настройки экономики, авто, компаний и районов редактируются здесь и уходят на сервер.",
        )
    }
}

@Composable
private fun OrderSourceCard() {
    InputCard("Название источника заказов") {
        Text(
            "Как называть тех, от кого приходят заказы, под вашу сферу. Подписи в отчётах и формах подстроятся под выбранное слово.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OptionGrid(
            options = OrderSource.presets,
            selected = OrderSource.current,
            label = { it.nomSingle },
            onSelect = { OrderSource.current = it },
        )
    }
}

@Composable
private fun AppSettingsCard(
    appSettings: AppSettingsUiState,
    onRefresh: () -> Unit,
    onSave: (Map<String, Any?>) -> Unit,
) {
    val snapshot = appSettings.snapshot
    // Локальное редактируемое состояние, пересобирается при новой загрузке с сервера.
    val textEdits = remember(snapshot) { mutableStateMapOf<String, String>() }
    val boolEdits = remember(snapshot) { mutableStateMapOf<String, Boolean>() }
    LaunchedEffect(snapshot) {
        if (snapshot != null) {
            textEdits.clear()
            boolEdits.clear()
            snapshot.sections.forEach { section ->
                section.fields.forEach { field ->
                    when (field.type) {
                        SettingType.Bool -> boolEdits[field.key] = field.boolValue
                        SettingType.ListValue -> textEdits[field.key] = field.listValue.joinToString(", ")
                        else -> textEdits[field.key] = field.textValue
                    }
                }
            }
        }
    }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Настройки приложения", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Экономика, авто, компании, базовые районы, маршрутизация, GPS и нагрузка. Значения хранятся на сервере и применяются к расчётам.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (appSettings.message.isNotBlank()) {
                Text(appSettings.message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            if (snapshot == null) {
                Button(modifier = Modifier.fillMaxWidth(), enabled = !appSettings.isLoading, onClick = onRefresh) {
                    Text(if (appSettings.isLoading) "Загружаю..." else "Загрузить настройки")
                }
            } else {
                snapshot.sections.forEach { section ->
                    AppSettingsSection(section = section, textEdits = textEdits, boolEdits = boolEdits)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        modifier = Modifier.weight(1f),
                        enabled = !appSettings.isLoading,
                        onClick = { onSave(collectSettingsChanges(snapshot.sections, textEdits, boolEdits)) },
                    ) {
                        Text(if (appSettings.isLoading) "Сохраняю..." else "Сохранить настройки")
                    }
                    OutlinedButton(modifier = Modifier.width(132.dp), enabled = !appSettings.isLoading, onClick = onRefresh) {
                        Text("Обновить")
                    }
                }
            }
        }
    }
}

@Composable
private fun AppSettingsSection(
    section: SettingsSection,
    textEdits: MutableMap<String, String>,
    boolEdits: MutableMap<String, Boolean>,
) {
    SectionHeader(section.title)
    section.fields.forEach { field ->
        when (field.type) {
            SettingType.Bool -> {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(field.label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
                    Switch(
                        checked = boolEdits[field.key] ?: field.boolValue,
                        onCheckedChange = { boolEdits[field.key] = it },
                    )
                }
            }
            SettingType.Number -> {
                OutlinedTextField(
                    modifier = Modifier.fillMaxWidth(),
                    value = textEdits[field.key] ?: field.textValue,
                    onValueChange = { textEdits[field.key] = it },
                    singleLine = true,
                    label = { Text(field.label) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                )
            }
            SettingType.ListValue -> {
                val raw = textEdits[field.key] ?: field.listValue.joinToString(", ")
                val items = if (raw.isBlank()) emptyList() else raw.split(",").map { it.trim() }
                ListFieldEditor(
                    label = field.label,
                    items = items,
                    onItemsChange = { newItems -> textEdits[field.key] = newItems.joinToString(", ") },
                )
            }
            else -> {
                OutlinedTextField(
                    modifier = Modifier.fillMaxWidth(),
                    value = textEdits[field.key] ?: field.textValue,
                    onValueChange = { textEdits[field.key] = it },
                    singleLine = true,
                    label = { Text(field.label) },
                )
            }
        }
    }
}

@Composable
private fun ListFieldEditor(
    label: String,
    items: List<String>,
    onItemsChange: (List<String>) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
        if (items.isEmpty()) {
            Text(
                "Список пуст. Нажмите «Добавить».",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        items.forEachIndexed { index, item ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    modifier = Modifier.weight(1f),
                    value = item,
                    onValueChange = { value -> onItemsChange(items.toMutableList().also { it[index] = value }) },
                    singleLine = true,
                )
                IconButton(onClick = { onItemsChange(items.toMutableList().also { it.removeAt(index) }) }) {
                    Icon(Icons.Filled.Delete, contentDescription = "Удалить")
                }
            }
        }
        OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = { onItemsChange(items + "") }) {
            Icon(Icons.Filled.Add, contentDescription = null)
            Spacer(Modifier.width(6.dp))
            Text("Добавить")
        }
    }
}

/** Собрать только изменённые поля в payload для `/api/settings`. */
private fun collectSettingsChanges(
    sections: List<SettingsSection>,
    textEdits: Map<String, String>,
    boolEdits: Map<String, Boolean>,
): Map<String, Any?> {
    val changes = mutableMapOf<String, Any?>()
    sections.forEach { section ->
        section.fields.forEach { field ->
            when (field.type) {
                SettingType.Bool -> {
                    val edited = boolEdits[field.key] ?: field.boolValue
                    if (edited != field.boolValue) changes[field.key] = edited
                }
                SettingType.Number -> {
                    val edited = (textEdits[field.key] ?: field.textValue).trim()
                    val number = edited.replace(',', '.').toDoubleOrNull()
                    if (number != null && edited != field.textValue) changes[field.key] = number
                }
                SettingType.ListValue -> {
                    val editedRaw = textEdits[field.key] ?: field.listValue.joinToString(", ")
                    val editedList = editedRaw.split(',').map { it.trim() }.filter { it.isNotEmpty() }
                    if (editedList != field.listValue) changes[field.key] = editedList
                }
                else -> {
                    val edited = (textEdits[field.key] ?: field.textValue).trim()
                    if (edited.isNotEmpty() && edited != field.textValue) changes[field.key] = edited
                }
            }
        }
    }
    return changes
}

@Composable
private fun ScreenColumn(content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        content = content,
    )
}

@Composable
private fun QuickActions(onOpenWork: () -> Unit) {
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
private fun DayControlRow(uiState: HomeVisitUiState, workActions: WorkActions) {
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
private fun WorkFormTabs(selectedForm: WorkForm, onSelect: (WorkForm) -> Unit) {
    OptionGrid(
        options = WorkForm.entries.toList(),
        selected = selectedForm,
        label = { it.title() },
        onSelect = onSelect,
    )
}

@Composable
private fun VisitInputCard(
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

private data class VerdictStyle(val accent: Color, val container: Color, val onContainer: Color)

/** Классифицируем решение сервера в вердикт-шкалу DS (стоит / на грани / не стоит). */
private fun verdictStyleFor(decision: String): VerdictStyle {
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

@Composable
private fun CandidateResultCard(candidate: CandidateUiState, onAccept: () -> Unit, onReject: () -> Unit) {
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
private fun OfficeInputCard(clinics: List<String>, onSubmit: (String, Double, Double, String) -> Unit) {
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
private fun TelemedInputCard(clinics: List<String>, onSubmit: (Double, Double, String) -> Unit) {
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
private fun ExpenseInputCard(onSubmit: (ExpenseCategory, Double, String) -> Unit) {
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

@Composable
private fun InputCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            content()
        }
    }
}

@Composable
private fun MoneyField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        modifier = modifier.fillMaxWidth(),
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        singleLine = true,
    )
}

@Composable
private fun ClinicPicker(
    clinics: List<String>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    if (clinics.isEmpty()) {
        Text(
            "Список пуст. Добавьте ${OrderSource.current.nomPlural} в разделе «Настройки» → «Настройки приложения».",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        return
    }
    OptionGrid(
        options = clinics,
        selected = selected,
        label = { it },
        onSelect = onSelect,
    )
}

@Composable
private fun <T> OptionGrid(
    options: List<T>,
    selected: T,
    label: (T) -> String,
    enabled: Boolean = true,
    onSelect: (T) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        options.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { option ->
                    val modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                    if (option == selected) {
                        Button(modifier = modifier, enabled = enabled, onClick = { onSelect(option) }) {
                            Text(label(option), maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                    } else {
                        OutlinedButton(modifier = modifier, enabled = enabled, onClick = { onSelect(option) }) {
                            Text(label(option), maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
                if (row.size == 1) {
                    Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun ActionGrid(actions: List<Pair<String, String>>, onClick: (() -> Unit)? = null) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        actions.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { (title, body) ->
                    ActionCard(title = title, body = body, modifier = Modifier.weight(1f), onClick = onClick)
                }
                if (row.size == 1) {
                    Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun ActionCard(title: String, body: String, modifier: Modifier = Modifier, onClick: (() -> Unit)? = null) {
    Card(
        modifier = (if (onClick != null) modifier.clickable { onClick() } else modifier).height(116.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSecondaryContainer)
            Text(body, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.75f))
        }
    }
}

@Composable
private fun StatusCard(title: String, value: String, body: String) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(title, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.78f))
            Text(value, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onPrimary)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.86f))
        }
    }
}

@Composable
private fun CompactCard(title: String, body: String) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun OfflineBadge() {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.tertiaryContainer,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            "⚠ Офлайн: показаны последние сохранённые данные (нет связи с сервером).",
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Medium,
            color = MaterialTheme.colorScheme.onTertiaryContainer,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
        )
    }
}

@Composable
private fun SectionHeader(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.onBackground,
    )
}

@Composable
private fun GpsControlCard(settingsState: GpsSettingsState) {
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
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("GPS и агрегаты вождения", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(
                        if (settingsState.gpsRunning) "Отправка включена" else "Отправка выключена",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Box(
                    modifier = Modifier
                        .size(12.dp)
                        .clip(CircleShape)
                        .background(if (settingsState.gpsRunning) Color(0xFF2E7D32) else Color(0xFF9E9E9E)),
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    modifier = Modifier.weight(1f),
                    onClick = settingsState.onStartGps,
                    enabled = !settingsState.gpsRunning,
                ) {
                    Text("Запустить")
                }
                OutlinedButton(
                    modifier = Modifier.weight(1f),
                    onClick = settingsState.onStopGps,
                    enabled = settingsState.gpsRunning,
                ) {
                    Text("Остановить")
                }
            }
        }
    }
}

@Composable
private fun SyncControlCard(
    syncState: SyncUiState,
    onSync: () -> Unit,
    onExportBackup: () -> Unit,
    onRefreshConflicts: () -> Unit,
    onCheckConnection: () -> Unit,
    onClearCache: () -> Unit,
    onImportBackup: (String) -> Unit,
    showImport: Boolean = false,
) {
    var importJson by rememberSaveable { mutableStateOf("") }
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
            Text("Синхронизация", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Отправляет локальные записи из очереди на backend `/api/sync`.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            ReportMetricGrid(
                metrics = listOf(
                    "Ожидают" to syncState.stats.pendingCount.toString(),
                    "Ошибки" to syncState.stats.failedCount.toString(),
                    "Отправлено" to syncState.stats.sentCount.toString(),
                    "Всего" to syncState.stats.totalCount.toString(),
                ),
            )
            if (syncState.message.isNotBlank()) {
                Text(
                    syncState.message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(modifier = Modifier.weight(1f), onClick = onSync) {
                    Text("Синхронизировать")
                }
                OutlinedButton(modifier = Modifier.weight(1f), onClick = onExportBackup) {
                    Text("Экспорт JSON")
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(modifier = Modifier.weight(1f), onClick = onCheckConnection) {
                    Text("Проверить связь")
                }
                OutlinedButton(modifier = Modifier.weight(1f), onClick = onRefreshConflicts) {
                    Text("Журнал конфликтов")
                }
            }
            OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = onClearCache) {
                Text("Очистить кэш адресов")
            }
            Text(
                "Удаляет офлайн-копии маршрута, отчётов и нагрузки. Свежие данные подтянутся при следующем обновлении со связью.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            syncState.conflicts.take(3).forEach { conflict ->
                CompactCard(
                    title = conflict.conflictType,
                    body = "${conflict.entityType}/${conflict.clientEntityId}: ${conflict.details.orEmpty()}",
                )
            }
            if (showImport) {
                OutlinedTextField(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp),
                    value = importJson,
                    onValueChange = { importJson = it },
                    label = { Text("JSON резервной копии") },
                    singleLine = false,
                )
                Button(
                    modifier = Modifier.fillMaxWidth(),
                    enabled = importJson.isNotBlank(),
                    onClick = {
                        onImportBackup(importJson)
                        importJson = ""
                    },
                ) {
                    Text("Импортировать backup")
                }
            }
        }
    }
}

@Composable
private fun GpsSettingsCard(settingsState: GpsSettingsState) {
    var showDeleteConfirm by remember { mutableStateOf(false) }
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Аккаунт", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            if (settingsState.accountNickname.isNotBlank()) {
                Text(settingsState.accountNickname, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
            }
            if (settingsState.accountEmail.isNotBlank()) {
                Text(
                    settingsState.accountEmail,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(modifier = Modifier.weight(1f), onClick = settingsState.onLogout) {
                    Text("Выйти")
                }
                OutlinedButton(
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                    onClick = { showDeleteConfirm = true },
                ) {
                    Text("Удалить аккаунт")
                }
            }

            Text("Подключение к серверу", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = settingsState.serverUrl,
                onValueChange = settingsState.onServerUrlChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("URL сервера") },
                placeholder = { Text(MainActivity.DEFAULT_SERVER_URL) },
            )
            OutlinedTextField(
                value = settingsState.intervalSeconds,
                onValueChange = settingsState.onIntervalChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("Интервал GPS, сек") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(modifier = Modifier.weight(1f), onClick = settingsState.onSave) {
                    Text("Сохранить")
                }
                OutlinedButton(modifier = Modifier.width(132.dp), onClick = settingsState.onStartGps) {
                    Text("GPS")
                }
            }
        }
    }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text("Удалить аккаунт?") },
            text = { Text("Аккаунт и все связанные данные будут удалены безвозвратно. Это действие нельзя отменить.") },
            confirmButton = {
                TextButton(onClick = {
                    showDeleteConfirm = false
                    settingsState.onDeleteAccount()
                }) {
                    Text("Удалить", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) { Text("Отмена") }
            },
        )
    }
}

private fun WorkDayStatus.title(): String = when (this) {
    WorkDayStatus.NotStarted -> "Не начат"
    WorkDayStatus.Active -> "Активен"
    WorkDayStatus.Closed -> "Завершен"
}

private fun WorkForm.title(): String = when (this) {
    WorkForm.Visit -> "Адрес"
    WorkForm.Office -> "На точке"
    WorkForm.Telemed -> "Удалённо"
    WorkForm.Expense -> "Расход"
}

private fun money(value: Double): String {
    return String.format(Locale("ru", "RU"), "%,.0f ₽", value)
}

/** Целое с разрядами по-русски: 84120 → «84 120». */
private fun groupedInt(value: Double): String {
    return String.format(Locale("ru", "RU"), "%,d", value.toLong())
}

private fun oneDecimal(value: Double): String {
    return String.format(Locale("ru", "RU"), "%.1f", value)
}

private fun minutesText(minutes: Double): String {
    val total = minutes.toInt()
    val hours = total / 60
    val rest = total % 60
    return if (hours > 0) "${hours} ч ${rest} мин" else "${rest} мин"
}

private fun hoursInput(minutes: Double): String {
    return oneDecimal(minutes / 60.0)
}

private fun parseNumber(value: String): Double? {
    return value
        .replace(" ", "")
        .replace(',', '.')
        .toDoubleOrNull()
        ?.takeIf { it >= 0.0 }
}

private fun parseCbiAnswers(value: String, count: Int): List<Int> {
    if (count <= 0) {
        return emptyList()
    }
    val values = value.split(",").mapNotNull { it.toIntOrNull() }.toMutableList()
    while (values.size < count) {
        values.add(-1)
    }
    return values.take(count)
}

private fun updateCbiAnswer(raw: String, count: Int, index: Int, value: Int): String {
    val answers = parseCbiAnswers(raw, count).toMutableList()
    if (index in answers.indices) {
        answers[index] = value
    }
    return answers.joinToString(",")
}

private fun sortedCorrelationCells(cells: List<FatigueCorrelationCell>): List<FatigueCorrelationCell> {
    return cells
        .filter { it.n >= 3 && (it.pearson != null || it.spearman != null) }
        .sortedByDescending { kotlin.math.abs(it.pearson ?: it.spearman ?: 0.0) }
}

private fun fatigueFeatureTitle(value: String): String = when (value) {
    "aggressive_score" -> "агрессивность"
    "harsh_accel_per_100km" -> "резкие ускорения"
    "harsh_brake_per_100km" -> "резкие торможения"
    "cornering_per_100km" -> "повороты"
    "lane_change_per_100km" -> "перестроения"
    "stop_go_per_100km" -> "старт-стоп"
    "jerk_score" -> "рывки"
    "speed_variability_score" -> "разброс скорости"
    "food_per_hour" -> "еда/час"
    "meal_per_hour" -> "обед/час"
    "coffee_per_hour" -> "кофе/час"
    "drinks_per_hour" -> "напитки/час"
    "sleep_debt" -> "дефицит сна"
    else -> value
}

private fun fatigueTargetTitle(value: String): String = when (value) {
    "fatigue_score" -> "нагрузка"
    "recovery_debt" -> "долг"
    "user_fatigue_score" -> "оценка исполнителя"
    "burnout_score" -> "Индекс восст."
    else -> value
}

private data class GpsSettingsState(
    val serverUrl: String,
    val apiKey: String,
    val intervalSeconds: String,
    val accountEmail: String,
    val accountNickname: String,
    val gpsRunning: Boolean,
    val onServerUrlChange: (String) -> Unit,
    val onApiKeyChange: (String) -> Unit,
    val onIntervalChange: (String) -> Unit,
    val onSave: () -> Unit,
    val onStartGps: () -> Unit,
    val onStopGps: () -> Unit,
    val onLogout: () -> Unit,
    val onDeleteAccount: () -> Unit,
)
