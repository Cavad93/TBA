package com.homevisit.location.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.homevisit.location.OrderSource
import com.homevisit.location.data.HomeVisitRepository
import com.homevisit.location.domain.AppSettingsSnapshot
import com.homevisit.location.domain.CandidateEstimate
import com.homevisit.location.domain.ClinicOptions
import com.homevisit.location.domain.EndDayDetails
import com.homevisit.location.domain.EndDayPreview
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.WorkloadCorrelationReport
import com.homevisit.location.domain.WorkloadSnapshot
import com.homevisit.location.domain.WorkloadTrendReport
import com.homevisit.location.domain.GpsDayEstimate
import com.homevisit.location.domain.GpsVisitHint
import com.homevisit.location.domain.HomeSnapshot
import com.homevisit.location.domain.ProfileSnapshot
import com.homevisit.location.domain.ShiftSnapshot
import com.homevisit.location.domain.ReportPeriod
import com.homevisit.location.domain.ReportSnapshot
import com.homevisit.location.domain.ServerRouteSnapshot
import com.homevisit.location.domain.StopLabel
import com.homevisit.location.domain.SyncConflict
import com.homevisit.location.domain.SyncQueueStats
import com.homevisit.location.data.local.VisitEntity
import com.homevisit.location.domain.VisitKind
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
    private val endShiftState = MutableStateFlow(EndShiftUiState())
    private val gpsHintState = MutableStateFlow(GpsHintUiState())
    private val reportState = MutableStateFlow(ReportUiState())
    private val workloadState = MutableStateFlow(WorkloadUiState())
    private val appSettingsState = MutableStateFlow(AppSettingsUiState())
    private val clinicsState = MutableStateFlow(ClinicOptions())
    private val syncMessageState = MutableStateFlow("")
    private val backupExportState = MutableStateFlow<String?>(null)
    private val syncConflictState = MutableStateFlow<List<SyncConflict>>(emptyList())
    private val homeStateFlow = MutableStateFlow(HomeUiState())
    private val shiftStateFlow = MutableStateFlow(ShiftUiState())
    private val profileStateFlow = MutableStateFlow(ProfileUiState())

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
                        breakUninterrupted = day.breakUninterrupted,
                        breakHoursBefore = day.breakHoursBefore,
                        activeVisit = visits
                            .filter { it.status == VisitStatus.Accepted }
                            .minByOrNull { it.createdAtEpochMillis }
                            ?.let { RouteVisitUi.fromVisit(it) },
                        routeVisits = visits
                            .filter { it.status == VisitStatus.Accepted }
                            .sortedBy { it.createdAtEpochMillis }
                            .map { RouteVisitUi.fromVisit(it) },
                    )
                }
            }
        }

    // combine принимает максимум пять потоков, поэтому оценку дня и состояние мастера
    // завершения сначала сводим в пару.
    private val estimatesState = combine(gpsEstimateState, endShiftState) { gpsEstimate, endShift ->
        gpsEstimate to endShift
    }

    private val operationalState = combine(routeState, estimatesState, gpsHintState, reportState, workloadState) { route, estimates, gpsHint, report, workload ->
        OperationalUiState(route, estimates.first, gpsHint, report, workload, estimates.second)
    }

    private val auxState = combine(appSettingsState, clinicsState, homeStateFlow, shiftStateFlow, profileStateFlow) { appSettings, clinics, home, shift, profile ->
        AuxUiState(appSettings, clinics, home, shift, profile)
    }

    val uiState: StateFlow<HomeVisitUiState> = combine(dayState, candidateState, operationalState, syncState, auxState) { day, candidate, operational, sync, aux ->
        // Порядок Ленты берём с сервера (order_number): он отражает и авто-оптимизацию,
        // и ручную перестановку. Без него список шёл бы по времени создания.
        val serverOrder = operational.route.snapshot?.order.orEmpty()
        val ordered = if (serverOrder.isEmpty()) {
            day.routeVisits
        } else {
            day.routeVisits.sortedBy { visit ->
                val index = serverOrder.indexOf(visit.serverId)
                if (index >= 0) index else Int.MAX_VALUE
            }
        }
        day.copy(
            routeVisits = ordered,
            // «Текущий заказ» — первый в этом же порядке, иначе кнопка «Готово»
            // закрывала бы не тот заказ, который показан сверху.
            activeVisit = ordered.firstOrNull() ?: day.activeVisit,
            candidate = candidate,
            serverRoute = operational.route,
            gpsEstimate = operational.gpsEstimate,
            gpsHint = operational.gpsHint,
            report = operational.report,
            workload = operational.workload,
            endShift = operational.endShift,
            sync = sync,
            appSettings = aux.appSettings,
            clinics = aux.clinics,
            home = aux.home,
            shift = aux.shift,
            profile = aux.profile,
        )
    }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = HomeVisitUiState(),
        )

    init {
        // Загружаем список клиник из локального кэша, чтобы формы работали офлайн.
        viewModelScope.launch {
            clinicsState.value = repository.loadCachedClinics()
        }
    }

    fun refreshClinics(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) return@launch
            clinicsState.value = repository.fetchClinics(serverUrl, apiKey)
        }
    }

    fun refreshHome(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                homeStateFlow.update { it.copy(loading = false) }
                return@launch
            }
            homeStateFlow.update { it.copy(loading = true, error = false) }
            val snapshot = repository.fetchHome(serverUrl, apiKey)
            homeStateFlow.value = HomeUiState(
                loading = false,
                snapshot = snapshot,
                error = snapshot == null,
            )
        }
    }

    fun refreshShift(serverUrl: String, apiKey: String, period: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                shiftStateFlow.update { it.copy(loading = false) }
                return@launch
            }
            shiftStateFlow.update { it.copy(loading = true, error = false, period = period) }
            val snapshot = repository.fetchShift(serverUrl, apiKey, period)
            shiftStateFlow.value = ShiftUiState(loading = false, snapshot = snapshot, error = snapshot == null, period = period)
        }
    }

    fun refreshProfile(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                profileStateFlow.update { it.copy(loading = false) }
                return@launch
            }
            profileStateFlow.update { it.copy(loading = true, error = false) }
            val snapshot = repository.fetchProfile(serverUrl, apiKey)
            profileStateFlow.value = ProfileUiState(loading = false, snapshot = snapshot, error = snapshot == null)
        }
    }

    /** Старт смены с главного экрана: без адресов, перерыв рассчитан автоматически. */
    fun startShift(startOdometer: Double, breakUninterrupted: Boolean, breakHoursBefore: Double) {
        viewModelScope.launch {
            repository.startDay(
                startOdometer = startOdometer,
                breakUninterrupted = breakUninterrupted,
                breakHoursBefore = breakHoursBefore,
            )
        }
    }

    fun startDay() {
        viewModelScope.launch {
            repository.startDay()
        }
    }

    fun startDayWithDetails(
        startAddress: String,
        finishAddress: String,
        startOdometer: Double,
        breakUninterrupted: Boolean,
        breakHoursBefore: Double,
    ) {
        viewModelScope.launch {
            repository.startDay(
                startAddress = startAddress,
                finishAddress = finishAddress,
                startOdometer = startOdometer,
                breakUninterrupted = breakUninterrupted,
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

    fun addVisit(address: String, income: Double, clinic: String) {
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
        clinic: String,
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

    fun updateFinish(serverUrl: String, apiKey: String, address: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                routeState.value = routeState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            if (address.isBlank()) {
                routeState.value = routeState.value.copy(message = "Введите новый адрес финиша")
                return@launch
            }
            routeState.value = routeState.value.copy(isLoading = true, message = "Меняю финиш...")
            when (repository.updateDayFinish(serverUrl, apiKey, address)) {
                "finish_updated" -> {
                    refreshRouteInternal(serverUrl, apiKey)
                    routeState.value = routeState.value.copy(message = "Финиш изменён, маршрут пересчитан")
                }
                "needs_coordinates" -> routeState.value = routeState.value.copy(isLoading = false, message = "Сервер не нашёл адрес финиша. Уточните адрес.")
                "geocoding_failed" -> routeState.value = routeState.value.copy(isLoading = false, message = "Не удалось геокодировать финиш")
                else -> routeState.value = routeState.value.copy(isLoading = false, message = "Не удалось изменить финиш")
            }
        }
    }

    fun updateStart(serverUrl: String, apiKey: String, address: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                routeState.value = routeState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            if (address.isBlank()) {
                routeState.value = routeState.value.copy(message = "Введите новый адрес старта")
                return@launch
            }
            routeState.value = routeState.value.copy(isLoading = true, message = "Меняю старт...")
            when (repository.updateDayStart(serverUrl, apiKey, address)) {
                "start_updated" -> {
                    refreshRouteInternal(serverUrl, apiKey)
                    routeState.value = routeState.value.copy(message = "Старт изменён, маршрут пересчитан")
                }
                "needs_coordinates" -> routeState.value = routeState.value.copy(isLoading = false, message = "Сервер не нашёл адрес старта. Уточните адрес.")
                "geocoding_failed" -> routeState.value = routeState.value.copy(isLoading = false, message = "Не удалось геокодировать старт")
                else -> routeState.value = routeState.value.copy(isLoading = false, message = "Не удалось изменить старт")
            }
        }
    }

    /** Ручная перестановка заказов (↑↓ в Ленте): сохраняем порядок и обновляем маршрут. */
    fun reorderRoute(serverUrl: String, apiKey: String, visitIds: List<Int>) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank() || visitIds.isEmpty()) {
                return@launch
            }
            routeState.value = routeState.value.copy(isLoading = true, message = "Меняю порядок...")
            if (repository.reorderRoute(serverUrl, apiKey, visitIds)) {
                refreshRouteInternal(serverUrl, apiKey)
                routeState.value = routeState.value.copy(message = "Порядок изменён")
            } else {
                routeState.value = routeState.value.copy(isLoading = false, message = "Не удалось изменить порядок")
            }
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

    /**
     * Готовит мастер завершения: спрашивает у сервера расчётные итоги смены.
     * Если сервер недоступен, мастер всё равно откроется — просто без подсказок.
     */
    fun prepareEndShift(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            endShiftState.value = EndShiftUiState(isLoading = true)
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                endShiftState.value = EndShiftUiState(message = "Нет связи с сервером — введите значения вручную")
                return@launch
            }
            repository.syncPending(serverUrl, apiKey)
            val preview = repository.fetchEndDayPreview(serverUrl, apiKey)
            endShiftState.value = if (preview == null) {
                EndShiftUiState(message = "Не удалось получить расчёт — введите значения вручную")
            } else {
                EndShiftUiState(preview = preview)
            }
        }
    }

    fun clearEndShift() {
        endShiftState.value = EndShiftUiState()
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
                    message = if (clinic == null) "Активный отчёт обновлён" else "Отчёт по ${OrderSource.current.datSingle}: $clinic",
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
                    message = if (clinic == null) "Отчёт обновлён" else "Отчёт по ${OrderSource.current.datSingle}: $clinic",
                    selectedClinic = clinic,
                    availableClinics = if (clinic == null) report.clinics.map { it.clinic } else reportState.value.availableClinics,
                )
            }
        }
    }

    fun refreshWorkload(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                workloadState.value = WorkloadUiState(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            workloadState.value = workloadState.value.copy(isLoading = true, message = "Обновляю нагрузку...")
            repository.syncPending(serverUrl, apiKey)
            val snapshot = repository.fetchWorkloadSummary(serverUrl, apiKey)
            workloadState.value = if (snapshot == null) {
                WorkloadUiState(message = "Не удалось получить данные нагрузки")
            } else {
                workloadState.value.copy(isLoading = false, snapshot = snapshot, message = "Нагрузка обновлена")
            }
        }
    }

    fun submitWorkloadFeedback(serverUrl: String, apiKey: String, action: String, score: Double?) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                workloadState.value = workloadState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            workloadState.value = workloadState.value.copy(isLoading = true, message = "Сохраняю оценку...")
            val workDayId = workloadState.value.snapshot?.workDayId
            val result = repository.saveWorkloadFeedback(serverUrl, apiKey, action, score, workDayId)
            if (result == null) {
                workloadState.value = workloadState.value.copy(isLoading = false, message = "Не удалось сохранить оценку")
                return@launch
            }
            val snapshot = repository.fetchWorkloadSummary(serverUrl, apiKey)
            workloadState.value = workloadState.value.copy(
                isLoading = false,
                snapshot = snapshot ?: workloadState.value.snapshot,
                message = "Оценка сохранена: ${result.userScore.toInt()}/100, ошибка ${result.error.toInt()}, весов ${result.activeWeightsCount}",
            )
        }
    }

    fun refreshWorkloadCorrelation(serverUrl: String, apiKey: String, days: Int) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                workloadState.value = workloadState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            workloadState.value = workloadState.value.copy(isLoading = true, message = "Считаю корреляции...")
            val report = repository.fetchWorkloadCorrelation(serverUrl, apiKey, days)
            workloadState.value = if (report == null) {
                workloadState.value.copy(isLoading = false, message = "Не удалось получить корреляции")
            } else {
                workloadState.value.copy(isLoading = false, correlation = report, message = "Корреляции за $days дней обновлены")
            }
        }
    }

    fun refreshWorkloadTrend(serverUrl: String, apiKey: String, days: Int) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                workloadState.value = workloadState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            workloadState.value = workloadState.value.copy(isLoading = true, message = "Загружаю тренд нагрузки...")
            val report = repository.fetchWorkloadTrend(serverUrl, apiKey, days)
            workloadState.value = if (report == null) {
                workloadState.value.copy(isLoading = false, message = "Не удалось получить тренд нагрузки")
            } else {
                workloadState.value.copy(isLoading = false, trend = report, message = "Тренд за ${report.days} дн. обновлён")
            }
        }
    }

    fun submitSurvey(serverUrl: String, apiKey: String, answers: List<Int>) {
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                workloadState.value = workloadState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            workloadState.value = workloadState.value.copy(isLoading = true, message = "Сохраняю индекс восст....")
            val survey = repository.saveSurvey(serverUrl, apiKey, answers)
            if (survey == null) {
                workloadState.value = workloadState.value.copy(isLoading = false, message = "Не удалось сохранить индекс восст.")
                return@launch
            }
            val snapshot = repository.fetchWorkloadSummary(serverUrl, apiKey)
            workloadState.value = workloadState.value.copy(
                isLoading = false,
                snapshot = snapshot ?: workloadState.value.snapshot,
                message = "Опрос сохранён: ${survey.latestScore.toInt()}/100 (${survey.level})",
            )
        }
    }

    /**
     * Работа на точке. Уходит на сервер сразу: он геокодирует адрес и ставит точку
     * в маршрут — без этого дорога до неё не считалась бы, а в Ленте её бы не было.
     */
    fun addOnSite(
        serverUrl: String,
        apiKey: String,
        address: String,
        minutes: Double,
        income: Double,
        clinic: String,
        startAt: String?,
        endAt: String?,
    ) {
        viewModelScope.launch {
            val workDayId = ensureActiveDay()
            routeState.value = routeState.value.copy(isLoading = true, message = "Добавляю работу на точке...")
            val ok = repository.addOnSiteVisit(
                serverUrl = serverUrl,
                apiKey = apiKey,
                workDayId = workDayId,
                address = address,
                income = income,
                serviceMinutes = minutes,
                clinic = clinic,
                startAt = startAt,
                endAt = endAt,
            )
            routeState.value = routeState.value.copy(
                isLoading = false,
                message = if (ok) "Работа на точке добавлена в Ленту" else "Не удалось добавить: проверьте адрес и связь",
            )
            if (ok) {
                refreshRoute(serverUrl, apiKey)
            }
        }
    }


    fun addTelemed(minutes: Double, income: Double, clinic: String) {
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

    fun checkConnection(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            syncMessageState.value = "Проверяю связь..."
            syncMessageState.value = repository.checkConnection(serverUrl, apiKey)
        }
    }

    fun clearCache() {
        viewModelScope.launch {
            syncMessageState.value = "Очищаю кэш адресов..."
            val cleared = repository.clearAddressCache()
            syncMessageState.value = if (cleared > 0) {
                "Кэш адресов очищен: удалено записей — $cleared"
            } else {
                "Кэш адресов уже пуст"
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
            clinicsState.value = repository.loadCachedClinics()
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
            clinicsState.value = repository.loadCachedClinics()
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
    val breakUninterrupted: Boolean = true,
    val breakHoursBefore: Double = 0.0,
    val candidate: CandidateUiState = CandidateUiState(),
    val activeVisit: RouteVisitUi? = null,
    val routeVisits: List<RouteVisitUi> = emptyList(),
    val serverRoute: RouteUiState = RouteUiState(),
    val gpsEstimate: GpsEstimateUiState = GpsEstimateUiState(),
    val endShift: EndShiftUiState = EndShiftUiState(),
    val gpsHint: GpsHintUiState = GpsHintUiState(),
    val report: ReportUiState = ReportUiState(),
    val fatigue: WorkloadUiState = WorkloadUiState(),
    val sync: SyncUiState = SyncUiState(),
    val appSettings: AppSettingsUiState = AppSettingsUiState(),
    val clinics: ClinicOptions = ClinicOptions(),
    val home: HomeUiState = HomeUiState(),
    val shift: ShiftUiState = ShiftUiState(),
    val profile: ProfileUiState = ProfileUiState(),
) {
    val netIncome: Double
        get() = grossIncome - expensesAmount
}

private data class OperationalUiState(
    val route: RouteUiState,
    val gpsEstimate: GpsEstimateUiState,
    val gpsHint: GpsHintUiState,
    val report: ReportUiState,
    val workload: WorkloadUiState,
    val endShift: EndShiftUiState,
)

/** Расчётные итоги смены для мастера завершения. */
data class EndShiftUiState(
    val isLoading: Boolean = false,
    val preview: EndDayPreview? = null,
    val message: String = "",
)

private data class AuxUiState(
    val appSettings: AppSettingsUiState,
    val clinics: ClinicOptions,
    val home: HomeUiState,
    val shift: ShiftUiState,
    val profile: ProfileUiState,
)

data class RouteVisitUi(
    val localId: String,
    val serverId: Int?,
    val address: String,
    val clinic: String,
    val income: Double,
    val kind: VisitKind = VisitKind.Field,
    val plannedStartAt: String? = null,
    val plannedEndAt: String? = null,
    val serviceMinutes: Double? = null,
) {
    /** Работа на точке — заказ с фиксированным временем: оптимизатор его не двигает. */
    val isAnchor: Boolean get() = kind == VisitKind.OnSite

    companion object {
        fun fromVisit(visit: VisitEntity): RouteVisitUi {
            return RouteVisitUi(
                localId = visit.id,
                serverId = visit.id.removePrefix("server-").toIntOrNull(),
                address = visit.address,
                clinic = visit.clinic,
                income = visit.income,
                kind = visit.kind,
                plannedStartAt = visit.plannedStartAt,
                plannedEndAt = visit.plannedEndAt,
                serviceMinutes = visit.serviceMinutes,
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

data class WorkloadUiState(
    val isLoading: Boolean = false,
    val snapshot: WorkloadSnapshot? = null,
    val correlation: WorkloadCorrelationReport? = null,
    val trend: WorkloadTrendReport? = null,
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

data class HomeUiState(
    val loading: Boolean = false,
    val snapshot: HomeSnapshot? = null,
    val error: Boolean = false,
)

data class ShiftUiState(
    val loading: Boolean = false,
    val snapshot: ShiftSnapshot? = null,
    val error: Boolean = false,
    val period: String = "day",
)

data class ProfileUiState(
    val loading: Boolean = false,
    val snapshot: ProfileSnapshot? = null,
    val error: Boolean = false,
)
