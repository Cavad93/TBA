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
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
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
import com.homevisit.location.domain.AddressCandidate
import com.homevisit.location.domain.ArchiveRange
import com.homevisit.location.domain.ArchiveSort
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
import com.homevisit.location.notify.ReminderScheduler
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

/** Текст из «Поделиться» (Ф15.1): только ACTION_SEND text/plain, иначе null. */
private fun extractSharedText(intent: Intent?): String? {
    if (intent?.action != Intent.ACTION_SEND || intent.type != "text/plain") return null
    return intent.getStringExtra(Intent.EXTRA_TEXT)
}

/** Картинка из «Поделиться» (Ф15.4): ACTION_SEND с mime-типом image, иначе null. */
private fun extractSharedImageUri(intent: Intent?): android.net.Uri? {
    if (intent?.action != Intent.ACTION_SEND || intent.type?.startsWith("image/") != true) return null
    @Suppress("DEPRECATION")
    return intent.getParcelableExtra(Intent.EXTRA_STREAM) as? android.net.Uri
}

class MainActivity : ComponentActivity() {
    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        OrderSource.current = OrderSource.byKey(prefs.getString(KEY_ORDER_SOURCE, null))
        SyncScheduler.schedule(this)
        // Плановые уведомления петли удержания (Ф7.1/7.2, 5.5): старт смены, закрытие дня,
        // ОСАГО. Локальный WorkManager, без FCM; отключается настройкой reminders_enabled.
        ReminderScheduler.schedule(this)
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
                            // Свежая регистрация → онбординг: спросить настройки и
                            // объяснить, зачем они (иначе советы будут по средним).
                            if (authViewModel.registrationJustCompleted) {
                                prefs.edit().putBoolean(KEY_ONBOARDING_PENDING, true).apply()
                            }
                            sessionToken = token
                        },
                    )
                } else {
                val viewModel: HomeVisitViewModel = viewModel()
                val uiState by viewModel.uiState.collectAsStateWithLifecycle()
                var onboardingPending by rememberSaveable {
                    mutableStateOf(prefs.getBoolean(KEY_ONBOARDING_PENDING, false))
                }
                if (onboardingPending) {
                    LaunchedEffect(Unit) {
                        if (uiState.appSettings.snapshot == null) {
                            viewModel.refreshAppSettings(DEFAULT_SERVER_URL, sessionToken)
                        }
                    }
                    OnboardingScreen(
                        appSettings = uiState.appSettings,
                        onRefresh = { viewModel.refreshAppSettings(DEFAULT_SERVER_URL, sessionToken) },
                        onSave = { values -> viewModel.saveAppSettings(DEFAULT_SERVER_URL, sessionToken, values) },
                        onFinish = {
                            prefs.edit().putBoolean(KEY_ONBOARDING_PENDING, false).apply()
                            onboardingPending = false
                        },
                        onSuggestAddress = { key, query ->
                            viewModel.suggestSettingsAddress(DEFAULT_SERVER_URL, sessionToken, key, query)
                        },
                        onRequestCity = { key ->
                            viewModel.suggestSettingsCity(DEFAULT_SERVER_URL, sessionToken, key)
                        },
                    )
                    return@HomeVisitTheme
                }
                // Share-target (Ф15.1/15.2): пришёл «Поделиться» текстом — разбираем пакетным
                // парсером и показываем экран подтверждения (зелёные/жёлтые/красные).
                val sharedText = remember { extractSharedText(intent) }
                // Share-target скриншотом (Ф15.4): пришла картинка — читаем байты и шлём на
                // наш OCR, дальше тот же экран пакета, что и для текста.
                val sharedImageUri = remember { extractSharedImageUri(intent) }
                val batchOrders by viewModel.batchOrders.collectAsStateWithLifecycle()
                val shareImage by viewModel.shareImage.collectAsStateWithLifecycle()
                // Миниатюра принятого фото. Живёт только в памяти экрана: изображение
                // транзитное и на диск не ложится (152-ФЗ).
                var sharedImagePreview by remember { mutableStateOf<ImageBitmap?>(null) }
                LaunchedEffect(sharedText) {
                    if (!sharedText.isNullOrBlank()) {
                        viewModel.parseSharedText(DEFAULT_SERVER_URL, sessionToken, sharedText)
                    }
                }
                LaunchedEffect(sharedImageUri) {
                    if (sharedImageUri != null) {
                        val bytes = runCatching {
                            contentResolver.openInputStream(sharedImageUri)?.use { it.readBytes() }
                        }.getOrNull()
                        if (bytes != null && bytes.isNotEmpty()) {
                            // Сначала миниатюра, потом разбор: человек должен увидеть, что
                            // фото принято, ещё до того, как ответит OCR.
                            sharedImagePreview = decodeThumbnail(bytes)
                            viewModel.parseSharedImage(DEFAULT_SERVER_URL, sessionToken, bytes)
                        }
                    }
                }
                if (batchOrders.isNotEmpty()) {
                    BatchOrdersScreen(
                        orders = batchOrders,
                        onAddGreen = { greens -> viewModel.addBatchGreen(DEFAULT_SERVER_URL, sessionToken, greens) },
                        onClose = { viewModel.clearBatch() },
                    )
                    return@HomeVisitTheme
                }
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
                Box(Modifier.fillMaxSize()) {
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
                    onStartDayDetails = viewModel::startDayWithResolvedDetails,
                    onStartShift = viewModel::startShift,
                    onRefreshHome = viewModel::refreshHome,
                    onRefreshShift = viewModel::refreshShift,
                    onRefreshProfile = viewModel::refreshProfile,
                    onConfirmIncome = viewModel::confirmIncome,
                    onEndDay = viewModel::endDay,
                    onEndDayWithOdometer = viewModel::endDayWithOdometer,
                    onEndDayWithDetails = viewModel::endDayWithDetails,
                    onPrepareEndShift = viewModel::prepareEndShift,
                    onClearEndShift = viewModel::clearEndShift,
                    onCalculateVisit = viewModel::calculateVisitCandidate,
                    onPersonalEstimate = viewModel::runPersonalEstimate,
                    onClearPersonalEstimate = viewModel::clearPersonalEstimate,
                    onServerVoiceTranscribe = viewModel::transcribeServerVoice,
                    onPickAddressCandidate = viewModel::pickAddressCandidate,
                    onAcceptCandidate = viewModel::acceptCandidate,
                    onDismissDuplicate = viewModel::dismissDuplicateConfirm,
                    onRejectCandidate = viewModel::rejectCandidate,
                    onCompleteCurrentVisit = viewModel::completeCurrentVisit,
                    onCancelCurrentVisit = viewModel::cancelCurrentVisit,
                    onCancelVisitById = viewModel::cancelVisitById,
                    onArchiveRange = viewModel::setArchiveRange,
                    onArchiveSort = viewModel::setArchiveSort,
                    onOpenOrder = viewModel::openOrder,
                    onCloseOrder = viewModel::closeOrder,
                    onCancelInRoute = viewModel::cancelInRouteCurrentVisit,
                    onCheckAutoClose = viewModel::checkAutoClose,
                    onUndoAutoClose = viewModel::undoAutoClose,
                    onDismissAutoClose = viewModel::dismissAutoClose,
                    onCancelPendingNav = viewModel::cancelPendingNav,
                    onRefreshRoute = viewModel::refreshRoute,
                    onUpdateFinish = viewModel::updateFinish,
                    onUpdateStart = viewModel::updateStart,
                    onReorderRoute = viewModel::reorderRoute,
                    onRefreshGpsHint = viewModel::refreshGpsHint,
                    onClassifyCurrentStop = viewModel::classifyCurrentStop,
                    onRefreshGpsEstimate = viewModel::refreshGpsEstimate,
                    onRefreshActiveReport = viewModel::refreshActiveReport,
                    onRefreshStatsReport = viewModel::refreshStatsReport,
                    onRefreshWorkload = viewModel::refreshWorkload,
                    onSubmitWorkloadFeedback = viewModel::submitWorkloadFeedback,
                    onRefreshWorkloadCorrelation = viewModel::refreshWorkloadCorrelation,
                    onRefreshWorkloadTrend = viewModel::refreshWorkloadTrend,
                    onSubmitSurvey = viewModel::submitSurvey,
                    onExportBackup = viewModel::exportBackup,
                    onBackupExportHandled = viewModel::clearBackupExport,
                    onRefreshSyncConflicts = viewModel::refreshSyncConflicts,
                    onCheckConnection = viewModel::checkConnection,
                    onClearCache = viewModel::clearCache,
                    onImportBackup = viewModel::importBackup,
                    onAddOffice = viewModel::addOnSite,
                    onAddTelemed = viewModel::addTelemed,
                    onAddExpense = viewModel::addExpense,
                    onRefreshAppSettings = viewModel::refreshAppSettings,
                    onSaveAppSettings = viewModel::saveAppSettings,
                    onRefreshClinics = viewModel::refreshClinics,
                    onSuggestSettingsAddress = viewModel::suggestSettingsAddress,
                    onRequestSettingsCity = viewModel::suggestSettingsCity,
                )
                    // Подтверждение принятого фото — поверх приложения, а не вместо него:
                    // OCR считает на сервере секунды, и всё это время человек должен
                    // видеть, что фото добавлено, продолжая пользоваться экраном.
                    // Нашлись адреса — откроется экран пакета, и карточка не нужна.
                    if (batchOrders.isEmpty() && (shareImage.loading || shareImage.failed)) {
                        Box(Modifier.align(Alignment.TopCenter)) {
                            SharedImageCard(
                                preview = sharedImagePreview,
                                ui = shareImage,
                                onDismiss = {
                                    viewModel.dismissSharedImage()
                                    sharedImagePreview = null
                                },
                            )
                        }
                    }
                }
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
        // Онбординг после регистрации не завершён: спрашиваем настройки, пока
        // человек не сохранил их или не отложил осознанно.
        const val KEY_ONBOARDING_PENDING = "onboarding_pending"
        // Последняя точка GPS — её шлём в подсказки адреса, чтобы сервер понимал город
        // по местоположению (Фаза 2). Пишет LocationUploadService на каждом фиксе.
        const val KEY_LAST_GPS_LAT = "last_gps_lat"
        const val KEY_LAST_GPS_LON = "last_gps_lon"
        const val KEY_LAST_GPS_AT = "last_gps_at"
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
    val onStartDayDetails: (String, String, Double) -> Unit,
    val onStartShift: (Double, Double) -> Unit,
    val onRefreshHome: () -> Unit,
    val onRefreshShift: (String) -> Unit,
    val onRefreshProfile: () -> Unit,
    val onConfirmIncome: () -> Unit,
    val onEndDay: () -> Unit,
    val onEndDayWithOdometer: (Double?) -> Unit,
    val onEndDayWithDetails: (EndDayDetails) -> Unit,
    val onPrepareEndShift: () -> Unit,
    val onClearEndShift: () -> Unit,
    val onCalculateVisit: (String, Double, String, Double?, Double?, String?, Double?) -> Unit,
    /** Личная поездка (Ф11.5): «во сколько обойдётся» по адресу, без дохода и вердикта. */
    val onPersonalEstimate: (String) -> Unit,
    val onClearPersonalEstimate: () -> Unit,
    /** Голос через наш ASR (Ф14.4): байты записи → текст колбэком (для телефонов без Google). */
    val onServerVoiceTranscribe: (ByteArray, (String?) -> Unit) -> Unit,
    /** Тап по варианту адреса из кандидатов (Фаза 2): докрутить расчёт по его координатам. */
    val onPickAddressCandidate: (AddressCandidate) -> Unit,
    /** Принять адрес. force=true — подтверждённый повтор адреса, уже есть в ленте. */
    val onAcceptCandidate: (Boolean) -> Unit,
    /** Отмена подтверждения дубля адреса: заказ не добавлять. */
    val onDismissDuplicate: () -> Unit,
    val onRejectCandidate: () -> Unit,
    val onCompleteCurrentVisit: () -> Unit,
    val onCancelCurrentVisit: () -> Unit,
    /** Убрать ЛЮБОЙ заказ из очереди «Далее», а не только текущий (клиент отменился). */
    val onCancelVisitById: (String) -> Unit,
    /** Архив: период, сортировка и открытие подробной карточки заказа. */
    val onArchiveRange: (ArchiveRange) -> Unit,
    val onArchiveSort: (ArchiveSort) -> Unit,
    val onOpenOrder: (String) -> Unit,
    val onCloseOrder: () -> Unit,
    /** Клиент отменил, когда уже ехали (Ф11.3): фиксируем потери. */
    val onCancelInRoute: () -> Unit,
    /** Проверить, не пора ли закрыть заказ самому (человек долго стоит у адреса). */
    val onCheckAutoClose: () -> Unit,
    /** Вернуть заказ, который приложение закрыло само. */
    val onUndoAutoClose: () -> Unit,
    val onDismissAutoClose: () -> Unit,
    /** Остановить отсчёт до автозапуска навигатора. */
    val onCancelPendingNav: () -> Unit,
    val onRefreshRoute: () -> Unit,
    val onUpdateFinish: (String) -> Unit,
    val onUpdateStart: (String) -> Unit,
    val onReorderRoute: (List<Int>) -> Unit,
    val onRefreshGpsHint: () -> Unit,
    val onClassifyCurrentStop: (StopLabel) -> Unit,
    val onRefreshGpsEstimate: () -> Unit,
    val onRefreshActiveReport: (String?) -> Unit,
    val onRefreshStatsReport: (ReportPeriod, String?) -> Unit,
    val onRefreshWorkload: () -> Unit,
    val onSubmitWorkloadFeedback: (String, Double?) -> Unit,
    val onRefreshWorkloadCorrelation: (Int) -> Unit,
    val onRefreshWorkloadTrend: (Int) -> Unit,
    val onSubmitSurvey: (List<Int>) -> Unit,
    val onExportBackup: () -> Unit,
    val onRefreshSyncConflicts: () -> Unit,
    val onCheckConnection: () -> Unit,
    val onClearCache: () -> Unit,
    val onImportBackup: (String) -> Unit,
    val onAddOffice: (String, Double, Double, String, String?, String?) -> Unit,
    val onAddTelemed: (Double, Double, String) -> Unit,
    val onAddExpense: (ExpenseCategory, Double, String) -> Unit,
    val onRefreshAppSettings: () -> Unit,
    val onSaveAppSettings: (Map<String, Any?>) -> Unit,
    /** Подсказки адреса для поля настроек: (ключ поля, введённый текст). */
    val onSuggestSettingsAddress: (String, String) -> Unit = { _, _ -> },
    /** Определить город по GPS для поля настроек: (ключ поля). */
    val onRequestSettingsCity: (String) -> Unit = {},
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
    onStartDayDetails: (String, String, String, String, Double) -> Unit,
    onStartShift: (Double, Double) -> Unit,
    onRefreshHome: (String, String) -> Unit,
    onRefreshShift: (String, String, String) -> Unit,
    onRefreshProfile: (String, String) -> Unit,
    onConfirmIncome: (String, String) -> Unit,
    onEndDay: () -> Unit,
    onEndDayWithOdometer: (Double?) -> Unit,
    onEndDayWithDetails: (EndDayDetails) -> Unit,
    onPrepareEndShift: (String, String) -> Unit,
    onClearEndShift: () -> Unit,
    onCalculateVisit: (String, String, String, Double, String, Double?, Double?, String?, Double?) -> Unit,
    onPersonalEstimate: (String, String, String) -> Unit,
    onClearPersonalEstimate: () -> Unit,
    onServerVoiceTranscribe: (String, String, ByteArray, (String?) -> Unit) -> Unit,
    onPickAddressCandidate: (AddressCandidate) -> Unit,
    onAcceptCandidate: (String, String, Boolean) -> Unit,
    onDismissDuplicate: () -> Unit,
    onRejectCandidate: (String, String) -> Unit,
    onCompleteCurrentVisit: (String, String) -> Unit,
    onCancelCurrentVisit: (String, String) -> Unit,
    onCancelInRoute: (String, String) -> Unit,
    onCancelVisitById: (String, String, String) -> Unit,
    onArchiveRange: (ArchiveRange) -> Unit,
    onArchiveSort: (ArchiveSort) -> Unit,
    onOpenOrder: (String) -> Unit,
    onCloseOrder: () -> Unit,
    onCheckAutoClose: (String, String) -> Unit,
    onUndoAutoClose: (String, String) -> Unit,
    onDismissAutoClose: () -> Unit,
    onCancelPendingNav: () -> Unit,
    onRefreshRoute: (String, String) -> Unit,
    onUpdateFinish: (String, String, String) -> Unit,
    onUpdateStart: (String, String, String) -> Unit,
    onReorderRoute: (String, String, List<Int>) -> Unit,
    onRefreshGpsHint: (String, String) -> Unit,
    onClassifyCurrentStop: (String, String, StopLabel) -> Unit,
    onRefreshGpsEstimate: (String, String) -> Unit,
    onRefreshActiveReport: (String, String, String?) -> Unit,
    onRefreshStatsReport: (String, String, ReportPeriod, String?) -> Unit,
    onRefreshWorkload: (String, String) -> Unit,
    onSubmitWorkloadFeedback: (String, String, String, Double?) -> Unit,
    onRefreshWorkloadCorrelation: (String, String, Int) -> Unit,
    onRefreshWorkloadTrend: (String, String, Int) -> Unit,
    onSubmitSurvey: (String, String, List<Int>) -> Unit,
    onExportBackup: () -> Unit,
    onBackupExportHandled: () -> Unit,
    onRefreshSyncConflicts: (String, String) -> Unit,
    onCheckConnection: (String, String) -> Unit,
    onClearCache: () -> Unit,
    onImportBackup: (String) -> Unit,
    onAddOffice: (String, String, String, Double, Double, String, String?, String?) -> Unit,
    onAddTelemed: (Double, Double, String) -> Unit,
    onAddExpense: (ExpenseCategory, Double, String) -> Unit,
    onRefreshAppSettings: (String, String) -> Unit,
    onSaveAppSettings: (String, String, Map<String, Any?>) -> Unit,
    onRefreshClinics: (String, String) -> Unit,
    onSuggestSettingsAddress: (String, String, String, String) -> Unit = { _, _, _, _ -> },
    onRequestSettingsCity: (String, String, String) -> Unit = { _, _, _ -> },
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
        onStartDayDetails = { start, finish, odometer ->
            onStartDayDetails(serverUrl, apiKey, start, finish, odometer)
        },
        onStartShift = onStartShift,
        onRefreshHome = { onRefreshHome(serverUrl, apiKey) },
        onRefreshShift = { period -> onRefreshShift(serverUrl, apiKey, period) },
        onRefreshProfile = { onRefreshProfile(serverUrl, apiKey) },
        onConfirmIncome = { onConfirmIncome(serverUrl, apiKey) },
        onEndDay = onEndDay,
        onEndDayWithOdometer = onEndDayWithOdometer,
        onEndDayWithDetails = onEndDayWithDetails,
        onPrepareEndShift = { onPrepareEndShift(serverUrl, apiKey) },
        onClearEndShift = onClearEndShift,
        onCalculateVisit = { address, income, clinic, routeKm, routeMinutes, source, responseCost ->
            onCalculateVisit(serverUrl, apiKey, address, income, clinic, routeKm, routeMinutes, source, responseCost)
        },
        onPersonalEstimate = { address -> onPersonalEstimate(serverUrl, apiKey, address) },
        onClearPersonalEstimate = onClearPersonalEstimate,
        onServerVoiceTranscribe = { audio, cb -> onServerVoiceTranscribe(serverUrl, apiKey, audio, cb) },
        onPickAddressCandidate = onPickAddressCandidate,
        onAcceptCandidate = { force -> onAcceptCandidate(serverUrl, apiKey, force) },
        onDismissDuplicate = onDismissDuplicate,
        onRejectCandidate = { onRejectCandidate(serverUrl, apiKey) },
        onCompleteCurrentVisit = { onCompleteCurrentVisit(serverUrl, apiKey) },
        onCancelCurrentVisit = { onCancelCurrentVisit(serverUrl, apiKey) },
        onCancelVisitById = { localId -> onCancelVisitById(serverUrl, apiKey, localId) },
        onArchiveRange = onArchiveRange,
        onArchiveSort = onArchiveSort,
        onOpenOrder = onOpenOrder,
        onCloseOrder = onCloseOrder,
        onCancelInRoute = { onCancelInRoute(serverUrl, apiKey) },
        onCheckAutoClose = { onCheckAutoClose(serverUrl, apiKey) },
        onUndoAutoClose = { onUndoAutoClose(serverUrl, apiKey) },
        onDismissAutoClose = onDismissAutoClose,
        onCancelPendingNav = onCancelPendingNav,
        onRefreshRoute = { onRefreshRoute(serverUrl, apiKey) },
        onUpdateFinish = { address -> onUpdateFinish(serverUrl, apiKey, address) },
        onUpdateStart = { address -> onUpdateStart(serverUrl, apiKey, address) },
        onReorderRoute = { ids -> onReorderRoute(serverUrl, apiKey, ids) },
        onRefreshGpsHint = { onRefreshGpsHint(serverUrl, apiKey) },
        onClassifyCurrentStop = { label -> onClassifyCurrentStop(serverUrl, apiKey, label) },
        onRefreshGpsEstimate = { onRefreshGpsEstimate(serverUrl, apiKey) },
        onRefreshActiveReport = { clinic -> onRefreshActiveReport(serverUrl, apiKey, clinic) },
        onRefreshStatsReport = { period, clinic -> onRefreshStatsReport(serverUrl, apiKey, period, clinic) },
        onRefreshWorkload = { onRefreshWorkload(serverUrl, apiKey) },
        onSubmitWorkloadFeedback = { action, score -> onSubmitWorkloadFeedback(serverUrl, apiKey, action, score) },
        onRefreshWorkloadCorrelation = { days -> onRefreshWorkloadCorrelation(serverUrl, apiKey, days) },
        onRefreshWorkloadTrend = { days -> onRefreshWorkloadTrend(serverUrl, apiKey, days) },
        onSubmitSurvey = { answers -> onSubmitSurvey(serverUrl, apiKey, answers) },
        onExportBackup = onExportBackup,
        onRefreshSyncConflicts = { onRefreshSyncConflicts(serverUrl, apiKey) },
        onCheckConnection = { onCheckConnection(serverUrl, apiKey) },
        onClearCache = onClearCache,
        onImportBackup = onImportBackup,
        onAddOffice = { address, minutes, income, clinic, startAt, endAt ->
            onAddOffice(serverUrl, apiKey, address, minutes, income, clinic, startAt, endAt)
        },
        onAddTelemed = onAddTelemed,
        onAddExpense = onAddExpense,
        onRefreshAppSettings = { onRefreshAppSettings(serverUrl, apiKey) },
        onSaveAppSettings = { values -> onSaveAppSettings(serverUrl, apiKey, values) },
        onSuggestSettingsAddress = { key, query -> onSuggestSettingsAddress(serverUrl, apiKey, key, query) },
        onRequestSettingsCity = { key -> onRequestSettingsCity(serverUrl, apiKey, key) },
    )
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
            appSettings = uiState.appSettings,
            reportState = uiState.report,
            workloadState = uiState.workload,
            workActions = workActions,
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
    App("Параметры расчёта"),
    Zones("Зоны обслуживания"),
    Reports("Подробные отчёты"),
    Workload("Режим труда"),
}

