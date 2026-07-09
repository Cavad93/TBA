package com.homevisit.location.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.homevisit.location.data.HomeVisitRepository
import com.homevisit.location.domain.AppSettingsSnapshot
import com.homevisit.location.domain.CandidateEstimate
import com.homevisit.location.domain.Clinic
import com.homevisit.location.domain.EndDayDetails
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.FatigueCorrelationReport
import com.homevisit.location.domain.FatigueSnapshot
import com.homevisit.location.domain.GpsDayEstimate
import com.homevisit.location.domain.GpsVisitHint
import com.homevisit.location.domain.ReportPeriod
import com.homevisit.location.domain.ReportSnapshot
import com.homevisit.location.domain.ServerRouteSnapshot
import com.homevisit.location.domain.StopLabel
import com.homevisit.location.domain.SyncConflict
import com.homevisit.location.domain.SyncQueueStats
import com.homevisit.location.domain.VisitStatus
import com.homevisit.location.domain.WorkDayStatus
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@OptIn(ExperimentalCoroutinesApi::class)
class HomeVisitViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = HomeVisitRepository.create(application)
    private val candidateState = MutableStateFlow(CandidateUiState())
    private val routeState = MutableStateFlow(RouteUiState())
    private val gpsEstimateState = MutableStateFlow(GpsEstimateUiState())
    private val gpsHintState = MutableStateFlow(GpsHintUiState())
    private val reportState = MutableStateFlow(ReportUiState())
    private val fatigueState = MutableStateFlow(FatigueUiState())
    private val appSettingsState = MutableStateFlow(AppSettingsUiState())
    private val syncMessageState = MutableStateFlow("")
    private val backupExportState = MutableStateFlow<String?>(null)
    private val syncConflictState = MutableStateFlow<List<SyncConflict>>(emptyList())

    private val syncState = combine(repository.observeSyncQueueStats(), syncMessageState, backupExportState, syncConflictState) { stats, message, backupJson, conflicts ->
        SyncUiState(stats = stats, message = message, backupJson = backupJson, conflicts = conflicts)
    }

    private val dayState = repository.observeLatestWorkDay()
        .flatMapLatest { day ->
            if (day == null) {
                flowOf(HomeVisitUiState())
            } else {
                combine(
                    repository.observeVisits(day.id),
                    repository.observeOfficeEntries(day.id),
                    repository.observeTelemedEntries(day.id),
                    repository.observeExpenses(day.id),
                ) { visits, officeEntries, telemedEntries, expenses ->
                    HomeVisitUiState(
                        workDayId = day.id,
                        status = day.status,
                        visitsCount = visits.size,
                        officeCount = officeEntries.size,
                        telemedCount = telemedEntries.size,
                        expensesCount = expenses.size,
                        grossIncome = visits.sumOf { it.income } +
                            officeEntries.sumOf { it.income } +
                            telemedEntries.sumOf { it.income },
                        expensesAmount = expenses.sumOf { it.amount },
                        startAddress = day.startAddress.orEmpty(),
                        finishAddress = day.finishAddress.orEmpty(),
                        startOdometer = day.startOdometer,
                        endOdometer = day.endOdometer,
                        sleepHours = day.sleepHours,
                        sleepQuality = day.sleepQuality,
                        breakHoursBefore = day.breakHoursBefore,
                        activeVisit = visits
                            .filter { it.status == VisitStatus.Accepted }
                            .minByOrNull { it.createdAtEpochMillis }
                            ?.let { RouteVisitUi.fromVisit(it.id, it.address, it.clinic.title, it.income) },
                        routeVisits = visits
                            .filter { it.status == VisitStatus.Accepted }
                            .sortedBy { it.createdAtEpochMillis }
                            .map { RouteVisitUi.fromVisit(it.id, it.address, it.clinic.title, it.income) },
                    )
                }
            }
        }

    private val operationalState = combine(routeState, gpsEstimateState, gpsHintState, reportState, fatigueState) { route, gpsEstimate, gpsHint, report, fatigue ->
        OperationalUiState(route, gpsEstimate, gpsHint, report, fatigue)
    }

    val uiState: StateFlow<HomeVisitUiState> = combine(dayState, candidateState, operationalState, syncState, appSettingsState) { day, candidate, operational, sync, appSettings ->
        day.copy(
            candidate = candidate,
            serverRoute = operational.route,
            gpsEstimate = operational.gpsEstimate,
            gpsHint = operational.gpsHint,
            report = operational.report,
            fatigue = operational.fatigue,
            sync = sync,
            appSettings = appSettings,
        )
    }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = HomeVisitUiState(),
        )

    fun startDay() {
        viewModelScope.launch {
            repository.startDay()
        }
    }

    fun startDayWithDetails(
        startAddress: String,
        finishAddress: String,
        startOdometer: Double,
        sleepHours: Double,
        sleepQuality: Double,
        breakHoursBefore: Double,
    ) {
        viewModelScope.launch {
            repository.startDay(
                startAddress = startAddress,
                finishAddress = finishAddress,
                startOdometer = startOdometer,
                sleepHours = sleepHours,
                sleepQuality = sleepQuality,
                breakHoursBefore = breakHoursBefore,
            )
        }
    }

    fun endDay() {
        viewModelScope.launch {
            repository.endDay(uiState.value.workDayId)
        }
    }

    fun endDayWithOdometer(endOdometer: Double?) {
        viewModelScope.launch {
            repository.endDay(uiState.value.workDayId, endOdometer)
        }
    }

    fun endDayWithDetails(details: EndDayDetails) {
        viewModelScope.launch {
            repository.endDay(uiState.value.workDayId, details.endOdometer, details)
        }
    }

    fun addVisit(address: String, income: Double, clinic: Clinic) {
        viewModelScope.launch {
            val workDayId = ensureActiveDay()
            repository.addVisit(workDayId, address, income, clinic)
        }
    }

    fun calculateVisitCandidate(
        serverUrl: String,
        apiKey: String,
        address: String,
        income: Double,
        clinic: Clinic,
        routeKm: Double?,
        routeMinutes: Double?,
    ) {
        viewModelScope.launch {
            ensureActiveDay()
            candidateState.value = CandidateUiState(isLoading = true)
            repository.syncPending(serverUrl, apiKey)
            val result = repository.calculateVisitCandidate(
                serverUrl = serverUrl,
                apiKey = apiKey,
                address = address,
                income = income,
                clinic = clinic,
                routeKm = routeKm,
                routeMinutes = routeMinutes,
            )
            candidateState.value = when {
                result.ok && result.estimate != null -> CandidateUiState(
                    estimate = result.estimate,
                    message = "Расчёт готов",
                )
                result.needsManualRoute -> CandidateUiState(
                    message = "Нужно ввести километры и минуты дороги вручную.",
                    needsManualRoute = true,
                )
                result.needsCoordinates -> CandidateUiState(
                    message = "Сервер не нашёл адрес. Введите координаты вместо адреса.",
                )
                else -> CandidateUiState(
                    message = "Не удалось рассчитать адрес: ${result.reason}",
                )
            }
        }
    }

    fun acceptCandidate(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            val estimate = candidateState.value.estimate ?: return@launch
            val workDayId = ensureActiveDay()
            candidateState.update { it.copy(isLoading = true, message = "Принимаю адрес...") }
            val ok = repository.acceptCandidate(serverUrl, apiKey, workDayId, estimate)
            candidateState.value = if (ok) {
                refreshRouteInternal(serverUrl, apiKey)
                CandidateUiState(message = "Адрес принят")
            } else {
                CandidateUiState(estimate = estimate, message = "Не удалось принять адрес")
            }
        }
    }

    fun rejectCandidate(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            val estimate = candidateState.value.estimate ?: return@launch
            candidateState.update { it.copy(isLoading = true, message = "Отклоняю адрес...") }
            val ok = repository.rejectCandidate(serverUrl, apiKey, estimate.visitId)
            candidateState.value = if (ok) {
                CandidateUiState(message = "Адрес отклонён")
            } else {
                CandidateUiState(estimate = estimate, message = "Не удалось отклонить адрес")
            }
        }
    }

    fun clearCandidateMessage() {
        candidateState.value = CandidateUiState()
    }

    fun completeCurrentVisit(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            val activeVisit = uiState.value.activeVisit ?: return@launch
            val serverId = activeVisit.serverId ?: return@launch
            val ok = repository.completeVisit(serverUrl, apiKey, serverId)
            if (ok) {
                repository.markVisitStatus(activeVisit.localId, VisitStatus.Completed)
                gpsHintState.value = GpsHintUiState(message = "Адрес закрыт")
                refreshRouteInternal(serverUrl, apiKey)
            }
        }
    }

    fun cancelCurrentVisit(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            val activeVisit = uiState.value.activeVisit ?: return@launch
            val serverId = activeVisit.serverId ?: return@launch
            val ok = repository.cancelVisit(serverUrl, apiKey, serverId)
            if (ok) {
                repository.markVisitStatus(activeVisit.localId, VisitStatus.Cancelled)
                refreshRouteInternal(serverUrl, apiKey)
            }
        }
    }

    fun refreshRoute(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            refreshRouteInternal(serverUrl, apiKey)
        }
    }

    fun refreshGpsHint(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                gpsHintState.value = GpsHintUiState(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            gpsHintState.value = gpsHintState.value.copy(isLoading = true, message = "Проверяю GPS-стоянку...")
            val hint = repository.fetchCurrentGpsHint(serverUrl, apiKey)
            gpsHintState.value = if (hint == null) {
                GpsHintUiState(message = "GPS-стоянка по текущему адресу пока не найдена")
            } else {
                val message = if (hint.readyToComplete) "Можно закрыть адрес по GPS" else "GPS-стоянка ещё короткая"
                GpsHintUiState(hint = hint, message = message)
            }
        }
    }

    fun classifyCurrentStop(serverUrl: String, apiKey: String, label: StopLabel) {
        viewModelScope.launch {
            val activeVisit = uiState.value.activeVisit
            val serverId = activeVisit?.serverId
            if (serverId == null) {
                routeState.value = routeState.value.copy(message = "Нет текущего серверного адреса для уточнения остановки")
                return@launch
            }
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                routeState.value = routeState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            routeState.value = routeState.value.copy(isLoading = true, message = "Сохраняю тип остановки...")
            val message = repository.setVisitStopLabel(serverUrl, apiKey, serverId, label)
            routeState.value = routeState.value.copy(isLoading = false, message = message)
        }
    }

    fun refreshGpsEstimate(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                gpsEstimateState.value = GpsEstimateUiState(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            gpsEstimateState.value = gpsEstimateState.value.copy(isLoading = true, message = "Обновляю GPS-оценку...")
            val estimate = repository.fetchGpsDayEstimate(serverUrl, apiKey)
            gpsEstimateState.value = if (estimate == null) {
                GpsEstimateUiState(message = "Не удалось получить GPS-оценку дня")
            } else {
                GpsEstimateUiState(estimate = estimate, message = "GPS-оценка обновлена")
            }
        }
    }

    fun refreshActiveReport(serverUrl: String, apiKey: String, clinic: String? = null) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                reportState.value = ReportUiState(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            reportState.value = reportState.value.copy(isLoading = true, message = "Обновляю активный отчёт...")
            repository.syncPending(serverUrl, apiKey)
            val report = repository.fetchActiveReport(serverUrl, apiKey, clinic)
            reportState.value = if (report == null) {
                reportState.value.copy(isLoading = false, message = "Не удалось получить активный отчёт")
            } else {
                reportState.value.copy(
                    isLoading = false,
                    snapshot = report,
                    message = if (clinic == null) "Активный отчёт обновлён" else "Отчёт по клинике: $clinic",
                    selectedClinic = clinic,
                    availableClinics = if (clinic == null) report.clinics.map { it.clinic } else reportState.value.availableClinics,
                )
            }
        }
    }

    fun refreshStatsReport(serverUrl: String, apiKey: String, period: ReportPeriod, clinic: String? = null) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                reportState.value = ReportUiState(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            reportState.value = reportState.value.copy(isLoading = true, message = "Обновляю отчёт: ${period.title.lowercase()}...")
            repository.syncPending(serverUrl, apiKey)
            val report = repository.fetchStatsReport(serverUrl, apiKey, period, clinic)
            reportState.value = if (report == null) {
                reportState.value.copy(isLoading = false, message = "Не удалось получить отчёт за период")
            } else {
                reportState.value.copy(
                    isLoading = false,
                    snapshot = report,
                    message = if (clinic == null) "Отчёт обновлён" else "Отчёт по клинике: $clinic",
                    selectedClinic = clinic,
                    availableClinics = if (clinic == null) report.clinics.map { it.clinic } else reportState.value.availableClinics,
                )
            }
        }
    }

    fun refreshFatigue(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                fatigueState.value = FatigueUiState(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            fatigueState.value = fatigueState.value.copy(isLoading = true, message = "Обновляю усталость...")
            repository.syncPending(serverUrl, apiKey)
            val snapshot = repository.fetchFatigueSummary(serverUrl, apiKey)
            fatigueState.value = if (snapshot == null) {
                FatigueUiState(message = "Не удалось получить данные усталости")
            } else {
                fatigueState.value.copy(isLoading = false, snapshot = snapshot, message = "Усталость обновлена")
            }
        }
    }

    fun submitFatigueFeedback(serverUrl: String, apiKey: String, action: String, score: Double?) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                fatigueState.value = fatigueState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            fatigueState.value = fatigueState.value.copy(isLoading = true, message = "Сохраняю оценку...")
            val workDayId = fatigueState.value.snapshot?.workDayId
            val result = repository.saveFatigueFeedback(serverUrl, apiKey, action, score, workDayId)
            if (result == null) {
                fatigueState.value = fatigueState.value.copy(isLoading = false, message = "Не удалось сохранить оценку")
                return@launch
            }
            val snapshot = repository.fetchFatigueSummary(serverUrl, apiKey)
            fatigueState.value = fatigueState.value.copy(
                isLoading = false,
                snapshot = snapshot ?: fatigueState.value.snapshot,
                message = "Оценка сохранена: ${result.userScore.toInt()}/100, ошибка ${result.error.toInt()}, весов ${result.activeWeightsCount}",
            )
        }
    }

    fun refreshFatigueCorrelation(serverUrl: String, apiKey: String, days: Int) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                fatigueState.value = fatigueState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            fatigueState.value = fatigueState.value.copy(isLoading = true, message = "Считаю корреляции...")
            val report = repository.fetchFatigueCorrelation(serverUrl, apiKey, days)
            fatigueState.value = if (report == null) {
                fatigueState.value.copy(isLoading = false, message = "Не удалось получить корреляции")
            } else {
                fatigueState.value.copy(isLoading = false, correlation = report, message = "Корреляции за $days дней обновлены")
            }
        }
    }

    fun submitCbi(serverUrl: String, apiKey: String, answers: List<Int>) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                fatigueState.value = fatigueState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            fatigueState.value = fatigueState.value.copy(isLoading = true, message = "Сохраняю CBI...")
            val cbi = repository.saveCbi(serverUrl, apiKey, answers)
            if (cbi == null) {
                fatigueState.value = fatigueState.value.copy(isLoading = false, message = "Не удалось сохранить CBI")
                return@launch
            }
            val snapshot = repository.fetchFatigueSummary(serverUrl, apiKey)
            fatigueState.value = fatigueState.value.copy(
                isLoading = false,
                snapshot = snapshot ?: fatigueState.value.snapshot,
                message = "CBI сохранён: ${cbi.latestScore.toInt()}/100 (${cbi.level})",
            )
        }
    }

    fun addOffice(address: String, minutes: Double, income: Double, clinic: Clinic) {
        viewModelScope.launch {
            val workDayId = ensureActiveDay()
            repository.addOfficeEntry(workDayId, address, minutes, income, clinic)
        }
    }

    fun addTelemed(minutes: Double, income: Double, clinic: Clinic) {
        viewModelScope.launch {
            val workDayId = ensureActiveDay()
            repository.addTelemedEntry(workDayId, minutes, income, clinic)
        }
    }

    fun addExpense(category: ExpenseCategory, amount: Double, comment: String) {
        viewModelScope.launch {
            val workDayId = ensureActiveDay()
            repository.addExpense(workDayId, category, amount, comment)
        }
    }

    fun syncPending(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                syncMessageState.value = "Заполните URL сервера и API ключ"
                return@launch
            }
            syncMessageState.value = "Синхронизирую..."
            val sent = repository.syncPending(serverUrl, apiKey)
            syncMessageState.value = if (sent > 0) {
                "Отправлено событий: $sent"
            } else {
                "Новых отправленных событий нет"
            }
        }
    }

    fun exportBackup() {
        viewModelScope.launch {
            val backupJson = repository.exportBackupJson()
            backupExportState.value = backupJson
            syncMessageState.value = "Резервная копия готова"
        }
    }

    fun clearBackupExport() {
        backupExportState.value = null
    }

    fun importBackup(backupJson: String) {
        viewModelScope.launch {
            if (backupJson.isBlank()) {
                syncMessageState.value = "Вставьте JSON резервной копии"
                return@launch
            }
            try {
                val imported = repository.importBackupJson(backupJson)
                syncMessageState.value = "Импортировано записей: $imported"
            } catch (error: Exception) {
                syncMessageState.value = "Не удалось импортировать backup: ${error.message.orEmpty()}"
            }
        }
    }

    fun refreshSyncConflicts(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                syncMessageState.value = "Заполните URL сервера и API ключ"
                return@launch
            }
            val conflicts = repository.fetchSyncConflicts(serverUrl, apiKey)
            if (conflicts == null) {
                syncMessageState.value = "Не удалось получить журнал конфликтов"
                return@launch
            }
            syncMessageState.value = "Конфликтов в журнале: ${conflicts.size}"
            syncConflictState.value = conflicts
        }
    }

    fun refreshAppSettings(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                appSettingsState.update { it.copy(message = "Заполните URL сервера и API ключ") }
                return@launch
            }
            appSettingsState.update { it.copy(isLoading = true, message = "Загружаю настройки...") }
            val snapshot = repository.fetchAppSettings(serverUrl, apiKey)
            appSettingsState.value = if (snapshot == null) {
                AppSettingsUiState(message = "Не удалось получить настройки")
            } else {
                AppSettingsUiState(snapshot = snapshot, message = "Настройки обновлены")
            }
        }
    }

    fun saveAppSettings(serverUrl: String, apiKey: String, values: Map<String, Any?>) {
        viewModelScope.launch {
            if (values.isEmpty()) {
                appSettingsState.update { it.copy(message = "Нет изменений для сохранения") }
                return@launch
            }
            appSettingsState.update { it.copy(isLoading = true, message = "Сохраняю настройки...") }
            repository.queueAppSettingsUpdate(values)
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                appSettingsState.update {
                    it.copy(isLoading = false, message = "Настройки поставлены в очередь. Заполните URL/ключ для синхронизации.")
                }
                return@launch
            }
            repository.syncPending(serverUrl, apiKey)
            val snapshot = repository.fetchAppSettings(serverUrl, apiKey)
            appSettingsState.value = if (snapshot == null) {
                appSettingsState.value.copy(isLoading = false, message = "Настройки отправлены, но не удалось обновить экран")
            } else {
                AppSettingsUiState(snapshot = snapshot, message = "Настройки сохранены")
            }
        }
    }

    private suspend fun refreshRouteInternal(serverUrl: String, apiKey: String) {
        if (serverUrl.isBlank() || apiKey.isBlank()) {
            routeState.value = RouteUiState(message = "Заполните URL сервера и API ключ")
            return
        }
        routeState.value = routeState.value.copy(isLoading = true, message = "Обновляю маршрут...")
        val route = repository.fetchActiveRoute(serverUrl, apiKey)
        routeState.value = if (route == null) {
            RouteUiState(message = "Не удалось получить маршрут с сервера")
        } else {
            RouteUiState(snapshot = route, message = "Маршрут обновлён")
        }
    }

    private suspend fun ensureActiveDay(): String {
        val state = uiState.value
        if (state.status == WorkDayStatus.Active && state.workDayId != null) {
            return state.workDayId
        }
        return repository.startDay()
    }
}

