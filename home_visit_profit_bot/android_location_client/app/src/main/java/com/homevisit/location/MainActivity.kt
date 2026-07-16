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
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.homevisit.location.domain.Clinic
import com.homevisit.location.domain.ClinicReportRow
import com.homevisit.location.domain.EndDayDetails
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.FatigueCorrelationCell
import com.homevisit.location.domain.FatigueCorrelationReport
import com.homevisit.location.domain.FatigueSnapshot
import com.homevisit.location.domain.ReportPeriod
import com.homevisit.location.domain.ReportSnapshot
import com.homevisit.location.domain.ReportSummary
import com.homevisit.location.domain.StopLabel
import com.homevisit.location.domain.WorkDayStatus
import com.homevisit.location.sync.SyncScheduler
import com.homevisit.location.ui.CandidateUiState
import com.homevisit.location.ui.FatigueUiState
import com.homevisit.location.ui.GpsEstimateUiState
import com.homevisit.location.ui.GpsHintUiState
import com.homevisit.location.ui.HomeVisitUiState
import com.homevisit.location.ui.HomeVisitViewModel
import com.homevisit.location.ui.ReportUiState
import com.homevisit.location.ui.RouteUiState
import com.homevisit.location.ui.RouteVisitUi
import com.homevisit.location.ui.SyncUiState
import java.util.Locale

