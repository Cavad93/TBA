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

internal fun shortMoney(value: Double): String {
    return if (value >= 1000) String.format(Locale("ru", "RU"), "%.0fк", value / 1000) else value.toInt().toString()
}

// ======================= Экран «Профиль» (состояние) =======================

internal fun initials(name: String): String {
    val parts = name.trim().split(" ", ".").filter { it.isNotBlank() }
    return when {
        parts.isEmpty() -> "?"
        parts.size == 1 -> parts[0].take(1).uppercase()
        else -> (parts[0].take(1) + parts[1].take(1)).uppercase()
    }
}

internal fun drivingWord(score: Double): String = when {
    score >= 8 -> "Ровный"
    score >= 6 -> "Аккуратный"
    score >= 4 -> "Средний"
    else -> "Резкий"
}

internal fun headerDate(iso: String): String {
    return try {
        val d = java.time.LocalDate.parse(iso)
        val days = arrayOf("ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ")
        val months = arrayOf("ЯНВАРЯ", "ФЕВРАЛЯ", "МАРТА", "АПРЕЛЯ", "МАЯ", "ИЮНЯ", "ИЮЛЯ", "АВГУСТА", "СЕНТЯБРЯ", "ОКТЯБРЯ", "НОЯБРЯ", "ДЕКАБРЯ")
        "${days[d.dayOfWeek.value - 1]}, ${d.dayOfMonth} ${months[d.monthValue - 1]}"
    } catch (_: Exception) {
        iso
    }
}

internal fun hoursWord(n: Int): String {
    val nn = n % 100
    val d = n % 10
    return when {
        nn in 11..14 -> "часов"
        d == 1 -> "час"
        d in 2..4 -> "часа"
        else -> "часов"
    }
}

internal fun trendLabel(delta: Double): String? {
    if (delta == 0.0) return null
    return (if (delta > 0) "↑ " else "↓ ") + money(kotlin.math.abs(delta)) + "/ч к среднему"
}

internal fun trendColor(delta: Double): Color = if (delta >= 0) VerdictColors.go else VerdictColors.skip

internal fun dayWord(count: Int): String {
    val n = kotlin.math.abs(count) % 100
    val d = n % 10
    return when {
        n in 11..14 -> "дней"
        d == 1 -> "день"
        d in 2..4 -> "дня"
        else -> "дней"
    }
}

internal fun qualityWord(value: Int): String = when (value) {
    0 -> "не спал"
    1 -> "плохо"
    2 -> "так себе"
    3 -> "нормально"
    4 -> "хорошо"
    else -> "отлично"
}

/** Настройки, которые допустимо очистить (сервер принимает пустое значение). */
private val CLEARABLE_TEXT_SETTINGS =
    setOf("default_start_address", "default_finish_address", "osago_expires_at")

// Человек пишет дату как привык: «16.07.2027». Сервер хранит ISO. Приводим сами,
// а нераспознанное отправляем как есть — сервер вернёт отказ с причиной, и она
// будет показана человеку (молча выбрасывать ввод нельзя, это «тихо соврало»).
private val HUMAN_DATE = Regex("""^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$""")
private val ISO_DATE = Regex("""^(\d{4})-(\d{1,2})-(\d{1,2})$""")

internal fun normalizeDateInput(raw: String): String? {
    val text = raw.trim()
    ISO_DATE.matchEntire(text)?.let { match ->
        val (year, month, day) = match.destructured
        return isoDateOrNull(year.toInt(), month.toInt(), day.toInt())
    }
    HUMAN_DATE.matchEntire(text)?.let { match ->
        val (day, month, year) = match.destructured
        return isoDateOrNull(year.toInt(), month.toInt(), day.toInt())
    }
    return null
}

private fun isoDateOrNull(year: Int, month: Int, day: Int): String? {
    if (month !in 1..12 || day !in 1..31) return null
    return "%04d-%02d-%02d".format(year, month, day)
}

