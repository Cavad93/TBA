package com.homevisit.location.domain

/**
 * Клиники не захардкожены: доступный список приходит из настроек сервера
 * (ключи `clinics` / `telemed_clinics`) и может содержать любое число клиник.
 */
data class ClinicOptions(
    val all: List<String> = emptyList(),
    val telemed: List<String> = emptyList(),
)

enum class WorkDayStatus {
    NotStarted,
    Active,
    Closed,
}

enum class VisitStatus {
    Candidate,
    Accepted,
    Completed,
    Rejected,
    Cancelled,
}

/**
 * Тип заказа. `OnSite` — работа на точке: адрес с фиксированным временем начала и
 * окончания. В Ленте он якорь — оптимизатор его не переставляет.
 */
enum class VisitKind(val apiValue: String) {
    Field("field"),
    OnSite("onsite");

    companion object {
        fun fromApi(value: String?): VisitKind =
            entries.firstOrNull { it.apiValue == value } ?: Field
    }
}

enum class ExpenseCategory(val title: String) {
    Meal("Еда"),
    Coffee("Кофе/энергетик"),
    Drinks("Вода/напитки"),
    Parking("Парковка"),
    Toll("Платная дорога"),
    Fuel("Топливо"),
    Other("Прочее"),
}

enum class StopLabel(val apiValue: String, val title: String) {
    Pause("pause", "Обед/пауза"),
    Waiting("waiting", "Ожидание"),
    Normal("normal", "Обычный"),
    Heavy("heavy", "Тяжёлый"),
    Conflict("conflict", "Конфликтный"),
}

enum class ReportPeriod(val apiValue: String, val title: String) {
    Day("day", "День"),
    Month("month", "Месяц"),
    Year("year", "Год"),
}

/** Сводка главного экрана «Штурвал» — приходит одним запросом `GET /api/home`. */
data class HomeSnapshot(
    val nickname: String,
    val date: String,
    val firstRun: Boolean,
    val hasData: Boolean,
    val shiftActive: Boolean,
    val shiftWorkDayId: Int?,
    val startPrompt: HomeStartPrompt,
    val recovery: HomeOverwork?,
    val pricing: OverworkPricing?,
    val monthMoney: HomeMoney,
    val yesterdayMoney: HomeMoney,
    val hourlyVsMonth: Double,
    val debtVsPrev: Double?,
    val greenStreak: Int,
    val recommendations: List<HomeRecommendation>,
    val fromCache: Boolean = false,
)

/**
 * Что подставить в форму старта смены. Перерыв между сменами не спрашивается — он
 * вычисляется на сервере: это промежуток между закрытием прошлой смены и «сейчас».
 * Достаточность перерыва тоже выводится, по норме междусменного отдыха (не менее
 * двойной продолжительности прошлой смены). Человеку остаётся подтвердить одометр.
 */
data class HomeStartPrompt(
    val hasLastOdometer: Boolean,
    val lastOdometer: Double,
    val hasPreviousShift: Boolean,
    val prevEndedAt: String?,
    val prevShiftHours: Double,
    val breakHours: Double,
    val requiredBreakHours: Double,
    val breakDeficitHours: Double,
    val isShort: Boolean,
    val explanation: String,
)

/** Состояние восстановления. `verdict` — go/edge/skip для окраски. */
data class HomeOverwork(
    val overworkIndex: Double,
    val workloadSurveyScore: Double,
    val workloadIndex: Double,
    val weeklyAverage: Double,
    val level: String,
    val verdict: String,
    val source: String,
)

data class HomeMoney(
    val gross: Double,
    val net: Double,
    val netHourly: Double,
    val days: Int,
)

data class HomeRecommendation(
    val kind: String,
    val tone: String,
    val title: String,
    val text: String,
)

// --- Экран «Смена» (GET /api/shift) ---

data class ShiftSnapshot(
    val period: String,
    val today: ShiftToday,
    val goal: ShiftGoal,
    val bars: List<ShiftBar>,
    val recent: List<ShiftOrder>,
    val fromCache: Boolean = false,
)

data class ShiftToday(
    val active: Boolean,
    val gross: Double,
    val net: Double,
    val netHourly: Double,
    val visits: Int,
    val workHours: Double,
)

/** daily/suggested = null, если не задано/нет истории. */
data class ShiftGoal(
    val daily: Double?,
    val suggested: Double?,
    val progress: Double?,
)

data class ShiftBar(
    val label: String,
    val value: Double,
)

data class ShiftOrder(
    val label: String,
    val income: Double,
    val verdict: String, // go/edge/skip/""
)