class MainActivity : ComponentActivity() {
    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        SyncScheduler.schedule(this)
        setContent {
            HomeVisitTheme {
                val viewModel: HomeVisitViewModel = viewModel()
                val uiState by viewModel.uiState.collectAsStateWithLifecycle()
                HomeVisitApp(
                    uiState = uiState,
                    initialServerUrl = prefs.getString(KEY_SERVER_URL, "").orEmpty(),
                    initialApiKey = prefs.getString(KEY_API_KEY, "").orEmpty(),
                    initialInterval = prefs.getInt(KEY_INTERVAL_SECONDS, 60).toString(),
                    onSaveSettings = ::saveSettings,
                    onStartGps = ::startTracking,
                    onStopGps = ::stopTracking,
                    onStartDay = viewModel::startDay,
                    onStartDayDetails = viewModel::startDayWithDetails,
                    onEndDay = viewModel::endDay,
                    onEndDayWithOdometer = viewModel::endDayWithOdometer,
                    onEndDayWithDetails = viewModel::endDayWithDetails,
                    onCalculateVisit = viewModel::calculateVisitCandidate,
                    onAcceptCandidate = viewModel::acceptCandidate,
                    onRejectCandidate = viewModel::rejectCandidate,
                    onCompleteCurrentVisit = viewModel::completeCurrentVisit,
                    onCancelCurrentVisit = viewModel::cancelCurrentVisit,
                    onRefreshRoute = viewModel::refreshRoute,
                    onRefreshGpsHint = viewModel::refreshGpsHint,
                    onClassifyCurrentStop = viewModel::classifyCurrentStop,
                    onRefreshGpsEstimate = viewModel::refreshGpsEstimate,
                    onRefreshActiveReport = viewModel::refreshActiveReport,
                    onRefreshStatsReport = viewModel::refreshStatsReport,
                    onRefreshFatigue = viewModel::refreshFatigue,
                    onSubmitFatigueFeedback = viewModel::submitFatigueFeedback,
                    onRefreshFatigueCorrelation = viewModel::refreshFatigueCorrelation,
                    onSubmitCbi = viewModel::submitCbi,
                    onExportBackup = viewModel::exportBackup,
                    onBackupExportHandled = viewModel::clearBackupExport,
                    onRefreshSyncConflicts = viewModel::refreshSyncConflicts,
                    onImportBackup = viewModel::importBackup,
                    onAddOffice = viewModel::addOffice,
                    onAddTelemed = viewModel::addTelemed,
                    onAddExpense = viewModel::addExpense,
                    onSync = viewModel::syncPending,
                )
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
        private const val PERMISSION_REQUEST = 1001
    }
}

private enum class AppDestination(
    val label: String,
    val shortLabel: String,
    val title: String,
) {
    Today("Сегодня", "С", "Сегодня"),
    Work("Работа", "Р", "Работа"),
    Route("Маршрут", "М", "Маршрут и GPS"),
    Reports("Отчеты", "О", "Отчеты"),
    Fatigue("Усталость", "У", "Усталость"),
    Settings("Настройки", "Н", "Настройки"),
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
    val onEndDay: () -> Unit,
    val onEndDayWithOdometer: (Double?) -> Unit,
    val onEndDayWithDetails: (EndDayDetails) -> Unit,
    val onCalculateVisit: (String, Double, Clinic, Double?, Double?) -> Unit,
    val onAcceptCandidate: () -> Unit,
    val onRejectCandidate: () -> Unit,
    val onCompleteCurrentVisit: () -> Unit,
    val onCancelCurrentVisit: () -> Unit,
    val onRefreshRoute: () -> Unit,
    val onRefreshGpsHint: () -> Unit,
    val onClassifyCurrentStop: (StopLabel) -> Unit,
    val onRefreshGpsEstimate: () -> Unit,
    val onRefreshActiveReport: () -> Unit,
    val onRefreshStatsReport: (ReportPeriod) -> Unit,
    val onRefreshFatigue: () -> Unit,
    val onSubmitFatigueFeedback: (String, Double?) -> Unit,
    val onRefreshFatigueCorrelation: (Int) -> Unit,
    val onSubmitCbi: (List<Int>) -> Unit,
    val onExportBackup: () -> Unit,
    val onRefreshSyncConflicts: () -> Unit,
    val onImportBackup: (String) -> Unit,
    val onAddOffice: (String, Double, Double, Clinic) -> Unit,
    val onAddTelemed: (Double, Double, Clinic) -> Unit,
    val onAddExpense: (ExpenseCategory, Double, String) -> Unit,
)

@Composable
private fun HomeVisitTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = androidx.compose.material3.lightColorScheme(
            primary = Color(0xFF176B52),
            secondary = Color(0xFF50645B),
            tertiary = Color(0xFF38656B),
            surface = Color(0xFFF7FAF8),
            background = Color(0xFFF2F6F4),
        ),
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
    onSaveSettings: (String, String, String) -> Unit,
    onStartGps: (String, String, String) -> Unit,
    onStopGps: () -> Unit,
    onStartDay: () -> Unit,
    onStartDayDetails: (String, String, Double, Double, Double, Double) -> Unit,
    onEndDay: () -> Unit,
    onEndDayWithOdometer: (Double?) -> Unit,
    onEndDayWithDetails: (EndDayDetails) -> Unit,
    onCalculateVisit: (String, String, String, Double, Clinic, Double?, Double?) -> Unit,
    onAcceptCandidate: (String, String) -> Unit,
    onRejectCandidate: (String, String) -> Unit,
    onCompleteCurrentVisit: (String, String) -> Unit,
    onCancelCurrentVisit: (String, String) -> Unit,
    onRefreshRoute: (String, String) -> Unit,
    onRefreshGpsHint: (String, String) -> Unit,
    onClassifyCurrentStop: (String, String, StopLabel) -> Unit,
    onRefreshGpsEstimate: (String, String) -> Unit,
    onRefreshActiveReport: (String, String) -> Unit,
    onRefreshStatsReport: (String, String, ReportPeriod) -> Unit,
    onRefreshFatigue: (String, String) -> Unit,
    onSubmitFatigueFeedback: (String, String, String, Double?) -> Unit,
    onRefreshFatigueCorrelation: (String, String, Int) -> Unit,
    onSubmitCbi: (String, String, List<Int>) -> Unit,
    onExportBackup: () -> Unit,
    onBackupExportHandled: () -> Unit,
    onRefreshSyncConflicts: (String, String) -> Unit,
    onImportBackup: (String) -> Unit,
    onAddOffice: (String, Double, Double, Clinic) -> Unit,
    onAddTelemed: (Double, Double, Clinic) -> Unit,
    onAddExpense: (ExpenseCategory, Double, String) -> Unit,
    onSync: (String, String) -> Unit,
) {
    var selected by rememberSaveable { mutableStateOf(AppDestination.Today) }
    var serverUrl by rememberSaveable { mutableStateOf(initialServerUrl) }
    var apiKey by rememberSaveable { mutableStateOf(initialApiKey) }
    var intervalSeconds by rememberSaveable { mutableStateOf(initialInterval) }
    var gpsRunning by rememberSaveable { mutableStateOf(false) }
    val context = LocalContext.current

    val settingsState = GpsSettingsState(
        serverUrl = serverUrl,
        apiKey = apiKey,
        intervalSeconds = intervalSeconds,
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
        gpsRunning = gpsRunning,
    )
    val workActions = WorkActions(
        onStartDay = onStartDay,
        onStartDayDetails = onStartDayDetails,
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
        onRefreshGpsHint = { onRefreshGpsHint(serverUrl, apiKey) },
        onClassifyCurrentStop = { label -> onClassifyCurrentStop(serverUrl, apiKey, label) },
        onRefreshGpsEstimate = { onRefreshGpsEstimate(serverUrl, apiKey) },
        onRefreshActiveReport = { onRefreshActiveReport(serverUrl, apiKey) },
        onRefreshStatsReport = { period -> onRefreshStatsReport(serverUrl, apiKey, period) },
        onRefreshFatigue = { onRefreshFatigue(serverUrl, apiKey) },
        onSubmitFatigueFeedback = { action, score -> onSubmitFatigueFeedback(serverUrl, apiKey, action, score) },
        onRefreshFatigueCorrelation = { days -> onRefreshFatigueCorrelation(serverUrl, apiKey, days) },
        onSubmitCbi = { answers -> onSubmitCbi(serverUrl, apiKey, answers) },
        onExportBackup = onExportBackup,
        onRefreshSyncConflicts = { onRefreshSyncConflicts(serverUrl, apiKey) },
        onImportBackup = onImportBackup,
        onAddOffice = onAddOffice,
        onAddTelemed = onAddTelemed,
        onAddExpense = onAddExpense,
    )
    val syncNow = { onSync(serverUrl, apiKey) }
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
                bottomBar = {
                    AppNavigationBar(selected = selected, onSelect = { selected = it })
                },
            )
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
    bottomBar: @Composable () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(selected.title, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            "Home Visit",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
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
                AppDestination.Today -> TodayScreen(uiState, workActions, settingsState, onSync)
                AppDestination.Work -> WorkScreen(uiState, workActions)
                AppDestination.Route -> RouteScreen(uiState, workActions, settingsState)
                AppDestination.Reports -> ReportsScreen(uiState.report, workActions)
                AppDestination.Fatigue -> FatigueScreen(uiState.fatigue, workActions)
                AppDestination.Settings -> SettingsScreen(settingsState, uiState.sync, workActions, onSync)
            }
        }
    }
}

