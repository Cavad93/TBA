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
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
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
                // GPS/агрегатор вождения — по умолчанию активны: на первом запуске
                // просим разрешения, при наличии — сразу включаем трекинг. И разовый синк.
                LaunchedEffect(Unit) {
                    if (hasRequiredPermissions()) startTrackingIfReady() else requestRequiredPermissions()
                    SyncScheduler.runOnce(this@MainActivity)
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
                    onUpdateStart = viewModel::updateStart,
                    onReorderRoute = viewModel::reorderRoute,
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

    /** Тихо включает трекинг по умолчанию, если есть разрешения и учётные данные. */
    private fun startTrackingIfReady() {
        if (!hasRequiredPermissions()) return
        val serverUrl = prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL).orEmpty()
        val apiKey = prefs.getString(KEY_SESSION_TOKEN, "").orEmpty()
        if (serverUrl.isBlank() || apiKey.isBlank()) return
        val intent = Intent(this, LocationUploadService::class.java).apply {
            action = LocationUploadService.ACTION_START
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent) else startService(intent)
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
            // Разрешения получены — включаем трекинг по умолчанию.
            startTrackingIfReady()
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

internal enum class AppDestination(
    val label: String,
    val icon: ImageVector,
    val title: String,
) {
    Home("Главная", Icons.Filled.Home, "Штурвал"),
    Work("Оценка", Icons.Filled.Speed, "Оценка заказа"),
    Route("Лента", Icons.AutoMirrored.Filled.FormatListBulleted, "Лента"),
    Shift("Смена", Icons.Filled.AccountBalanceWallet, "Смена"),
    Profile("Профиль", Icons.Filled.Person, "Профиль");

    companion object {
        /** Вкладки «первого этажа» (во время смены). Штурвал (Home) — отдельный
         *  «второй этаж», в нижнем меню его нет. */
        val firstFloor: List<AppDestination> = entries.filter { it != Home }
    }
}

internal enum class WorkForm {
    Visit,
    Office,
    Telemed,
    Expense,
}

internal enum class ReportMode(val title: String) {
    Active("Активный"),
    Day("День"),
    Month("Месяц"),
    Year("Год"),
}

internal data class WorkActions(
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
    val onUpdateStart: (String) -> Unit,
    val onReorderRoute: (List<Int>) -> Unit,
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun HomeVisitApp(
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
    onUpdateStart: (String, String, String) -> Unit,
    onReorderRoute: (String, String, List<Int>) -> Unit,
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
        onUpdateStart = { address -> onUpdateStart(serverUrl, apiKey, address) },
        onReorderRoute = { ids -> onReorderRoute(serverUrl, apiKey, ids) },
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
            reportState = uiState.report,
            fatigueState = uiState.fatigue,
            workActions = workActions,
            onSync = syncNow,
            onBack = { showSettings = false },
        )
        return
    }

    // «Двухэтажный дом»: пока смена не идёт — виден только Штурвал (2-й этаж) без
    // нижнего меню; с началом смены «лифт» опускает на 1-й этаж со вкладками.
    val shiftActive = uiState.status == WorkDayStatus.Active
    // Каждый вход на 1-й этаж начинаем с «Оценить» — главного рабочего действия.
    LaunchedEffect(shiftActive) {
        if (shiftActive) selected = AppDestination.Work
    }

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
    ) {
        val wide = maxWidth >= 720.dp
        // 1-й этаж (рабочий) — выезжает снизу и уходит вниз.
        AnimatedVisibility(
            visible = shiftActive,
            enter = slideInVertically(animationSpec = tween(durationMillis = 420)) { it },
            exit = slideOutVertically(animationSpec = tween(durationMillis = 420)) { it },
        ) {
            FirstFloor(
                wide = wide,
                selected = selected,
                uiState = uiState,
                workActions = workActions,
                settingsState = settingsState,
                onSync = syncNow,
                onSelectDestination = { selected = it },
                onOpenSettings = { showSettings = true },
            )
        }
        // 2-й этаж (Штурвал) — уезжает вверх и возвращается сверху.
        AnimatedVisibility(
            visible = !shiftActive,
            enter = slideInVertically(animationSpec = tween(durationMillis = 420)) { -it },
            exit = slideOutVertically(animationSpec = tween(durationMillis = 420)) { -it },
        ) {
            SturvalFloor(
                uiState = uiState,
                workActions = workActions,
                onOpenSettings = { showSettings = true },
            )
        }
    }
}