// --- Экран «Профиль» (GET /api/profile) ---

data class ProfileSnapshot(
    val user: ProfileUser,
    val month: ProfileMonth,
    val indices: ProfileIndices,
    val pricing: OverworkPricing?,
    val vehicle: VehicleCost?,
    val income: IncomeModel?,
    val wellbeing: ProfileWellbeing,
    val driving: ProfileDriving?,
    val fromCache: Boolean = false,
)

/**
 * Три индекса. Каждый считается как отклонение от личной нормы человека, а не по
 * абсолютным порогам: двенадцать адресов — перегруз для одного и обычный вторник
 * для другого.
 */
data class ProfileIndices(
    val hasData: Boolean,
    val days: Int,
    val needMoreShifts: Int,
    val economy: IndexCard?,
    val load: IndexCard?,
    val recovery: IndexCard?,
)

data class IndexCard(
    val key: String,
    val title: String,
    val score: Double,
    val level: String,
    val tone: String,
    val advice: String,
    val why: List<IndexReason>,
)

/** «Сон 5,5 ч — на 21% меньше твоей нормы (7 ч): +12 к долгу». */
data class IndexReason(
    val metric: String,
    val title: String,
    val points: Double,
    val text: String,
)

/** Во что состояние обходится в деньгах: обычный минимум против сегодняшнего. */
data class OverworkPricing(
    val debt: Double,
    val markupPercent: Int,
    val baseMinHourly: Int,
    val effectiveMinHourly: Int,
    val changed: Boolean,
    val blocksOutsideZone: Boolean,
    val reason: String,
)

data class ProfileUser(
    val nickname: String,
    val occupation: String,
    val daysInService: Int?,
)

data class ProfileMonth(
    val avgOnSiteMin: Double,
    val avgRouteMin: Double,
    val netHourly: Double,
    val visits: Int,
)

data class ProfileWellbeing(
    val hasData: Boolean,
    val recovery: WellbeingGauge,
    val load: WellbeingGauge,
    val reserve: WellbeingGauge,
    val note: String,
)

/** percent = null, если данных ещё нет. */
data class WellbeingGauge(
    val percent: Int?,
    val label: String,
)

/**
 * Метрики «превышение скорости» здесь нет намеренно: чтобы знать превышение, нужен
 * лимит дороги, а мы его ниоткуда не берём. Раньше она приходила захардкоженным нулём —
 * то есть пользователю показывалась выдуманная цифра.
 */
data class ProfileDriving(
    val score10: Double,
    val smoothAccelPct: Int,
    val smoothBrakePct: Int,
    val harshBrakesPer100km: Double,
    val harshAccelPer100km: Double,
    val rating: DrivingRating,
    val withinDay: DrivingWithinDay?,
)

/** «После 5-го адреса стиль вождения стал менее стабильным». */
data class DrivingWithinDay(
    val turningPoint: Int,
    val earlyScore: Double,
    val lateScore: Double,
    val delta: Double,
    val text: String,
)

data class DrivingRating(
    val stars: Int,
    val deltaPct: Double,
    val text: String,
)

data class WorkDaySummary(
    val status: WorkDayStatus = WorkDayStatus.NotStarted,
    val visitsCount: Int = 0,
    val officeCount: Int = 0,
    val telemedCount: Int = 0,
    val grossIncome: Double = 0.0,
    val netHourlyIncome: Double = 0.0,
    val workloadIndex: Double = 0.0,
)

data class VisitDraft(
    val address: String = "",
    val income: Double = 0.0,
    val clinic: String? = null,
)

data class CandidateEstimate(
    val visitId: Int,
    val address: String,
    val income: Double,
    val clinic: String,
    val decision: String,
    val reason: String,
    val score: Int,
    val requiredExtraPayment: Double,
    val requiredCandidateIncome: Double,
    val beforeHourly: Double,
    val afterHourly: Double,
    val marginalHourly: Double,
    // Деньги на километр — рядом с деньгами на час. Порознь обманчивы: короткий
    // дорогой заказ в соседнем доме даёт огромные ₽/км и нулевые ₽/ч.
    val marginalPerKm: Double = 0.0,
    val costPerKm: Double = 0.0,
    val extraKm: Double,
    val extraDriveMinutes: Double,
    val workloadLevel: String,
    // Состояние поднимает МИНИМАЛЬНЫЙ ТАРИФ, а не добавляет отдельную надбавку.
    // Прежнее поле REMOVED_fatigueExtraPayment приходило с сервера и не показывалось ни на
    // одном экране; складывать его с поднятым порогом значило бы взять наценку дважды.
    val baseMinHourly: Double = 0.0,
    val effectiveMinHourly: Double = 0.0,
    val overworkMarkupPercent: Int = 0,
    val overworkBlocksOutsideZone: Boolean = false,
) {
    /** Минимум сегодня выше обычного — это надо показать на экране Оценки. */
    val tariffRaised: Boolean get() = overworkMarkupPercent > 0 && effectiveMinHourly > baseMinHourly
}