@Composable
private fun AppNavigationBar(selected: AppDestination, onSelect: (AppDestination) -> Unit) {
    NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
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
        containerColor = MaterialTheme.colorScheme.surface,
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
    Box(
        modifier = Modifier
            .size(28.dp)
            .clip(CircleShape)
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            destination.shortLabel,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
        )
    }
}

@Composable
private fun TodayScreen(uiState: HomeVisitUiState, workActions: WorkActions, settingsState: GpsSettingsState, onSync: () -> Unit) {
    val fatigueText = uiState.fatigue.snapshot?.summary?.let { ", усталость ${oneDecimal(it.score)}/100" }.orEmpty()
    val syncText = if (uiState.sync.stats.pendingCount + uiState.sync.stats.failedCount > 0) {
        ", sync: ${uiState.sync.stats.pendingCount} ждут / ${uiState.sync.stats.failedCount} ошибок"
    } else {
        ", sync чисто"
    }
    ScreenColumn {
        StatusCard(
            title = "Рабочий день",
            value = uiState.status.title(),
            body = "Адресов: ${uiState.visitsCount}, офис: ${uiState.officeCount}, телемед: ${uiState.telemedCount}$fatigueText$syncText. Доход: ${money(uiState.grossIncome)}, чистыми после расходов: ${money(uiState.netIncome)}.",
        )
        DayDetailsCard(uiState, workActions)
        DayControlRow(uiState, workActions)
        QuickActions()
        GpsControlCard(settingsState)
        SyncControlCard(
            syncState = uiState.sync,
            onSync = onSync,
            onExportBackup = workActions.onExportBackup,
            onRefreshConflicts = workActions.onRefreshSyncConflicts,
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
            "Для чистого дохода/час, топлива, личного коэффициента дороги и усталости.",
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
            MoneyField(modifier = Modifier.weight(1f), value = completedVisitsText, onValueChange = { completedVisitsText = it }, label = "Вызовов")
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
            MoneyField(modifier = Modifier.weight(1f), value = fatigueText, onValueChange = { fatigueText = it }, label = "Усталость 0-100")
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
                onCalculate = workActions.onCalculateVisit,
                onAccept = workActions.onAcceptCandidate,
                onReject = workActions.onRejectCandidate,
            )
            WorkForm.Office -> OfficeInputCard(workActions.onAddOffice)
            WorkForm.Telemed -> TelemedInputCard(workActions.onAddTelemed)
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
        RouteListCard(uiState.routeVisits)
        StopClassificationCard(
            activeVisit = uiState.activeVisit,
            isLoading = uiState.serverRoute.isLoading,
            onSelect = workActions.onClassifyCurrentStop,
        )
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
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
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
                    "Нет принятого адреса. После расчёта и принятия вызова он появится здесь.",
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
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
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
                    "Пока нет серверного порядка адресов. Нажмите обновить после принятия вызова.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
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
            "Уточнение влияет только на усталость и долг восстановления, экономический расчёт не меняет.",
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
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
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
            onClick = {
                when (selectedMode) {
                    ReportMode.Active -> workActions.onRefreshActiveReport()
                    ReportMode.Day -> workActions.onRefreshStatsReport(ReportPeriod.Day)
                    ReportMode.Month -> workActions.onRefreshStatsReport(ReportPeriod.Month)
                    ReportMode.Year -> workActions.onRefreshStatsReport(ReportPeriod.Year)
                }
            },
        ) {
            Text(if (reportState.isLoading) "Обновляю..." else "Обновить отчёт")
        }
        if (reportState.message.isNotBlank()) {
            CompactCard(title = "Статус", body = reportState.message)
        }
        if (snapshot != null) {
            ReportSummaryCard(snapshot)
            ClinicBreakdownCard(snapshot.clinics)
            ExpenseBreakdownCard(snapshot.summary)
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
                "Вызовы" to snapshot.summary.visitsCount.toString(),
                "Работа" to minutesText(snapshot.summary.totalWorkMinutes),
                "Дорога" to minutesText(snapshot.summary.totalRouteMinutes),
                "Км" to oneDecimal(snapshot.summary.actualKm),
            ),
        )
        ReportLine("Вызовы", money(snapshot.summary.visitIncome))
        ReportLine("Телемедицина", money(snapshot.summary.telemedIncome))
        ReportLine("Офис", "${money(snapshot.summary.officeIncome)} / ${minutesText(snapshot.summary.officeMinutes)}")
        if (snapshot.summary.fatigueScore > 0 || snapshot.summary.recoveryDebt > 0) {
            ReportLine(
                "Усталость",
                "${oneDecimal(snapshot.summary.fatigueScore)}/100, долг ${oneDecimal(snapshot.summary.recoveryDebt)}",
            )
        }
    }
}