/** Экран настроек как оверлей (открывается шестерёнкой), с под-навигацией и «назад». */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun SettingsOverlay(
    settingsState: GpsSettingsState,
    appSettings: AppSettingsUiState,
    reportState: ReportUiState,
    workloadState: WorkloadUiState,
    workActions: WorkActions,
    onBack: () -> Unit,
) {
    var page by rememberSaveable { mutableStateOf(SettingsPage.Main) }
    // Страницы параметров и зон бесполезны без каталога с сервера — тянем его при
    // каждом входе, а не только при пустом: снапшот устаревает незаметно (смена
    // якоря в Ленте «липко» обновляет дефолтные адреса), и по устаревшему снапшоту
    // повторный ввод того же адреса глотался сравнением «ничего не изменилось».
    LaunchedEffect(page) {
        val needsCatalog = page == SettingsPage.App || page == SettingsPage.Zones
        if (needsCatalog && !appSettings.isLoading) {
            workActions.onRefreshAppSettings()
        }
    }
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
                    settingsState, appSettings, workActions,
                    onOpenReports = { page = SettingsPage.Reports },
                    onOpenWorkload = { page = SettingsPage.Workload },
                    onOpenAppSettings = { page = SettingsPage.App },
                    onOpenZones = { page = SettingsPage.Zones },
                )
                SettingsPage.App -> AppSettingsPage(appSettings, workActions)
                SettingsPage.Zones -> BaseZonesPage(appSettings, workActions)
                SettingsPage.Reports -> ReportsScreen(reportState, workActions)
                SettingsPage.Workload -> WorkloadScreen(workloadState, workActions)
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
            // Состояние вкладки переживает переключение. Без SaveableStateProvider экран
            // при уходе покидает композицию, и весь его rememberSaveable обнуляется:
            // набранный адрес пропадал при переходе на Ленту и обратно. rememberSaveable
            // спасает только от поворота экрана и смерти процесса (запись в Bundle), но
            // не от удаления из дерева. Теперь поле чистится лишь тогда, когда его
            // очистил сам человек.
            val tabState = rememberSaveableStateHolder()
            tabState.SaveableStateProvider(selected) {
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
                        onConfirmIncome = workActions.onConfirmIncome,
                        onLogout = settingsState.onLogout,
                    )
                }
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