data class HomeVisitUiState(
    val workDayId: String? = null,
    val status: WorkDayStatus = WorkDayStatus.NotStarted,
    val visitsCount: Int = 0,
    val officeCount: Int = 0,
    val telemedCount: Int = 0,
    val expensesCount: Int = 0,
    val grossIncome: Double = 0.0,
    val expensesAmount: Double = 0.0,
    val startAddress: String = "",
    val finishAddress: String = "",
    val startOdometer: Double = 0.0,
    val endOdometer: Double? = null,
    val sleepHours: Double = 0.0,
    val sleepQuality: Double = 0.0,
    val breakHoursBefore: Double = 0.0,
    val candidate: CandidateUiState = CandidateUiState(),
    val activeVisit: RouteVisitUi? = null,
    val routeVisits: List<RouteVisitUi> = emptyList(),
    val serverRoute: RouteUiState = RouteUiState(),
    val gpsEstimate: GpsEstimateUiState = GpsEstimateUiState(),
    val gpsHint: GpsHintUiState = GpsHintUiState(),
    val report: ReportUiState = ReportUiState(),
    val fatigue: FatigueUiState = FatigueUiState(),
    val sync: SyncUiState = SyncUiState(),
    val appSettings: AppSettingsUiState = AppSettingsUiState(),
) {
    val netIncome: Double
        get() = grossIncome - expensesAmount
}