/** 2-й этаж — полноэкранный Штурвал без нижнего меню; шестерёнка открывает настройки. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun SturvalFloor(
    uiState: HomeVisitUiState,
    workActions: WorkActions,
    onOpenSettings: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(AppDestination.Home.title) },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Настройки")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
            )
        },
    ) { padding ->
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            color = MaterialTheme.colorScheme.background,
        ) {
            HomeScreen(
                home = uiState.home,
                shiftActive = false,
                workActions = workActions,
                onOpenWork = {},
                onOpenReports = {},
            )
        }
    }
}

/** 1-й этаж — рабочее пространство со вкладками (Оценить/Лента/Смена/Профиль). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun FirstFloor(
    wide: Boolean,
    selected: AppDestination,
    uiState: HomeVisitUiState,
    workActions: WorkActions,
    settingsState: GpsSettingsState,
    onSync: () -> Unit,
    onSelectDestination: (AppDestination) -> Unit,
    onOpenSettings: () -> Unit,
) {
    if (wide) {
        Row(Modifier.fillMaxSize()) {
            AppNavigationRail(selected = selected, onSelect = onSelectDestination)
            AppScaffold(
                selected = selected,
                uiState = uiState,
                workActions = workActions,
                settingsState = settingsState,
                onSync = onSync,
                onSelectDestination = onSelectDestination,
                onOpenSettings = onOpenSettings,
                bottomBar = {},
            )
        }
    } else {
        AppScaffold(
            selected = selected,
            uiState = uiState,
            workActions = workActions,
            settingsState = settingsState,
            onSync = onSync,
            onSelectDestination = onSelectDestination,
            onOpenSettings = onOpenSettings,
            bottomBar = {
                AppNavigationBar(selected = selected, onSelect = onSelectDestination)
            },
        )
    }
}

internal enum class SettingsPage(val title: String) {
    Main("Настройки"),
    Reports("Подробные отчёты"),
    Fatigue("Нагрузка и восстановление"),
}

/** Экран настроек как оверлей (открывается шестерёнкой), с под-навигацией и «назад». */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun SettingsOverlay(
    settingsState: GpsSettingsState,
    syncState: SyncUiState,
    appSettings: AppSettingsUiState,
    reportState: ReportUiState,
    fatigueState: FatigueUiState,
    workActions: WorkActions,
    onSync: () -> Unit,
    onBack: () -> Unit,
) {
    var page by rememberSaveable { mutableStateOf(SettingsPage.Main) }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(page.title) },
                navigationIcon = {
                    IconButton(onClick = { if (page == SettingsPage.Main) onBack() else page = SettingsPage.Main }) {
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
            when (page) {
                SettingsPage.Main -> SettingsScreen(
                    settingsState, syncState, appSettings, workActions, onSync,
                    onOpenReports = { page = SettingsPage.Reports },
                    onOpenFatigue = { page = SettingsPage.Fatigue },
                )
                SettingsPage.Reports -> ReportsScreen(reportState, workActions)
                SettingsPage.Fatigue -> FatigueScreen(fatigueState, workActions)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun AppScaffold(
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
internal fun AppNavigationBar(selected: AppDestination, onSelect: (AppDestination) -> Unit) {
    NavigationBar(containerColor = MaterialTheme.colorScheme.surfaceContainer) {
        AppDestination.firstFloor.forEach { destination ->
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
internal fun AppNavigationRail(selected: AppDestination, onSelect: (AppDestination) -> Unit) {
    NavigationRail(
        modifier = Modifier.fillMaxHeight(),
        containerColor = MaterialTheme.colorScheme.surfaceContainer,
    ) {
        Spacer(Modifier.height(12.dp))
        AppDestination.firstFloor.forEach { destination ->
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
internal fun DestinationIcon(destination: AppDestination) {
    Icon(
        imageVector = destination.icon,
        contentDescription = destination.label,
    )
}

// --- Главный экран «Штурвал» -------------------------------------------------

/** Стиль вердикта состояния: цвет + короткая фраза «стоит ли впахивать». */
internal data class GpsSettingsState(
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