data class CandidateRequestResult(
    val ok: Boolean,
    val reason: String,
    val estimate: CandidateEstimate? = null,
    val detail: String = "",
) {
    val needsManualRoute: Boolean
        get() = reason == "needs_manual_route"

    val needsCoordinates: Boolean
        get() = reason == "needs_coordinates"
}

data class ServerRouteSnapshot(
    val visitsCount: Int,
    val totalKm: Double,
    val totalMinutes: Double,
    val legs: List<ServerRouteLeg>,
    /** Сохранённый на сервере порядок принятых заказов (id визитов) — по нему
     *  сортируется Лента: отражает и авто-оптимизацию, и ручную перестановку. */
    val order: List<Int> = emptyList(),
    /** Работы на точке, к которым по текущему порядку Ленты уже не успеваем. */
    val lateWarnings: List<LateWarning> = emptyList(),
    /** Готовая ссылка «Поехали» по каждому заказу — приходит с сервера вместе с маршрутом,
     *  поэтому кнопка работает и без сети. Ключ — серверный id заказа. */
    val navTargets: Map<Int, NavTarget> = emptyMap(),
    /** Сколько заказ приносит чистыми, по нашему расчёту. Ключ — серверный id заказа. */
    val netByVisitId: Map<Int, Double> = emptyMap(),
    val navigation: NavigationPrefs = NavigationPrefs(),
    val fromCache: Boolean = false,
) {
    fun legFor(visitId: Int?): ServerRouteLeg? =
        if (visitId == null) null else legs.firstOrNull { it.visitId == visitId }
}

/**
 * Ссылка «Поехали» по одному заказу.
 *
 * Собрана и подписана сервером: приватный ключ Яндекса в приложении не хранится.
 * Телефону остаётся только открыть её.
 */
data class NavTarget(
    val url: String,
    val fallbackUrl: String,
    val app: String,
    val packageName: String,
    val signed: Boolean,
    /** Координаты текстом — их кладём в буфер, когда переходы за сутки кончились. */
    val coordinates: String = "",
)

/** Настройки навигатора: чем ехать и что приложение делает само. */
data class NavigationPrefs(
    val app: String = "yandex_navi",
    val autoOpen: Boolean = false,
    val autoOpenDelaySeconds: Int = 7,
    val autoClose: Boolean = false,
    val signed: Boolean = false,
)

/** «К приёму на Ленина, 40 в 9:00 не успеваете: приедете к 10:15». */
data class LateWarning(
    val visitId: Int,
    val address: String,
    val plannedStartAt: String,
    val etaAt: String,
    val lateMinutes: Int,
)

data class ServerRouteLeg(
    val fromLabel: String,
    val toLabel: String,
    val visitId: Int?,
    val km: Double,
    val minutes: Double,
)

data class EndDayDetails(
    val actualKm: Double,
    val totalWorkMinutes: Double,
    val actualRouteMinutes: Double,
    val completedVisitsCount: Int,
    val startOdometer: Double,
    val endOdometer: Double,
    val fuelExpenses: Double,
    val fuelLiters: Double,
    val fuelConsumptionLitersPer100Km: Double,
    val fuelCompensation: Double,
    val parkingCompensation: Double,
    val tollExpenses: Double,
    val tollCompensation: Double,
    val otherExpenses: Double,
    val userWorkloadIndex: Double?,
    val foodMealExpenses: Double = 0.0,
    val coffeeExpenses: Double = 0.0,
    val drinksExpenses: Double = 0.0,
    val parkingExpenses: Double = 0.0,
    // Еда и питьё — ТОЛЬКО рубли. Количество чашек кофе это физиологический вход,
    // из которого выводится состояние человека, а значит специальная категория
    // персональных данных (152-ФЗ, ст. 10).
    //
    // Загруженность смены 1–10 — оценка УСЛОВИЙ ТРУДА, а не самочувствия. Она же
    // обратная связь: сравнивая её с нашей, система подстраивается под человека.
    val workloadRating: Double = 0.0,
    // Ремонт, ТО, шины, страховка — из них считается настоящий коэффициент износа.
    val vehicleExpenses: Double = 0.0,
    val vehicleRent: Double = 0.0,
    // Халтура, разовая премия — доход, который не пришёл заказом.
    val extraIncome: Double = 0.0,
)