private data class OperationalUiState(
    val route: RouteUiState,
    val gpsEstimate: GpsEstimateUiState,
    val gpsHint: GpsHintUiState,
    val report: ReportUiState,
    val fatigue: FatigueUiState,
)

data class RouteVisitUi(
    val localId: String,
    val serverId: Int?,
    val address: String,
    val clinic: String,
    val income: Double,
) {
    companion object {
        fun fromVisit(localId: String, address: String, clinic: String, income: Double): RouteVisitUi {
            return RouteVisitUi(
                localId = localId,
                serverId = localId.removePrefix("server-").toIntOrNull(),
                address = address,
                clinic = clinic,
                income = income,
            )
        }
    }
}

data class CandidateUiState(
    val isLoading: Boolean = false,
    val estimate: CandidateEstimate? = null,
    val message: String = "",
    val needsManualRoute: Boolean = false,
)

data class RouteUiState(
    val isLoading: Boolean = false,
    val snapshot: ServerRouteSnapshot? = null,
    val message: String = "",
)

data class GpsEstimateUiState(
    val isLoading: Boolean = false,
    val estimate: GpsDayEstimate? = null,
    val message: String = "",
)

data class GpsHintUiState(
    val isLoading: Boolean = false,
    val hint: GpsVisitHint? = null,
    val message: String = "",
)

data class ReportUiState(
    val isLoading: Boolean = false,
    val snapshot: ReportSnapshot? = null,
    val message: String = "",
    val selectedClinic: String? = null,
    val availableClinics: List<String> = emptyList(),
)

data class FatigueUiState(
    val isLoading: Boolean = false,
    val snapshot: FatigueSnapshot? = null,
    val correlation: FatigueCorrelationReport? = null,
    val message: String = "",
)

data class SyncUiState(
    val stats: SyncQueueStats = SyncQueueStats(),
    val message: String = "",
    val backupJson: String? = null,
    val conflicts: List<SyncConflict> = emptyList(),
)

data class AppSettingsUiState(
    val isLoading: Boolean = false,
    val snapshot: AppSettingsSnapshot? = null,
    val message: String = "",
)
