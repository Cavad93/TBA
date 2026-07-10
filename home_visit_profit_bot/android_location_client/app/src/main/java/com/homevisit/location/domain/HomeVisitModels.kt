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
    val recovery: HomeRecovery?,
    val monthMoney: HomeMoney,
    val yesterdayMoney: HomeMoney,
    val hourlyVsMonth: Double,
    val debtVsPrev: Double?,
    val greenStreak: Int,
    val recommendations: List<HomeRecommendation>,
    val fromCache: Boolean = false,
)

/** Данные для запуска смены: предзаполнение одометра и авто-перерыв. */
data class HomeStartPrompt(
    val hasLastOdometer: Boolean,
    val lastOdometer: Double,
    val prevEndedAt: String?,
    val breakHours: Double,
)

/** Состояние восстановления. `verdict` — go/edge/skip для окраски. */
data class HomeRecovery(
    val recoveryDebt: Double,
    val burnoutScore: Double,
    val fatigueScore: Double,
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

data class WorkDaySummary(
    val status: WorkDayStatus = WorkDayStatus.NotStarted,
    val visitsCount: Int = 0,
    val officeCount: Int = 0,
    val telemedCount: Int = 0,
    val grossIncome: Double = 0.0,
    val netHourlyIncome: Double = 0.0,
    val fatigueScore: Double = 0.0,
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
    val requiredExtraPayment: Double,
    val requiredCandidateIncome: Double,
    val beforeHourly: Double,
    val afterHourly: Double,
    val marginalHourly: Double,
    val extraKm: Double,
    val extraDriveMinutes: Double,
    val fatigueExtraPayment: Double,
    val fatigueLevel: String,
)

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
    val fromCache: Boolean = false,
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
    val userFatigueScore: Double?,
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
    val fatigueScore: Double,
    val fatigueWeeklyAverage: Double,
    val recoveryDebt: Double,
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

data class FatigueSnapshot(
    val source: String,
    val workDayId: Int?,
    val date: String?,
    val summary: FatigueSummary?,
    val latestFeedback: FatigueFeedback?,
    val cbi: CbiInfo,
    val fromCache: Boolean = false,
)

data class FatigueSummary(
    val score: Double,
    val weeklyAverage: Double,
    val recoveryDebt: Double,
    val level: String,
    val longStopCount: Int,
    val pauseMinutes: Double,
    val heavyVisitCount: Int,
    val circadianRiskMinutes: Double,
    val burnoutScore: Double,
    val sleepHours: Double,
    val sleepQuality: Double,
    val breakHoursBefore: Double,
)

data class FatigueFeedback(
    val predictedScore: Double,
    val userScore: Double,
    val feedbackType: String,
    val error: Double,
    val createdAt: String?,
)

data class FatigueFeedbackResult(
    val predictedScore: Double,
    val userScore: Double,
    val error: Double,
    val activeWeightsCount: Int,
)

data class CbiInfo(
    val questions: List<String>,
    val latestScore: Double,
    val latestDate: String?,
    val level: String,
)

data class FatigueCorrelationReport(
    val days: Int,
    val rowsUsed: Int,
    val cells: List<FatigueCorrelationCell>,
    val fromCache: Boolean = false,
)

data class FatigueCorrelationCell(
    val feature: String,
    val target: String,
    val pearson: Double?,
    val spearman: Double?,
    val n: Int,
)

data class FatigueTrendPoint(
    val date: String,
    val score: Double,
    val weeklyAverage: Double,
    val recoveryDebt: Double,
)

data class FatigueTrendReport(
    val days: Int,
    val points: List<FatigueTrendPoint>,
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
)

data class SettingsSection(
    val key: String,
    val title: String,
    val fields: List<SettingField>,
)

data class AppSettingsSnapshot(
    val sections: List<SettingsSection>,
)