/**
 * Расчётные итоги смены с сервера: их мастер показывает на подтверждение, чтобы
 * пользователь не вводил цифры с нуля.
 */
data class EndDayPreview(
    val gpsKm: Double,
    val plannedKm: Double,
    val suggestedKm: Double,
    val kmSource: String,
    val startOdometer: Double,
    val suggestedEndOdometer: Double,
    val totalWorkMinutes: Double,
    val drivingMinutes: Double,
    val avgServiceMinutes: Double,
    val completedVisitsCount: Int,
    val minutesSource: String,
    val foodMealExpenses: Double,
    val coffeeExpenses: Double,
    val drinksExpenses: Double,
    val parkingExpenses: Double,
    val tollExpenses: Double,
    val otherExpenses: Double,
    val lastFuelPricePerLiter: Double,
    val fuelConsumptionLitersPer100Km: Double,
    val fuelPriceWarnRatio: Double,
    /** Что делать, если GPS и одометр разошлись. Сравнение делает мастер. */
    val mileagePolicy: String = "gps",
    val mileageSmallGap: Double = 0.10,
    val mileageBigGap: Double = 0.20,
    val mileageMinKm: Double = 5.0,
)

data class GpsDayEstimate(
    val totalWorkMinutes: Double,
    val routeMinutes: Double,
    val serviceMinutes: Double,
    val avgServiceMinutes: Double,
    val detectedVisitsCount: Int,
    val gpsStartedAt: String?,
    val gpsFinishedAt: String?,
)

data class GpsVisitHint(
    val visitId: Int,
    val address: String,
    val clinic: String,
    val dwellMinutes: Double,
    val requiredDwellMinutes: Double,
    val readyToComplete: Boolean,
    val distanceMeters: Double,
    val accuracyMeters: Double,
    val firstSeenAt: String?,
    val lastSeenAt: String?,
    val fatigueLabel: String?,
)

data class ReportSnapshot(
    val title: String,
    val period: String,
    val startDate: String,
    val endDate: String,
    val summary: ReportSummary,
    val clinics: List<ClinicReportRow>,
    val fromCache: Boolean = false,
)

data class ReportSummary(
    val daysCount: Int,
    val visitsCount: Int,
    val grossIncome: Double,
    val totalExpenses: Double,
    val netProfit: Double,
    val netHourlyIncome: Double,
    val totalWorkMinutes: Double,
    val totalRouteMinutes: Double,
    val actualKm: Double,
    val visitIncome: Double,
    val telemedIncome: Double,
    val officeIncome: Double,
    val officeMinutes: Double,
    val fuelExpenses: Double,
    val amortizationExpenses: Double,
    val parkingExpenses: Double,
    val foodExpenses: Double,
    val foodMealExpenses: Double,
    val coffeeExpenses: Double,
    val drinksExpenses: Double,
    val tollExpenses: Double,
    val otherExpenses: Double,
    val workloadIndex: Double,
    val fatigueWeeklyAverage: Double,
    val overworkIndex: Double,
)

data class ClinicReportRow(
    val clinic: String,
    val visitsCount: Int,
    val visitIncome: Double,
    val telemedIncome: Double,
    val telemedMinutes: Double,
    val officeIncome: Double,
    val officeMinutes: Double,
    val workMinutes: Double,
    val grossIncome: Double,
    val netIncome: Double,
    val netHourlyIncome: Double,
)

data class WorkloadSnapshot(
    val source: String,
    val workDayId: Int?,
    val date: String?,
    val summary: WorkloadSummary?,
    val latestFeedback: WorkloadFeedback?,
    val survey: SurveyInfo,
    val fromCache: Boolean = false,
)

data class WorkloadSummary(
    val score: Double,
    val weeklyAverage: Double,
    val overworkIndex: Double,
    val level: String,
    val longStopCount: Int,
    val pauseMinutes: Double,
    val heavyVisitCount: Int,
    val nightWorkMinutes: Double,
    val workloadSurveyScore: Double,
    val breakHoursBefore: Double,
)

data class WorkloadFeedback(
    val predictedScore: Double,
    val userScore: Double,
    val feedbackType: String,
    val error: Double,
    val createdAt: String?,
)