internal fun collectSettingsChanges(
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
                    if (edited != field.textValue) {
                        // Нераспознанное (и очищенное) уходит как есть: сервер отвергнет
                        // поключево с причиной, и человек её увидит («Сохранено, кроме…»).
                        // Молча выбрасывать правку нельзя — поле откатывалось без слов.
                        changes[field.key] = number ?: edited
                    }
                }
                SettingType.ListValue -> {
                    val editedRaw = textEdits[field.key] ?: field.listValue.joinToString(", ")
                    val editedList = editedRaw.split(',').map { it.trim() }.filter { it.isNotEmpty() }
                    if (editedList != field.listValue) changes[field.key] = editedList
                }
                SettingType.Date -> {
                    val edited = (textEdits[field.key] ?: field.textValue).trim()
                    if (edited != field.textValue) {
                        if (edited.isEmpty()) {
                            // Дата необязательная: стёр — значит, хочет убрать напоминание.
                            if (field.key in CLEARABLE_TEXT_SETTINGS) changes[field.key] = ""
                        } else {
                            changes[field.key] = normalizeDateInput(edited) ?: edited
                        }
                    }
                }
                else -> {
                    val edited = (textEdits[field.key] ?: field.textValue).trim()
                    // Пустое значение обычно означает «поле не трогали» и не отправляется.
                    // Исключение — старт и финиш: их можно осознанно очистить, пока
                    // пользователь не выбрал шаблон. Остальные текстовые поля сервер
                    // пустыми не принимает, и отправка пустоты уронила бы синхронизацию.
                    val clearable = field.key in CLEARABLE_TEXT_SETTINGS
                    if (edited != field.textValue && (edited.isNotEmpty() || clearable)) {
                        changes[field.key] = edited
                    }
                }
            }
        }
    }
    return changes
}

internal fun WorkDayStatus.title(): String = when (this) {
    WorkDayStatus.NotStarted -> "Не начат"
    WorkDayStatus.Active -> "Активен"
    WorkDayStatus.Closed -> "Завершен"
}

internal fun WorkForm.title(): String = when (this) {
    WorkForm.Visit -> "Адрес"
    WorkForm.Office -> "На точке"
    WorkForm.Telemed -> "Удалённо"
    WorkForm.Expense -> "Расход"
}

internal fun money(value: Double): String {
    return String.format(Locale("ru", "RU"), "%,.0f ₽", value)
}

/** Целое с разрядами по-русски: 84120 → «84 120». */
internal fun groupedInt(value: Double): String {
    return String.format(Locale("ru", "RU"), "%,d", value.toLong())
}

internal fun oneDecimal(value: Double): String {
    return String.format(Locale("ru", "RU"), "%.1f", value)
}

internal fun minutesText(minutes: Double): String {
    val total = minutes.toInt()
    val hours = total / 60
    val rest = total % 60
    return if (hours > 0) "${hours} ч ${rest} мин" else "${rest} мин"
}

internal fun hoursInput(minutes: Double): String {
    return oneDecimal(minutes / 60.0)
}

internal fun parseNumber(value: String): Double? {
    return value
        .replace(" ", "")
        .replace(',', '.')
        .toDoubleOrNull()
        ?.takeIf { it >= 0.0 }
}

internal fun parseSurveyAnswers(value: String, count: Int): List<Int> {
    if (count <= 0) {
        return emptyList()
    }
    val values = value.split(",").mapNotNull { it.toIntOrNull() }.toMutableList()
    while (values.size < count) {
        values.add(-1)
    }
    return values.take(count)
}

internal fun updateSurveyAnswer(raw: String, count: Int, index: Int, value: Int): String {
    val answers = parseSurveyAnswers(raw, count).toMutableList()
    if (index in answers.indices) {
        answers[index] = value
    }
    return answers.joinToString(",")
}

internal fun sortedCorrelationCells(cells: List<WorkloadCorrelationCell>): List<WorkloadCorrelationCell> {
    return cells
        .filter { it.n >= 3 && (it.pearson != null || it.spearman != null) }
        .sortedByDescending { kotlin.math.abs(it.pearson ?: it.spearman ?: 0.0) }
}

internal fun workloadFeatureTitle(value: String): String = when (value) {
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

internal fun workloadTargetTitle(value: String): String = when (value) {
    "workload_index" -> "нагрузка"
    "overwork_index" -> "долг"
    "user_workload_index" -> "оценка исполнителя"
    "workload_survey_score" -> "Самочувствие"
    else -> value
}