@Composable
private fun ClinicBreakdownCard(rows: List<ClinicReportRow>) {
    InputCard("По клиникам") {
        if (rows.isEmpty()) {
            Text(
                "Данных по клиникам пока нет.",
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
        shape = RoundedCornerShape(8.dp),
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
                "Вызовы: ${row.visitsCount} / ${money(row.visitIncome)}. Телемед: ${money(row.telemedIncome)}. Офис: ${money(row.officeIncome)}.",
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
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
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
    var cbiAnswersText by rememberSaveable { mutableStateOf("") }
    val snapshot = fatigueState.snapshot
    val summary = snapshot?.summary
    val cbiQuestions = snapshot?.cbi?.questions.orEmpty()
    val cbiAnswers = parseCbiAnswers(cbiAnswersText, cbiQuestions.size)
    ScreenColumn {
        StatusCard(
            title = "Усталость",
            value = summary?.let { "${oneDecimal(it.score)} / 100" } ?: "Нет данных",
            body = summary?.let {
                "${it.level}. 7 дней: ${oneDecimal(it.weeklyAverage)}, долг восстановления: ${oneDecimal(it.recoveryDebt)}, CBI: ${oneDecimal(it.burnoutScore)}."
            } ?: "Обновите сводку после синхронизации. Активный день считается предварительно, закрытый день берётся из статистики.",
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = !fatigueState.isLoading,
            onClick = workActions.onRefreshFatigue,
        ) {
            Text(if (fatigueState.isLoading) "Обновляю..." else "Обновить усталость")
        }
        if (fatigueState.message.isNotBlank()) {
            CompactCard(title = "Статус", body = fatigueState.message)
        }
        if (snapshot != null) {
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
        FatigueCorrelationCard(
            report = fatigueState.correlation,
            selectedDays = selectedCorrelationDays,
            onDaysChange = { selectedCorrelationDays = it },
            onRefresh = { workActions.onRefreshFatigueCorrelation(selectedCorrelationDays) },
        )
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
                "CBI" to "${oneDecimal(summary.burnoutScore)}/100",
                "Сон" to "${oneDecimal(summary.sleepHours)} ч",
                "Качество" to "${oneDecimal(summary.sleepQuality)}/5",
                "Перерыв" to "${oneDecimal(summary.breakHoursBefore)} ч",
                "Циркадный риск" to minutesText(summary.circadianRiskMinutes),
            ),
        )
        ReportLine("Длинные остановки", summary.longStopCount.toString())
        ReportLine("Вероятные паузы", minutesText(summary.pauseMinutes))
        ReportLine("Тяжёлые GPS-вызовы", summary.heavyVisitCount.toString())
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
    InputCard("CBI/выгорание") {
        Text(
            "Последний CBI: ${oneDecimal(latestScore)}/100, $latestLevel.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (questions.isEmpty()) {
            Text("Нажмите `Обновить усталость`, чтобы загрузить вопросы.", style = MaterialTheme.typography.bodyMedium)
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
                Text("Сохранить CBI")
            }
        }
    }
}

@Composable
private fun FatigueCorrelationCard(
    report: FatigueCorrelationReport?,
    selectedDays: Int,
    onDaysChange: (Int) -> Unit,
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
                "Матрица станет полезной после 2-4 недель данных по усталости, вождению, сну и расходам.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            Text(
                "Дней: ${report.days}, строк данных: ${report.rowsUsed}. Чем ближе коэффициент к +1/-1, тем сильнее связь.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            topCorrelationCells(report.cells).forEach { cell ->
                CorrelationRow(cell)
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
private fun SettingsScreen(settingsState: GpsSettingsState, syncState: SyncUiState, workActions: WorkActions, onSync: () -> Unit) {
    ScreenColumn {
        GpsSettingsCard(settingsState)
        SyncControlCard(
            syncState = syncState,
            onSync = onSync,
            onExportBackup = workActions.onExportBackup,
            onRefreshConflicts = workActions.onRefreshSyncConflicts,
            onImportBackup = workActions.onImportBackup,
            showImport = true,
        )
        CompactCard(
            title = "Что здесь важно",
            body = "URL сервера и API ключ нужны для расчёта маршрутов, отчётов, усталости и синхронизации. Экспорт/импорт JSON помогает перенести локальные данные без Telegram.",
        )
    }
}

@Composable
private fun ScreenColumn(content: @Composable Column.() -> Unit) {
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
private fun QuickActions() {
    SectionHeader("Быстрые действия")
    ActionGrid(
        actions = listOf(
            "+ Адрес" to "Домашний вызов с расчетом.",
            "ОФИС" to "Прием на предприятии.",
            "Телемед" to "ПСК или ДНД.",
            "Расход" to "Еда, кофе, парковка.",
        ),
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
    onCalculate: (String, Double, Clinic, Double?, Double?) -> Unit,
    onAccept: () -> Unit,
    onReject: () -> Unit,
) {
    var address by rememberSaveable { mutableStateOf("") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    var routeKmText by rememberSaveable { mutableStateOf("") }
    var routeMinutesText by rememberSaveable { mutableStateOf("") }
    var clinic by rememberSaveable { mutableStateOf(Clinic.Dynasty) }
    val income = parseNumber(incomeText)
    val routeKm = parseNumber(routeKmText)
    val routeMinutes = parseNumber(routeMinutesText)
    val hasManualRoute = routeKm != null && routeMinutes != null

    InputCard("Домашний вызов") {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = address,
            onValueChange = { address = it },
            label = { Text("Адрес") },
            singleLine = false,
        )
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Стоимость")
        ClinicPicker(selected = clinic, onSelect = { clinic = it })
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
            enabled = address.isNotBlank() && income != null,
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
            Text(if (candidate.isLoading) "Считаю..." else "Рассчитать вызов")
        }
        CandidateResultCard(candidate = candidate, onAccept = onAccept, onReject = onReject)
    }
}

@Composable
private fun CandidateResultCard(candidate: CandidateUiState, onAccept: () -> Unit, onReject: () -> Unit) {
    val estimate = candidate.estimate
    if (candidate.message.isBlank() && estimate == null && !candidate.isLoading) {
        return
    }
    Card(
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (candidate.message.isNotBlank()) {
                Text(candidate.message, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
            }
            if (candidate.needsManualRoute) {
                Text(
                    "Заполните поля `Км вручную` и `Мин вручную`, затем нажмите `Рассчитать вызов` ещё раз.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (estimate != null) {
                Text(estimate.decision, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(estimate.reason, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(
                    "Было ${money(estimate.beforeHourly)}/ч, станет ${money(estimate.afterHourly)}/ч. Маржинально: ${money(estimate.marginalHourly)}/ч.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    "Добавится: ${oneDecimal(estimate.extraKm)} км, ${oneDecimal(estimate.extraDriveMinutes)} мин. Минимум: ${money(estimate.requiredCandidateIncome)}, надбавка: ${money(estimate.requiredExtraPayment)}.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                if (estimate.fatigueExtraPayment > 0 || estimate.fatigueLevel.isNotBlank()) {
                    Text(
                        "Усталость: ${estimate.fatigueLevel.ifBlank { "без отдельного уровня" }}, надбавка ${money(estimate.fatigueExtraPayment)}.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        modifier = Modifier.weight(1f),
                        enabled = !candidate.isLoading,
                        onClick = onAccept,
                    ) {
                        Text("Принять")
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
private fun OfficeInputCard(onSubmit: (String, Double, Double, Clinic) -> Unit) {
    var address by rememberSaveable { mutableStateOf("") }
    var minutesText by rememberSaveable { mutableStateOf("") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    var clinic by rememberSaveable { mutableStateOf(Clinic.Dynasty) }
    val minutes = parseNumber(minutesText)
    val income = parseNumber(incomeText)

    InputCard("ОФИС") {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = address,
            onValueChange = { address = it },
            label = { Text("Адрес предприятия") },
            singleLine = false,
        )
        MoneyField(value = minutesText, onValueChange = { minutesText = it }, label = "Продолжительность, мин")
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Стоимость")
        ClinicPicker(selected = clinic, onSelect = { clinic = it })
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = address.isNotBlank() && minutes != null && income != null,
            onClick = {
                onSubmit(address, minutes ?: 0.0, income ?: 0.0, clinic)
                address = ""
                minutesText = ""
                incomeText = ""
            },
        ) {
            Text("Сохранить офис")
        }
    }
}

@Composable
private fun TelemedInputCard(onSubmit: (Double, Double, Clinic) -> Unit) {
    var minutesText by rememberSaveable { mutableStateOf("3") }
    var incomeText by rememberSaveable { mutableStateOf("") }
    var clinic by rememberSaveable { mutableStateOf(Clinic.Psk) }
    val minutes = parseNumber(minutesText)
    val income = parseNumber(incomeText)

    InputCard("Телемедицина") {
        MoneyField(value = incomeText, onValueChange = { incomeText = it }, label = "Стоимость")
        MoneyField(value = minutesText, onValueChange = { minutesText = it }, label = "Минуты")
        ClinicPicker(
            selected = clinic,
            allowedClinics = listOf(Clinic.Psk, Clinic.Dnd),
            onSelect = { clinic = it },
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = minutes != null && income != null,
            onClick = {
                onSubmit(minutes ?: 3.0, income ?: 0.0, clinic)
                incomeText = ""
            },
        ) {
            Text("Сохранить телемедицину")
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
private fun InputCard(title: String, content: @Composable Column.() -> Unit) {
    Card(
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
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
    selected: Clinic,
    allowedClinics: List<Clinic> = Clinic.entries.toList(),
    onSelect: (Clinic) -> Unit,
) {
    OptionGrid(
        options = allowedClinics,
        selected = selected,
        label = { it.title },
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
private fun ActionGrid(actions: List<Pair<String, String>>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        actions.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { (title, body) ->
                    ActionCard(title = title, body = body, modifier = Modifier.weight(1f))
                }
                if (row.size == 1) {
                    Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun ActionCard(title: String, body: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.height(116.dp),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun StatusCard(title: String, value: String, body: String) {
    Card(
        shape = RoundedCornerShape(8.dp),
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
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
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
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
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
    onImportBackup: (String) -> Unit,
    showImport: Boolean = false,
) {
    var importJson by rememberSaveable { mutableStateOf("") }
    Card(
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
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
            OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = onRefreshConflicts) {
                Text("Журнал конфликтов")
            }
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
    Card(
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Подключение к серверу", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = settingsState.serverUrl,
                onValueChange = settingsState.onServerUrlChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("URL сервера") },
                placeholder = { Text("https://example.com:8088/location") },
            )
            OutlinedTextField(
                value = settingsState.apiKey,
                onValueChange = settingsState.onApiKeyChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("API ключ") },
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
}

private fun WorkDayStatus.title(): String = when (this) {
    WorkDayStatus.NotStarted -> "Не начат"
    WorkDayStatus.Active -> "Активен"
    WorkDayStatus.Closed -> "Завершен"
}

private fun WorkForm.title(): String = when (this) {
    WorkForm.Visit -> "Адрес"
    WorkForm.Office -> "ОФИС"
    WorkForm.Telemed -> "Телемед"
    WorkForm.Expense -> "Расход"
}

private fun money(value: Double): String {
    return String.format(Locale("ru", "RU"), "%.0f ₽", value)
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

private fun topCorrelationCells(cells: List<FatigueCorrelationCell>): List<FatigueCorrelationCell> {
    return cells
        .filter { it.n >= 3 && (it.pearson != null || it.spearman != null) }
        .sortedByDescending { kotlin.math.abs(it.pearson ?: it.spearman ?: 0.0) }
        .take(8)
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
    "fatigue_score" -> "усталость"
    "recovery_debt" -> "долг"
    "user_fatigue_score" -> "оценка врача"
    "burnout_score" -> "CBI"
    else -> value
}

private data class GpsSettingsState(
    val serverUrl: String,
    val apiKey: String,
    val intervalSeconds: String,
    val gpsRunning: Boolean,
    val onServerUrlChange: (String) -> Unit,
    val onApiKeyChange: (String) -> Unit,
    val onIntervalChange: (String) -> Unit,
    val onSave: () -> Unit,
    val onStartGps: () -> Unit,
    val onStopGps: () -> Unit,
)