data class WorkloadFeedbackResult(
    val predictedScore: Double,
    val userScore: Double,
    val error: Double,
    val activeWeightsCount: Int,
)

data class SurveyInfo(
    val questions: List<String>,
    val latestScore: Double,
    val latestDate: String?,
    val level: String,
)

data class WorkloadCorrelationReport(
    val days: Int,
    val rowsUsed: Int,
    val cells: List<WorkloadCorrelationCell>,
    val fromCache: Boolean = false,
)

data class WorkloadCorrelationCell(
    val feature: String,
    val target: String,
    val pearson: Double?,
    val spearman: Double?,
    val n: Int,
)

data class WorkloadTrendPoint(
    val date: String,
    val score: Double,
    val weeklyAverage: Double,
    val overworkIndex: Double,
)

data class WorkloadTrendReport(
    val days: Int,
    val points: List<WorkloadTrendPoint>,
    val fromCache: Boolean = false,
)

data class SyncQueueStats(
    val pendingCount: Int = 0,
    val sentCount: Int = 0,
    val failedCount: Int = 0,
) {
    val totalCount: Int
        get() = pendingCount + sentCount + failedCount
}

data class SyncConflict(
    val id: Int,
    val clientEventId: String?,
    val eventType: String,
    val entityType: String,
    val clientEntityId: String,
    val serverEntityId: Int?,
    val conflictType: String,
    val details: String?,
    val createdAt: String,
)

data class OfficeEntryDraft(
    val address: String = "",
    val minutes: Double = 0.0,
    val income: Double = 0.0,
    val clinic: String? = null,
)

data class TelemedEntryDraft(
    val income: Double = 0.0,
    val minutes: Double = 3.0,
    val clinic: String? = null,
)

data class ExpenseDraft(
    val category: ExpenseCategory = ExpenseCategory.Other,
    val amount: Double = 0.0,
    val comment: String = "",
)

enum class SettingType(val wire: String) {
    Number("number"),
    Text("text"),
    Bool("bool"),
    ListValue("list"),
    /** Зоны обслуживания: область → город → районы (JSON). */
    Zones("zones"),
    /** Выбор из вариантов: тип транспорта, режим расчёта километра, кто платит. */
    Choice("choice"),
    Unknown("");

    companion object {
        fun fromWire(value: String): SettingType = entries.firstOrNull { it.wire == value } ?: Unknown
    }
}

data class SettingField(
    val key: String,
    val label: String,
    val type: SettingType,
    val textValue: String = "",
    val boolValue: Boolean = false,
    val listValue: List<String> = emptyList(),
    /** Варианты для типа Choice: значение и то, что видит человек. */
    val options: List<SettingOption> = emptyList(),
    /** Одно предложение: что это за параметр и зачем он нужен. */
    val hint: String = "",
)

data class SettingOption(
    val value: String,
    val title: String,
)

/**
 * Сколько стоит километр — и что из этого посчитано по таблице, а что измерено по
 * вашим заправкам и расходам на машину.
 *
 * Считать один бензин — значит обманывать себя: машина ещё изнашивается, требует шин,
 * масла и ремонта. Коэффициент нужен ровно для этого — оценить реальную рентабельность
 * заказа. Это приблизительная модель, и она уступает факту, как только факт появится.
 */
data class VehicleCost(
    val total: Double,
    val fuelPerKm: Double,
    val maintenancePerKm: Double,
    /** «Платон», платные дороги, мойка, лизинг — то, чего модель знать не может. */
    val extraPerKm: Double,
    val mode: String,
    val wearCoefficient: Double,
    val riskMarkupPercent: Int,
    val fuelMeasured: Boolean,
    val maintenanceMeasured: Boolean,
    val explanation: String,
    val measuredConsumption: Double?,
    val measuredCoefficient: Double?,
    val measuredKm: Double,
)

/**
 * Как человеку платят. От этого зависит сам смысл вопроса «стоит ли ехать»: у окладника
 * лишний заказ не приносит денег — он только тратит его топливо и его время.
 */
data class IncomeModel(
    val kind: String,
    val title: String,
    val isSalary: Boolean,
    val paysPerOrder: Boolean,
    val monthlySalary: Int,
    val monthlyBonus: Int,
    val monthHours: Int,
    val hourlyRate: Double,
    val needsConfirmation: Boolean,
    val confirmText: String,
)

data class SettingsSection(
    val key: String,
    val title: String,
    val fields: List<SettingField>,
)

data class AppSettingsSnapshot(
    val sections: List<SettingsSection>,
)
