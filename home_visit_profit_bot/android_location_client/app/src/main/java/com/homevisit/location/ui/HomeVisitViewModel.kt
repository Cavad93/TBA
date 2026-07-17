package com.homevisit.location.ui

import android.Manifest
import android.app.Application
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import com.homevisit.location.MainActivity
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.homevisit.location.OrderSource
import com.homevisit.location.settingText
import com.homevisit.location.data.HomeVisitRepository
import com.homevisit.location.ShareImageUi
import com.homevisit.location.domain.AnchorUpdate
import com.homevisit.location.domain.AppSettingsSnapshot
import com.homevisit.location.domain.ArchiveRange
import com.homevisit.location.domain.ArchiveSort
import com.homevisit.location.domain.ArchiveUiState
import com.homevisit.location.domain.ArchivedVisit
import com.homevisit.location.domain.OrderDetails
import com.homevisit.location.domain.archiveBounds
import com.homevisit.location.domain.archiveTimeText
import com.homevisit.location.domain.sortArchive
import com.homevisit.location.domain.AddressCandidate
import com.homevisit.location.domain.CandidateEstimate
import com.homevisit.location.domain.MinimumCheck
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
import com.homevisit.location.domain.NavTarget
import com.homevisit.location.domain.ParkingHint
import com.homevisit.location.domain.ServerRouteSnapshot
import com.homevisit.location.domain.StopLabel
import com.homevisit.location.domain.SyncConflict
import com.homevisit.location.domain.SyncQueueStats
import com.homevisit.location.domain.settingsSaveMessage
import com.homevisit.location.data.local.VisitEntity
import com.homevisit.location.domain.VisitKind
import com.homevisit.location.domain.VisitStatus
import com.homevisit.location.domain.WorkDayStatus
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import com.homevisit.location.domain.BatchOrder
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
    // Личная поездка (Ф11.5): та же форма адреса, но без дохода и вердикта — только
    // «во сколько обойдётся». Отдельный поток, чтобы не мешать состоянию оценки заказа.
    private val personalState = MutableStateFlow(PersonalTripUi())
    private val routeState = MutableStateFlow(RouteUiState())
    private var navCountdownJob: Job? = null
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

    // Пакет заказов из вставки/шаринга (Ф15.2). Отдельный поток — MainActivity читает
    // напрямую и показывает экран подтверждения; в общий uiState не мешаем.
    private val batchOrdersState = MutableStateFlow<List<BatchOrder>>(emptyList())
    val batchOrders: StateFlow<List<BatchOrder>> = batchOrdersState.asStateFlow()

    // Фото из «Поделиться» (Ф15.4): принято, разбирается, не нашлось адресов. Пустой
    // список заказов — не состояние: по нему не отличить «ещё считаем» от «не нашли».
    private val shareImageState = MutableStateFlow(ShareImageUi())
    val shareImage: StateFlow<ShareImageUi> = shareImageState.asStateFlow()

    // Архив закрытых заказов: период и сортировку выбирает человек, список тянется из
    // локальной базы по всем сменам (а не только по текущей).
    private val archiveRangeState = MutableStateFlow(ArchiveRange.Today)
    private val archiveSortState = MutableStateFlow(ArchiveSort.ByClosed)

    @OptIn(ExperimentalCoroutinesApi::class)
    val archive: StateFlow<ArchiveUiState> =
        combine(archiveRangeState, archiveSortState) { range, sort -> range to sort }
            .flatMapLatest { (range, sort) ->
                val (from, to) = archiveBounds(range)
                repository.observeArchive(from, to).map { rows ->
                    ArchiveUiState(
                        range = range,
                        sort = sort,
                        visits = sortArchive(rows.map { it.toArchivedVisit() }, sort),
                    )
                }
            }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ArchiveUiState())

    fun setArchiveRange(range: ArchiveRange) { archiveRangeState.value = range }

    fun setArchiveSort(sort: ArchiveSort) { archiveSortState.value = sort }

    // Открытый заказ (подробная карточка). null — карточка закрыта.
    private val openedOrderState = MutableStateFlow<String?>(null)

    @OptIn(ExperimentalCoroutinesApi::class)
    val openedOrder: StateFlow<OrderDetails?> = openedOrderState
        .flatMapLatest { id ->
            if (id == null) flowOf(null) else repository.observeVisit(id).map { it?.toOrderDetails() }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    fun openOrder(id: String) { openedOrderState.value = id }

    fun closeOrder() { openedOrderState.value = null }

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
                        breakHoursBefore = day.breakHoursBefore,
                        activeVisit = visits
                            .filter { it.status == VisitStatus.Accepted }
                            .minByOrNull { it.createdAtEpochMillis }
                            ?.let { RouteVisitUi.fromVisit(it) },
                        routeVisits = visits
                            .filter { it.status == VisitStatus.Accepted }
                            .sortedBy { it.createdAtEpochMillis }
                            .map { RouteVisitUi.fromVisit(it) },
                        recentAddresses = visits
                            .sortedByDescending { it.createdAtEpochMillis }
                            .map { it.address }
                            .filter { it.isNotBlank() }
                            .distinct()
                            .take(5),
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

    // Оценка заказа, личная поездка, архив и открытая карточка заказа складываются в
    // один мешок: у верхнего combine максимум 5 источников, и он уже занят целиком.
    private val evaluateState = combine(
        candidateState, personalState, archive, openedOrder,
    ) { candidate, personal, archiveUi, opened ->
        EvaluateBundle(candidate, personal, archiveUi, opened)
    }

    val uiState: StateFlow<HomeVisitUiState> = combine(dayState, evaluateState, operationalState, syncState, auxState) { day, evaluate, operational, sync, aux ->
        val candidate = evaluate.candidate
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
            personalTrip = evaluate.personal,
            archive = evaluate.archive,
            openedOrder = evaluate.opened,
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

    /**
     * Подтвердить, что оклад и премия не изменились. Одна кнопка, без ввода — спрашивать
     * человека заново то, что он уже вводил, незачем.
     */
    fun confirmIncome(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            repository.confirmIncome(serverUrl, apiKey)
            refreshProfile(serverUrl, apiKey)
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

    /**
     * Старт смены с главного экрана. `firstBreakHours` заполняется ТОЛЬКО на первой
     * смене: дальше перерыв считает сервер, от времени закрытия прошлой смены.
     */
    fun startShift(startOdometer: Double, firstBreakHours: Double) {
        viewModelScope.launch {
            // Адреса по умолчанию из настроек кладём сразу и в ЛОКАЛЬНЫЙ день: сервер
            // и так подставит их при синке, но карточки Ленты читают адрес из локальной
            // базы — пустота там выглядела как «мой адрес не сохранился».
            repository.startDay(
                startAddress = uiState.value.appSettings.settingText("default_start_address").ifBlank { null },
                finishAddress = uiState.value.appSettings.settingText("default_finish_address").ifBlank { null },
                startOdometer = startOdometer,
                breakHoursBefore = firstBreakHours,
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
    ) {
        viewModelScope.launch {
            repository.startDay(
                startAddress = startAddress,
                finishAddress = finishAddress,
                startOdometer = startOdometer,
            )
        }
    }

    /**
     * Начать день, прогнав старт и финиш через слой подсказок (P7).
     *
     * Координаты старта — фундамент всей оценки дня, а поля «Начала дня» шли на сервер
     * как есть: опечатка («Аваконструкторов 33») не находилась строгим геокодером, и
     * день стартовал вообще без координат — адрес оставался просто строкой.
     * Прощающий слой (learned-кеш + DaData) опечатку исправляет; уверенного ответа
     * нет — стартуем с тем, что ввёл человек: сервер попробует сам, и день начнётся
     * в любом случае. Начало смены нельзя блокировать разбором адреса.
     */
    fun startDayWithResolvedDetails(
        serverUrl: String,
        apiKey: String,
        startAddress: String,
        finishAddress: String,
        startOdometer: Double,
    ) {
        viewModelScope.launch {
            repository.startDay(
                startAddress = resolvedLabelOr(serverUrl, apiKey, startAddress),
                finishAddress = resolvedLabelOr(serverUrl, apiKey, finishAddress),
                startOdometer = startOdometer,
            )
        }
    }

    /** Нормализованный адрес от слоя подсказок или исходный текст, если уверенности нет. */
    private suspend fun resolvedLabelOr(serverUrl: String, apiKey: String, address: String): String {
        if (serverUrl.isBlank() || apiKey.isBlank() || address.isBlank()) return address
        val gps = lastKnownGps()
        val suggestion = repository.suggestAddress(serverUrl, apiKey, address, gps?.first, gps?.second)
        return suggestion.resolved?.label?.takeIf { it.isNotBlank() } ?: address
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

    // Запрос оценки, отложенный до выбора адреса из кандидатов (Фаза 2). Держим здесь
    // всё, что нужно, чтобы докрутить расчёт после тапа по варианту — без новых
    // параметров у экранного колбэка.
    private var pendingCandidate: PendingCandidate? = null

    /** Отложенная личная оценка: ждёт, пока человек выберет вариант адреса. */
    private var pendingPersonal: PendingPersonal? = null

    /** Отложенная смена старта/финиша: ждёт выбора варианта адреса в Ленте. */
    private var pendingAnchor: PendingAnchor? = null

    fun calculateVisitCandidate(
        serverUrl: String,
        apiKey: String,
        address: String,
        income: Double,
        clinic: String,
        routeKm: Double?,
        routeMinutes: Double?,
        orderSource: String? = null,
        responseCost: Double? = null,
    ) {
        viewModelScope.launch {
            ensureActiveDay()
            candidateState.value = CandidateUiState(isLoading = true)
            repository.syncPending(serverUrl, apiKey)

            // Ручной маршрут — человек уже разбирается с трудным адресом сам, подсказки
            // тут только помешают: считаем сразу. Иначе спрашиваем слои геокодинга.
            val hasManualRoute = routeKm != null && routeMinutes != null
            if (!hasManualRoute) {
                val gps = lastKnownGps()
                val suggestion = repository.suggestAddress(
                    serverUrl, apiKey, address, lat = gps?.first, lon = gps?.second,
                )
                if (suggestion.resolved == null && suggestion.candidates.isNotEmpty()) {
                    // Не уверены — пусть выберет человек (даже единственный вариант
                    // подтверждается одним тапом, а не подставляется молча и не
                    // теряется). Расчёт откладываем.
                    // Один взведённый выбор за раз: старое ожидание якоря/личной
                    // поездки не должно перехватить тап по кандидату заказа.
                    pendingAnchor = null
                    pendingPersonal = null
                    pendingCandidate = PendingCandidate(serverUrl, apiKey, address, income, clinic, orderSource, responseCost)
                    candidateState.value = CandidateUiState(
                        message = "Уточните адрес — выберите вариант",
                        addressCandidates = suggestion.candidates,
                        candidatesForAddress = address,
                    )
                    return@launch
                }
                if (suggestion.resolved != null) {
                    // Уверенный resolved — считаем сразу по его координатам.
                    runCandidate(serverUrl, apiKey, address, income, clinic, null, null,
                        suggestion.resolved.lat, suggestion.resolved.lon, orderSource, responseCost)
                    return@launch
                }
                // Ноль кандидатов без resolved — идём обычным путём: сервер сам
                // попробует геокодировать по названию.
            }
            runCandidate(serverUrl, apiKey, address, income, clinic, routeKm, routeMinutes, null, null, orderSource, responseCost)
        }
    }

    /**
     * Личная поездка (Ф11.5): «во сколько обойдётся съездить туда-обратно» — без дохода,
     * без вердикта. Текущую точку GPS шлём, если есть; иначе сервер считает от старта
     * смены (дома). Сеть/адрес не сложились — показываем человеку словами, не нулём.
     */
    fun runPersonalEstimate(serverUrl: String, apiKey: String, address: String) {
        if (address.isBlank()) return
        viewModelScope.launch {
            personalState.value = PersonalTripUi(isLoading = true)
            val gps = lastKnownGps()
            // Слоёные подсказки (Ф2) и здесь: DaData прощает опечатки, а неоднозначность
            // («Коменданский 17к1» похож и на Комендантский, и на Коломяжский) отдаём
            // человеку на выбор — как в рабочем режиме, а не тупик «не распознан».
            val suggestion = repository.suggestAddress(
                serverUrl, apiKey, address, lat = gps?.first, lon = gps?.second,
            )
            if (suggestion.resolved == null && suggestion.candidates.isNotEmpty()) {
                // Один взведённый выбор за раз (см. pickAddressCandidate).
                pendingAnchor = null
                pendingCandidate = null
                pendingPersonal = PendingPersonal(serverUrl, apiKey, address)
                personalState.value = PersonalTripUi(
                    message = "Уточните адрес — выберите вариант",
                    addressCandidates = suggestion.candidates,
                    candidatesForAddress = address,
                )
                return@launch
            }
            runPersonalQuick(
                serverUrl, apiKey, address, gps,
                suggestion.resolved?.lat, suggestion.resolved?.lon,
            )
        }
    }

    /** Достроить личную оценку: адрес и координаты, если слой подсказок их уже дал. */
    private suspend fun runPersonalQuick(
        serverUrl: String,
        apiKey: String,
        address: String,
        gps: Pair<Double, Double>?,
        destLat: Double?,
        destLon: Double?,
    ) {
        // mode=personal — по нему сервер решает, уместно ли сравнение с билетами (Ф11.6).
        val result = repository.quickEstimate(
            serverUrl, apiKey, address, gps?.first, gps?.second,
            mode = "personal", lat = destLat, lon = destLon,
        )
        personalState.value = if (result.check != null) {
            PersonalTripUi(result = result.check)
        } else {
            PersonalTripUi(message = personalEstimateMessage(result.reason))
        }
    }

    /** Тап по варианту адреса в личном режиме — докрутить оценку по его координатам. */
    private fun pickPersonalCandidate(candidate: AddressCandidate) {
        val pending = pendingPersonal ?: return
        pendingPersonal = null
        viewModelScope.launch {
            personalState.value = PersonalTripUi(isLoading = true)
            runPersonalQuick(
                pending.serverUrl, pending.apiKey, candidate.label,
                lastKnownGps(), candidate.lat, candidate.lon,
            )
        }
    }

    /** Сбросить результат личной поездки (переключение режима/новый адрес). */
    fun clearPersonalEstimate() {
        pendingPersonal = null
        personalState.value = PersonalTripUi()
    }

    private fun personalEstimateMessage(reason: String?): String = when (reason) {
        "no_address" -> "Введите адрес."
        "needs_coordinates" -> "Адрес не распознан по карте — уточните его."
        "needs_location" -> "Нет местоположения: включите GPS или начните смену от дома."
        "network_error" -> "Нет связи с сервером — попробуйте позже."
        else -> "Не удалось посчитать поездку."
    }

    /**
     * Последняя известная точка GPS (пишет LocationUploadService на каждом фиксе).
     * Шлём её в подсказки адреса, чтобы сервер понимал город по местоположению и не
     * заставлял указывать его руками. Старше часа не берём — человек мог уехать.
     */
    private fun lastKnownGps(): Pair<Double, Double>? {
        val prefs = getApplication<Application>()
            .getSharedPreferences(MainActivity.PREFS, Context.MODE_PRIVATE)
        val at = prefs.getLong(MainActivity.KEY_LAST_GPS_AT, 0L)
        if (at != 0L && System.currentTimeMillis() - at <= 60 * 60 * 1000L) {
            val lat = prefs.getString(MainActivity.KEY_LAST_GPS_LAT, null)?.toDoubleOrNull()
            val lon = prefs.getString(MainActivity.KEY_LAST_GPS_LON, null)?.toDoubleOrNull()
            if (lat != null && lon != null) return lat to lon
        }
        return systemLastKnownGps()
    }

    /**
     * Вне смены трекинг выключен и prefs пустые — берём последнюю известную точку у
     * самой системы (мгновенно, без нового замера и без расхода батареи). Возраст
     * ограничен двумя часами: GPS здесь лишь мягкая подсказка города, но совсем
     * устаревшая точка из другого города могла бы молча выбрать не тот адрес-дом.
     */
    private fun systemLastKnownGps(): Pair<Double, Double>? {
        val app = getApplication<Application>()
        if (app.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        ) {
            return null
        }
        val manager = app.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
            ?: return null
        val fresh = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            .mapNotNull { provider -> runCatching { manager.getLastKnownLocation(provider) }.getOrNull() }
            .filter { System.currentTimeMillis() - it.time <= 2 * 60 * 60 * 1000L }
            .maxByOrNull { it.time }
            ?: return null
        return fresh.latitude to fresh.longitude
    }

    /**
     * Человек выбрал адрес из кандидатов — докручиваем отложенный расчёт по координатам
     * выбранного варианта (уходят как ручная точка).
     */
    fun pickAddressCandidate(candidate: AddressCandidate) {
        // Кандидаты бывают из трёх потоков: смена старта/финиша в Ленте, личная
        // поездка и рабочая оценка. Взведён может быть только один одновременно.
        pendingAnchor?.let { anchor ->
            pendingAnchor = null
            viewModelScope.launch {
                routeState.value = routeState.value.copy(isLoading = true, anchorCandidates = emptyList(), anchorTarget = "")
                applyAnchorUpdate(anchor.serverUrl, anchor.apiKey, anchor.target, candidate.label, candidate.lat, candidate.lon)
            }
            return
        }
        if (pendingPersonal != null) {
            pickPersonalCandidate(candidate)
            return
        }
        val pending = pendingCandidate ?: return
        pendingCandidate = null
        viewModelScope.launch {
            candidateState.value = CandidateUiState(isLoading = true)
            runCandidate(
                pending.serverUrl, pending.apiKey, pending.address,
                pending.income, pending.clinic, null, null, candidate.lat, candidate.lon,
                pending.orderSource, pending.responseCost,
            )
        }
    }

    private suspend fun runCandidate(
        serverUrl: String,
        apiKey: String,
        address: String,
        income: Double,
        clinic: String,
        routeKm: Double?,
        routeMinutes: Double?,
        lat: Double?,
        lon: Double?,
        orderSource: String? = null,
        responseCost: Double? = null,
    ) {
        val result = repository.calculateVisitCandidate(
            serverUrl = serverUrl,
            apiKey = apiKey,
            address = address,
            income = income,
            clinic = clinic,
            routeKm = routeKm,
            routeMinutes = routeMinutes,
            lat = lat,
            lon = lon,
            orderSource = orderSource,
            responseCost = responseCost,
        )
        // Нет сети, но есть координаты кандидата и прогретый кеш матрицы дня —
        // мгновенный офлайн-вердикт по кешу (Фаза 3.4/3.5), сервер уточнит при связи.
        if (!result.ok && result.reason == "network_error" && lat != null && lon != null) {
            // responseCost обязателен и офлайн: человек ввёл цену лида на этом же
            // экране, а без неё знак маржи мог перевернуться (сервер −400, телефон +400).
            val offline = repository.offlineCandidateEstimate(
                lat, lon, income, address, clinic, responseCost ?: 0.0,
            )
            if (offline != null) {
                candidateState.value = CandidateUiState(
                    estimate = offline,
                    message = "Нет сети — офлайн-оценка по кешу. Сервер уточнит при связи.",
                )
                return
            }
        }
        candidateState.value = when {
            result.ok && result.estimate != null -> CandidateUiState(
                estimate = result.estimate,
                message = "Расчёт готов",
                parking = result.parking,
                warnings = result.warnings,
            )
            result.outsideCoverage -> CandidateUiState(
                // Не «ошибка», а честная граница: карты этого города у нас пока нет.
                // Молча подставить ноль километров было бы куда хуже — заказ выглядел
                // бы бесконечно выгодным.
                message = "Этот адрес пока вне покрытия наших карт. Введите километры и минуты дороги вручную.",
                needsManualRoute = true,
                warnings = result.warnings,
            )
            result.needsManualRoute -> CandidateUiState(
                message = "Нужно ввести километры и минуты дороги вручную.",
                needsManualRoute = true,
                warnings = result.warnings,
            )
            result.needsCoordinates -> CandidateUiState(
                // Сервер принимает ручные км/мин и без координат — предлагаем оба пути:
                // уточнить адрес (снова пройдёт через подсказки) или дать дорогу руками.
                message = "Сервер не нашёл адрес. Уточните его или введите километры и минуты вручную.",
                needsManualRoute = true,
                warnings = result.warnings,
            )
            result.reason == "geocoding_failed" -> CandidateUiState(
                // Сервис карт лёг по сети — раньше это был глухой тупик без плашки.
                // Ручные км/мин сервер примет и без геокодера.
                message = "Сервис карт недоступен. Введите километры и минуты вручную или повторите позже.",
                needsManualRoute = true,
                warnings = result.warnings,
            )
            else -> CandidateUiState(
                message = "Не удалось рассчитать адрес: ${result.reason}",
                warnings = result.warnings,
            )
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
                CandidateUiState(message = "Адрес принят", done = true)
            } else {
                // Провал оставляет estimate: человеку есть что повторить, и лист
                // остаётся открытым с честным заголовком ошибки.
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
                CandidateUiState(message = "Адрес отклонён", done = true)
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
                startAutoOpenIfEnabled()
            }
        }
    }

    /**
     * Закрыть заказ самому: человек долго простоял у адреса.
     *
     * Отличается от обычного «Готово» ровно одним — тем, что человек об этом не просил.
     * Поэтому закрытие показывается ему и откатывается одной кнопкой: простоять он мог
     * и в кафе напротив, а «долго простоял» — всего лишь догадка.
     */
    private fun autoCloseCurrentVisit(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            val activeVisit = uiState.value.activeVisit ?: return@launch
            val serverId = activeVisit.serverId ?: return@launch
            val ok = repository.completeVisit(serverUrl, apiKey, serverId)
            if (!ok) return@launch
            repository.markVisitStatus(activeVisit.localId, VisitStatus.Completed)
            gpsHintState.value = GpsHintUiState()
            routeState.update {
                it.copy(autoClosed = AutoClosed(visitId = serverId, address = activeVisit.address))
            }
            refreshRouteInternal(serverUrl, apiKey)
            startAutoOpenIfEnabled()
        }
    }

    /** Проверить, не пора ли закрыть заказ самому. Вызывается опросом с экрана Ленты. */
    fun checkAutoClose(serverUrl: String, apiKey: String) {
        val snapshot = routeState.value.snapshot ?: return
        if (!snapshot.navigation.autoClose) return
        if (routeState.value.autoClosed != null) return
        viewModelScope.launch {
            if (serverUrl.isBlank() || apiKey.isBlank()) return@launch
            val hint = repository.fetchCurrentGpsHint(serverUrl, apiKey) ?: return@launch
            gpsHintState.value = GpsHintUiState(hint = hint)
            if (hint.readyToComplete) {
                autoCloseCurrentVisit(serverUrl, apiKey)
            }
        }
    }

    /** Вернуть заказ, который приложение закрыло само. */
    fun undoAutoClose(serverUrl: String, apiKey: String) {
        val closed = routeState.value.autoClosed ?: return
        viewModelScope.launch {
            cancelPendingNav()
            val ok = repository.reopenVisit(serverUrl, apiKey, closed.visitId)
            routeState.update {
                it.copy(
                    autoClosed = null,
                    message = if (ok) "Заказ вернул в работу" else "Не удалось вернуть заказ",
                )
            }
            if (ok) {
                repository.markVisitStatus("server-${closed.visitId}", VisitStatus.Accepted)
                refreshRouteInternal(serverUrl, apiKey)
            }
        }
    }

    fun dismissAutoClose() {
        routeState.update { it.copy(autoClosed = null) }
    }

    /**
     * Отсчёт до автоматического запуска навигатора на следующий адрес.
     *
     * Приложение вот-вот заберёт экран себе — поэтому не «через мгновение», а с
     * видимым счётчиком и кнопкой «Не надо». Задержка берётся из настроек.
     */
    private fun startAutoOpenIfEnabled() {
        val snapshot = routeState.value.snapshot ?: return
        if (!snapshot.navigation.autoOpen) return
        val next = uiState.value.activeVisit ?: return
        val serverId = next.serverId ?: return
        val target = snapshot.navTargets[serverId] ?: return
        val seconds = snapshot.navigation.autoOpenDelaySeconds.coerceIn(3, 30)

        navCountdownJob?.cancel()
        routeState.update {
            it.copy(
                pendingNav = PendingNav(
                    target = target,
                    address = next.address,
                    secondsLeft = seconds,
                    totalSeconds = seconds,
                ),
            )
        }
        navCountdownJob = viewModelScope.launch {
            var left = seconds
            while (left > 0) {
                delay(1_000)
                left -= 1
                val pending = routeState.value.pendingNav ?: return@launch
                routeState.update { it.copy(pendingNav = pending.copy(secondsLeft = left)) }
            }
            // Дошли до нуля. Сам Intent запускает экран — у него есть Context.
        }
    }

    fun cancelPendingNav() {
        navCountdownJob?.cancel()
        navCountdownJob = null
        routeState.update { it.copy(pendingNav = null) }
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

    /**
     * Отменить ЛЮБОЙ заказ из очереди «Далее», а не только текущий.
     *
     * Раньше убрать можно было лишь активный вызов: если клиент отменился по третьему
     * адресу из очереди, заказ оставался в Ленте, тянул за собой километры и продолжал
     * портить оценку дня — а человеку некуда было нажать.
     */
    fun cancelVisitById(serverUrl: String, apiKey: String, localId: String) {
        viewModelScope.launch {
            val visit = uiState.value.routeVisits.firstOrNull { it.localId == localId } ?: return@launch
            val serverId = visit.serverId ?: return@launch
            val ok = repository.cancelVisit(serverUrl, apiKey, serverId)
            if (ok) {
                repository.markVisitStatus(visit.localId, VisitStatus.Cancelled)
                refreshRouteInternal(serverUrl, apiKey)
            }
        }
    }

    /** Отмена в пути (Ф11.3): клиент отменил, когда уже ехали — фиксируем потери на сервере. */
    fun cancelInRouteCurrentVisit(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            val activeVisit = uiState.value.activeVisit ?: return@launch
            val serverId = activeVisit.serverId ?: return@launch
            val ok = repository.cancelInRoute(serverUrl, apiKey, serverId)
            if (ok) {
                repository.markVisitStatus(activeVisit.localId, VisitStatus.Cancelled)
                gpsHintState.value = GpsHintUiState(message = "Отменён в пути — потери зафиксированы")
                refreshRouteInternal(serverUrl, apiKey)
            }
        }
    }

    fun refreshRoute(serverUrl: String, apiKey: String) {
        viewModelScope.launch {
            refreshRouteInternal(serverUrl, apiKey)
        }
    }

    /** Разобрать пришедший списком/шарингом текст в пакет заказов (Ф15.2). */
    fun parseSharedText(serverUrl: String, apiKey: String, text: String) {
        if (text.isBlank()) return
        viewModelScope.launch {
            batchOrdersState.value = repository.batchParse(serverUrl, apiKey, text)
        }
    }

    /** Разобрать пришедший скриншот в пакет заказов через наш OCR (Ф15.4).
     *
     * Состояние [shareImage] нужно, чтобы человек видел: фото принято и с ним что-то
     * происходит. Раньше единственной реакцией был экран пакета, который открывался
     * только при непустом результате: пока OCR считает — тишина, а если адресов не
     * нашлось — тишина навсегда, неотличимая от «приложение сломалось».
     */
    fun parseSharedImage(serverUrl: String, apiKey: String, image: ByteArray) {
        if (image.isEmpty()) return
        viewModelScope.launch {
            shareImageState.value = ShareImageUi(loading = true)
            val orders = repository.ocrExtract(serverUrl, apiKey, image)
            batchOrdersState.value = orders
            shareImageState.value = ShareImageUi(loading = false, failed = orders.isEmpty())
        }
    }

    /** Спрятать карточку принятого фото (человек её прочитал). */
    fun dismissSharedImage() {
        shareImageState.value = ShareImageUi()
    }

    /**
     * Записанный голос → текст через наш ASR (Ф14.4). Результат отдаём колбэком: поле
     * адреса — локальное состояние формы, туда и кладём распознанное (человек правит).
     */
    fun transcribeServerVoice(serverUrl: String, apiKey: String, audio: ByteArray, onResult: (String?) -> Unit) {
        if (audio.isEmpty()) {
            onResult(null)
            return
        }
        viewModelScope.launch {
            onResult(repository.transcribeAudio(serverUrl, apiKey, audio))
        }
    }

    fun clearBatch() {
        batchOrdersState.value = emptyList()
    }

    /** «Добавить все зелёные» (Ф15.2): распознанные заказы — сразу в работу, по одному calc+accept. */
    fun addBatchGreen(serverUrl: String, apiKey: String, greens: List<BatchOrder>) {
        viewModelScope.launch {
            val workDayId = ensureActiveDay()
            for (order in greens) {
                val resolved = order.resolved ?: continue
                val result = repository.calculateVisitCandidate(
                    serverUrl, apiKey, order.address, order.income ?: 0.0, "",
                    lat = resolved.lat, lon = resolved.lon,
                )
                if (result.ok && result.estimate != null) {
                    repository.acceptCandidate(serverUrl, apiKey, workDayId, result.estimate)
                }
            }
            batchOrdersState.value = emptyList()
            refreshRouteInternal(serverUrl, apiKey)
        }
    }

    fun updateFinish(serverUrl: String, apiKey: String, address: String) =
        updateAnchor(serverUrl, apiKey, target = "finish", address = address)

    fun updateStart(serverUrl: String, apiKey: String, address: String) =
        updateAnchor(serverUrl, apiKey, target = "start", address = address)

    /**
     * Смена старта/финиша через слой подсказок (Ф2), как у заказов: DaData прощает
     * опечатки, неоднозначность («Ленина 40» в двух городах) отдаём человеку на выбор,
     * а координаты resolved-варианта уходят на сервер — он тогда не может ответить
     * needs_coordinates, и адрес гарантированно сохраняется.
     */
    private fun updateAnchor(serverUrl: String, apiKey: String, target: String, address: String) {
        viewModelScope.launch {
            val what = if (target == "start") "старта" else "финиша"
            if (serverUrl.isBlank() || apiKey.isBlank()) {
                routeState.value = routeState.value.copy(message = "Заполните URL сервера и API ключ")
                return@launch
            }
            if (address.isBlank()) {
                routeState.value = routeState.value.copy(message = "Введите новый адрес $what")
                return@launch
            }
            pendingAnchor = null
            routeState.value = routeState.value.copy(
                isLoading = true,
                message = if (target == "start") "Меняю старт..." else "Меняю финиш...",
                anchorCandidates = emptyList(),
                anchorTarget = "",
            )
            val gps = lastKnownGps()
            val suggestion = repository.suggestAddress(serverUrl, apiKey, address, lat = gps?.first, lon = gps?.second)
            if (suggestion.resolved == null && suggestion.candidates.isNotEmpty()) {
                // Один взведённый выбор за раз (см. pickAddressCandidate).
                pendingCandidate = null
                pendingPersonal = null
                pendingAnchor = PendingAnchor(serverUrl, apiKey, target)
                routeState.value = routeState.value.copy(
                    isLoading = false,
                    message = "Уточните адрес $what — выберите вариант",
                    anchorCandidates = suggestion.candidates,
                    anchorTarget = target,
                )
                return@launch
            }
            applyAnchorUpdate(serverUrl, apiKey, target, address, suggestion.resolved?.lat, suggestion.resolved?.lon)
        }
    }

    /** Достроить смену старта/финиша: адрес и координаты (если слой подсказок их дал). */
    private suspend fun applyAnchorUpdate(
        serverUrl: String,
        apiKey: String,
        target: String,
        address: String,
        lat: Double?,
        lon: Double?,
    ) {
        val what = if (target == "start") "старта" else "финиша"
        val update = if (target == "start") {
            repository.updateDayStart(serverUrl, apiKey, address, lat, lon)
        } else {
            repository.updateDayFinish(serverUrl, apiKey, address, lat, lon)
        }
        val reason = update.reason
        val expected = if (target == "start") "start_updated" else "finish_updated"
        if (reason == expected) {
            // Храним НОРМАЛИЗОВАННЫЙ адрес с сервера, а не набранный текст: координаты
            // и там и там одни, но строки расходились, и один адрес выглядел на
            // телефоне и на сервере по-разному. Сервер не прислал — остаётся введённое.
            val stored = update.address ?: address
            // Локальная база — источник адреса для карточек Ленты: без этого успешная
            // правка выглядела «не сохранившейся».
            if (target == "start") {
                repository.updateLocalDayAddresses(startAddress = stored)
            } else {
                repository.updateLocalDayAddresses(finishAddress = stored)
            }
            // Запоминаем как адрес по умолчанию: следующая смена стартует с него.
            // Раньше адреса жили только внутри одного дня, а новая смена бралась из
            // настроек default_* — их никто не обновлял, и человек, задавший старт и
            // финиш вчера, сегодня снова видел «не задан» и вводил всё заново.
            val defaultKey = if (target == "start") "default_start_address" else "default_finish_address"
            repository.queueAppSettingsUpdate(mapOf(defaultKey to stored))
            refreshRouteInternal(serverUrl, apiKey)
            routeState.value = routeState.value.copy(
                message = if (target == "start") "Старт изменён, маршрут пересчитан" else "Финиш изменён, маршрут пересчитан",
                anchorCandidates = emptyList(),
                anchorTarget = "",
            )
            return
        }
        routeState.value = routeState.value.copy(
            isLoading = false,
            message = when (reason) {
                "needs_coordinates" -> "Сервер не нашёл адрес $what. Уточните адрес."
                "geocoding_failed" -> "Сервис карт недоступен — не удалось проверить адрес $what. Попробуйте позже."
                else -> "Не удалось изменить адрес $what"
            },
        )
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
            // Синк — фоном, НЕ на пути открытия мастера. Раньше он шёл первым и
            // синхронно: очередь может нести десятки событий, у каждого свой таймаут,
            // и всё это время человек смотрел в спиннер «Считаю итоги смены…», не имея
            // возможности просто закрыть смену. Отсюда «при закрытии смены подвисает».
            // Отправка догонит сама — очередь для того и есть.
            launch { repository.syncPending(serverUrl, apiKey) }
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
            val reason = repository.addOnSiteVisit(
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
                // «Адрес не распознан» и «нет сети» — разные проблемы: раньше обе
                // сливались в одно сообщение, и человек не знал, что чинить.
                message = when (reason) {
                    "ok" -> "Работа на точке добавлена в Ленту"
                    "needs_coordinates" -> "Адрес точки не распознан — уточните его (например, добавьте город)."
                    "geocoding_failed" -> "Сервис карт недоступен — попробуйте добавить точку позже."
                    "network_error" -> "Нет связи с сервером — попробуйте позже."
                    else -> "Не удалось добавить: проверьте адрес и связь"
                },
            )
            if (reason == "ok") {
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
            // Правда вместо безусловного «Настройки сохранены»: сервер применяет батч
            // поключево, и отвергнутое поле (кривая дата, число вне границ) человек
            // обязан увидеть — иначе он считает сохранённым то, что молча пропало.
            val outcome = repository.consumeSettingsSyncOutcome()
            val message = settingsSaveMessage(outcome)
            val snapshot = repository.fetchAppSettings(serverUrl, apiKey)
            appSettingsState.value = if (snapshot == null) {
                appSettingsState.value.copy(isLoading = false, message = message)
            } else {
                AppSettingsUiState(snapshot = snapshot, message = message)
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
            // Смена, начатая офлайн, локально без адресов и показывает «не задан», хотя
            // сервер их знает. Дозаполняем ТОЛЬКО пустое: правка человека новее и главнее.
            repository.fillMissingDayAddresses(route.startAddress, route.finishAddress)
            RouteUiState(snapshot = route, message = "Маршрут обновлён")
        }
        // Прогреваем кеш матрицы дня для офлайн-вердикта (Ф3.4/3.5) — ПОСЛЕ показа Ленты,
        // чтобы сетевой запрос не задерживал UI. Best-effort: набор точек дня меняется на
        // принял/выполнил/удалил, этот вызов едет на каждом обновлении и держит кеш свежим.
        repository.warmDayMatrix(serverUrl, apiKey)
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
    val breakHoursBefore: Double = 0.0,
    val candidate: CandidateUiState = CandidateUiState(),
    /** Личная поездка (Ф11.5): минимальный чек без дохода и вердикта. */
    val personalTrip: PersonalTripUi = PersonalTripUi(),
    /** Архив закрытых заказов под ползунком завершения смены. */
    val archive: ArchiveUiState = ArchiveUiState(),
    /** Открытая подробная карточка заказа. null — закрыта. */
    val openedOrder: OrderDetails? = null,
    val activeVisit: RouteVisitUi? = null,
    val routeVisits: List<RouteVisitUi> = emptyList(),
    /** Недавние уникальные адреса дня (Ф13.1): чипы над полем адреса — ввод в один тап. */
    val recentAddresses: List<String> = emptyList(),
    val serverRoute: RouteUiState = RouteUiState(),
    val gpsEstimate: GpsEstimateUiState = GpsEstimateUiState(),
    val endShift: EndShiftUiState = EndShiftUiState(),
    val gpsHint: GpsHintUiState = GpsHintUiState(),
    val report: ReportUiState = ReportUiState(),
    val workload: WorkloadUiState = WorkloadUiState(),
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

/**
 * Мешок для верхнего combine: у типизированной перегрузки максимум 5 источников, а их
 * больше. Сюда складываем то, что живёт вокруг оценки заказа.
 */
private data class EvaluateBundle(
    val candidate: CandidateUiState,
    val personal: PersonalTripUi,
    val archive: ArchiveUiState,
    val opened: OrderDetails?,
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
    /** Адрес в зоне платной парковки. Показываем ДО того, как человек нажал «Принять». */
    val parking: ParkingHint? = null,
    /** Сервер не уверен в адресе — 2–3 варианта на выбор (Фаза 2). Пусто = выбирать нечего. */
    val addressCandidates: List<AddressCandidate> = emptyList(),
    /** Для какого ввода даны кандидаты: правка адреса делает старый список неактуальным. */
    val candidatesForAddress: String = "",
    /** Оговорки честности оценки с сервера: нет старта смены, мало заказов в ленте. */
    val warnings: List<String> = emptyList(),
    /**
     * Заказ принят или отклонён — считать больше нечего.
     *
     * Без этого флага успех был неотличим от провала: у обоих `estimate == null`, и
     * лист показывал «Адрес принят» под заголовком «Не удалось рассчитать».
     */
    val done: Boolean = false,
)

/**
 * Состояние личной поездки (Ф11.5). `result` — посчитанный минимальный чек; `message` —
 * человеческое объяснение, когда посчитать нечем (нет адреса/координат/связи).
 */
data class PersonalTripUi(
    val isLoading: Boolean = false,
    val result: MinimumCheck? = null,
    val message: String = "",
    /** Сервер не уверен в адресе — 2–3 варианта на выбор (Фаза 2), как в рабочем режиме. */
    val addressCandidates: List<AddressCandidate> = emptyList(),
    /** Для какого ввода даны кандидаты: правка адреса делает старый список неактуальным. */
    val candidatesForAddress: String = "",
)

/** Отложенная личная поездка: всё, чтобы докрутить оценку после выбора варианта адреса. */
private data class PendingPersonal(
    val serverUrl: String,
    val apiKey: String,
    val address: String,
)

/** Отложенная смена старта/финиша: чей адрес меняем и куда слать выбор. */
private data class PendingAnchor(
    val serverUrl: String,
    val apiKey: String,
    val target: String,
)

/** Отложенный до выбора адреса запрос оценки: всё, чтобы докрутить расчёт после тапа. */
private data class PendingCandidate(
    val serverUrl: String,
    val apiKey: String,
    val address: String,
    val income: Double,
    val clinic: String,
    val orderSource: String? = null,
    val responseCost: Double? = null,
)

data class RouteUiState(
    val isLoading: Boolean = false,
    val snapshot: ServerRouteSnapshot? = null,
    val message: String = "",
    /** Идёт отсчёт до автоматического запуска навигатора. */
    val pendingNav: PendingNav? = null,
    /** Заказ закрылся сам по GPS — пока это здесь, закрытие можно откатить. */
    val autoClosed: AutoClosed? = null,
    /** Сервер не уверен в адресе старта/финиша — варианты на выбор одним тапом. */
    val anchorCandidates: List<AddressCandidate> = emptyList(),
    /** Чей это выбор: "start" или "finish" (пусто = вариантов нет). */
    val anchorTarget: String = "",
)

/** Отсчёт до автозапуска навигатора на следующий адрес. */
data class PendingNav(
    val target: NavTarget,
    val address: String,
    val secondsLeft: Int,
    val totalSeconds: Int,
)

/** Заказ, который приложение закрыло само. Держим id, чтобы вернуть его обратно. */
data class AutoClosed(
    val visitId: Int,
    val address: String,
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

/**
 * Строка архива из записи локальной базы.
 *
 * `updatedAtEpochMillis` — момент последней смены статуса, то есть когда заказ реально
 * закрылся: именно он и есть «время выполнения/отмены». Отклонённый заказ показываем
 * вместе с отменённым: для человека это одно и то же — «не поехал».
 */
/** Подробности заказа для карточки. Текст статуса — словами, а не именем enum. */
internal fun VisitEntity.toOrderDetails(): OrderDetails = OrderDetails(
    id = id,
    address = address,
    clinic = clinic,
    income = income,
    statusText = when (status) {
        VisitStatus.Completed -> "Выполнен"
        VisitStatus.Cancelled -> "Отменён"
        VisitStatus.Rejected -> "Отклонён при оценке"
        VisitStatus.Accepted -> "В работе"
        VisitStatus.Candidate -> "На оценке"
    },
    addedAtText = archiveTimeText(createdAtEpochMillis),
    // У активного заказа закрытия ещё не было: updatedAt — это последняя правка, и
    // показывать её как «закрыт» значило бы врать.
    closedAtText = if (status == VisitStatus.Accepted || status == VisitStatus.Candidate) {
        ""
    } else {
        archiveTimeText(updatedAtEpochMillis)
    },
    driveMinutes = actualDriveMinutes ?: estimatedDriveMinutes,
    onSiteMinutes = onSiteMinutes,
    plannedStartAt = plannedStartAt,
)

internal fun VisitEntity.toArchivedVisit(): ArchivedVisit = ArchivedVisit(
    id = id,
    address = address,
    clinic = clinic,
    income = income,
    done = status == VisitStatus.Completed,
    addedAtMillis = createdAtEpochMillis,
    closedAtMillis = updatedAtEpochMillis,
    addedAtText = archiveTimeText(createdAtEpochMillis),
    closedAtText = archiveTimeText(updatedAtEpochMillis),
)
