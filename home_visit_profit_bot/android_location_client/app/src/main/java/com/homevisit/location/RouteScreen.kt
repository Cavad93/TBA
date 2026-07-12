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
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
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
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.KeyboardArrowDown
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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
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
import androidx.compose.ui.unit.IntOffset
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
import kotlin.math.roundToInt
import kotlinx.coroutines.launch

@Composable
internal fun RouteScreen(uiState: HomeVisitUiState, workActions: WorkActions, settingsState: GpsSettingsState) {
    // Лента «Фокус»: Старт (редактируемый) → текущий заказ крупной карточкой →
    // «Далее» списком → порядок маршрута → Финиш (редактируемый) → слайдер завершения.
    var reordering by rememberSaveable { mutableStateOf(false) }
    var wizardOpen by rememberSaveable { mutableStateOf(false) }
    val templates = uiState.appSettings.addressTemplates()
    val orders = uiState.routeVisits

    ScreenColumn {
        RouteAnchor(
            title = "Старт",
            icon = Icons.Filled.PlayArrow,
            accent = VerdictColors.go,
            address = uiState.startAddress,
            templates = templates,
            isLoading = uiState.serverRoute.isLoading,
            onSave = workActions.onUpdateStart,
        )
        if (reordering) {
            ReorderCard(orders = orders, onReorder = workActions.onReorderRoute)
        } else {
            FocusOrderCard(
                active = uiState.activeVisit,
                gpsHint = uiState.gpsHint,
                onRefreshGpsHint = workActions.onRefreshGpsHint,
                onComplete = workActions.onCompleteCurrentVisit,
                onCancel = workActions.onCancelCurrentVisit,
            )
            UpNextList(orders = orders, activeLocalId = uiState.activeVisit?.localId)
        }
        if (orders.size > 1) {
            ReorderToggle(
                reordering = reordering,
                isLoading = uiState.serverRoute.isLoading,
                onToggle = { reordering = !reordering },
            )
        }
        RouteAnchor(
            title = "Финиш",
            icon = Icons.Filled.NearMe,
            accent = MaterialTheme.colorScheme.primary,
            address = uiState.finishAddress,
            templates = templates,
            isLoading = uiState.serverRoute.isLoading,
            onSave = workActions.onUpdateFinish,
        )
        // Единственная точка завершения смены — внизу Ленты (модель «двухэтажного дома»).
        // Слайдер не закрывает день сразу: сначала мастер уточняет итоги, и уже он
        // отправляет расчёт. Без него день закрывался бы без статистики.
        EndShiftSection(
            onEndShift = {
                wizardOpen = true
                workActions.onPrepareEndShift()
            },
        )
    }

    if (wizardOpen) {
        EndShiftWizard(
            endShift = uiState.endShift,
            onFinish = { details ->
                wizardOpen = false
                workActions.onEndDayWithDetails(details)
                workActions.onClearEndShift()
            },
            onDismiss = {
                wizardOpen = false
                workActions.onClearEndShift()
            },
        )
    }
}

/**
 * Кнопка порядка маршрута над Финишем. Маршрут и так оптимизируется автоматически
 * при каждом добавлении заказа (настройка auto_optimize), поэтому здесь — ручная
 * донастройка порядка кнопками ↑↓.
 */
@Composable
internal fun ReorderToggle(reordering: Boolean, isLoading: Boolean, onToggle: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        OutlinedButton(modifier = Modifier.fillMaxWidth(), enabled = !isLoading, onClick = onToggle) {
            Icon(
                imageVector = if (reordering) Icons.Filled.CheckCircle else Icons.AutoMirrored.Filled.TrendingUp,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(if (reordering) "Готово" else "Изменить порядок")
        }
        if (!reordering) {
            Text(
                "Маршрут оптимизирован автоматически",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** Ручная перестановка заказов: ↑↓ меняют порядок, он сразу сохраняется на сервере. */
@Composable
internal fun ReorderCard(orders: List<RouteVisitUi>, onReorder: (List<Int>) -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                "Порядок заказов",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
            )
            orders.forEachIndexed { index, visit ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(
                        Modifier.size(24.dp).clip(CircleShape).background(MaterialTheme.colorScheme.surfaceContainerHighest),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text("${index + 1}", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    }
                    Column(Modifier.weight(1f)) {
                        Text(visit.address, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            "${visit.clinic.ifBlank { "Без компании" }} · ${money(visit.income)}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    OutlinedIconButton(
                        enabled = index > 0,
                        onClick = { onReorder(movedOrderIds(orders, index, index - 1)) },
                    ) {
                        Icon(Icons.Filled.KeyboardArrowUp, contentDescription = "Выше")
                    }
                    OutlinedIconButton(
                        enabled = index < orders.lastIndex,
                        onClick = { onReorder(movedOrderIds(orders, index, index + 1)) },
                    ) {
                        Icon(Icons.Filled.KeyboardArrowDown, contentDescription = "Ниже")
                    }
                }
            }
        }
    }
}

/** Новый порядок id визитов после перемещения элемента from → to. */
internal fun movedOrderIds(orders: List<RouteVisitUi>, from: Int, to: Int): List<Int> {
    val list = orders.toMutableList()
    val item = list.removeAt(from)
    list.add(to, item)
    return list.mapNotNull { it.serverId }
}

/**
 * Якорь маршрута (Старт/Финиш): показывает адрес, по «Изменить» — правка и пересчёт.
 * В режиме правки можно выбрать сохранённый шаблон адреса из выпадающего списка
 * (последний пункт — ввод вручную) или просто напечатать новый адрес.
 */
@Composable
internal fun RouteAnchor(
    title: String,
    icon: ImageVector,
    accent: Color,
    address: String,
    templates: List<AddressTemplate>,
    isLoading: Boolean,
    onSave: (String) -> Unit,
) {
    var editing by rememberSaveable(title) { mutableStateOf(false) }
    var text by rememberSaveable(title) { mutableStateOf("") }
    var pickerOpen by remember { mutableStateOf(false) }
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Box(
                    Modifier.size(34.dp).clip(RoundedCornerShape(10.dp)).background(accent.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(18.dp))
                }
                Column(Modifier.weight(1f)) {
                    Text(title, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(address.ifBlank { "не задан" }, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                TextButton(onClick = {
                    if (!editing) text = address
                    editing = !editing
                }) {
                    Text(if (editing) "Отмена" else "Изменить")
                }
            }
            if (editing) {
                if (templates.isNotEmpty()) {
                    Box(Modifier.fillMaxWidth()) {
                        OutlinedButton(onClick = { pickerOpen = true }, modifier = Modifier.fillMaxWidth()) {
                            Text(
                                "Выбрать шаблон",
                                modifier = Modifier.weight(1f),
                                textAlign = TextAlign.Start,
                                maxLines = 1,
                            )
                            Icon(Icons.Filled.ArrowDropDown, contentDescription = null)
                        }
                        DropdownMenu(expanded = pickerOpen, onDismissRequest = { pickerOpen = false }) {
                            templates.forEach { template ->
                                DropdownMenuItem(
                                    text = { Text("${template.name} · ${template.address}", maxLines = 1, overflow = TextOverflow.Ellipsis) },
                                    onClick = {
                                        text = template.address
                                        pickerOpen = false
                                    },
                                )
                            }
                            DropdownMenuItem(
                                text = { Text("Ввести вручную…") },
                                onClick = {
                                    text = ""
                                    pickerOpen = false
                                },
                            )
                        }
                    }
                }
                OutlinedTextField(
                    modifier = Modifier.fillMaxWidth(),
                    value = text,
                    onValueChange = { text = it },
                    label = { Text("Новый адрес") },
                    singleLine = true,
                )
                Button(
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !isLoading && text.isNotBlank(),
                    onClick = {
                        onSave(text.trim())
                        editing = false
                    },
                ) {
                    Text("Сохранить · пересчитать маршрут")
                }
            }
        }
    }
}

/** Крупная карточка текущего заказа: «Готово»/«Отмена» и «Закрыть по GPS». */
@Composable
internal fun FocusOrderCard(
    active: RouteVisitUi?,
    gpsHint: GpsHintUiState,
    onRefreshGpsHint: () -> Unit,
    onComplete: () -> Unit,
    onCancel: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (active != null) VerdictColors.edgeContainer else MaterialTheme.colorScheme.surfaceContainerLow,
        ),
        border = if (active != null) BorderStroke(1.dp, VerdictColors.edge) else null,
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(
                "Текущий заказ",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = if (active != null) VerdictColors.onEdgeContainer else MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (active == null) {
                Text(
                    "Активного заказа нет. Оцените и примите заказ во вкладке «Оценка».",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                Text(active.address, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(
                    "${active.clinic.ifBlank { "Без компании" }} · ${money(active.income)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                AnchorTimeLabel(active)
                GpsHintBlock(gpsHint = gpsHint, onRefresh = onRefreshGpsHint, onComplete = onComplete)
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(
                        modifier = Modifier.weight(1f),
                        enabled = active.serverId != null,
                        onClick = onComplete,
                        colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go, contentColor = Color.White),
                    ) {
                        Text("Готово")
                    }
                    OutlinedButton(modifier = Modifier.weight(1f), enabled = active.serverId != null, onClick = onCancel) {
                        Text("Отмена")
                    }
                }
            }
        }
    }
}

/** Список остальных принятых заказов — «Далее». */
@Composable
internal fun UpNextList(orders: List<RouteVisitUi>, activeLocalId: String?) {
    val upcoming = orders.filter { it.localId != activeLocalId }
    if (upcoming.isEmpty()) return
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(
                "Далее · ${upcoming.size}",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            upcoming.forEachIndexed { index, v ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        Modifier.size(22.dp).clip(CircleShape).background(MaterialTheme.colorScheme.surfaceContainerHighest),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text("${index + 1}", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    }
                    Column(Modifier.weight(1f)) {
                        Text(v.address, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            "${v.clinic.ifBlank { "Без компании" }} · ${money(v.income)}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        AnchorTimeLabel(v)
                    }
                }
            }
        }
    }
}


/**
 * Время работы на точке. Показываем его явно: это заказ-якорь — оптимизатор его не
 * переставляет, потому что на приём с 9:00 нельзя приехать в другое время.
 */
@Composable
internal fun AnchorTimeLabel(visit: RouteVisitUi) {
    if (!visit.isAnchor) return
    val start = timeOfDayText(visit.plannedStartAt)
    val end = timeOfDayText(visit.plannedEndAt)
    val window = when {
        start != null && end != null -> "$start–$end"
        start != null -> "с $start"
        else -> null
    }
    Text(
        text = listOfNotNull("На точке", window).joinToString(" · "),
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.SemiBold,
        color = VerdictColors.edge,
    )
}

/**
 * Завершение смены — только здесь, внизу Ленты. Чтобы случайное касание не
 * закрывало смену, это слайдер: ручку нужно осознанно протолкнуть слева направо.
 * Отпустил, не доведя до конца — ручка пружиной возвращается в начало. Дошёл до
 * конца — смена закрывается, статус перестаёт быть Active, и «лифт» поднимает
 * пользователя обратно на Штурвал (см. HomeVisitApp).
 */
@Composable
internal fun EndShiftSection(onEndShift: () -> Unit) {
    val density = LocalDensity.current
    val scope = rememberCoroutineScope()

    val trackHeight = 56.dp
    val thumbSize = 48.dp
    val edge = 4.dp
    val thumbPx = with(density) { thumbSize.toPx() }
    val edgePx = with(density) { edge.toPx() }

    val offsetX = remember { Animatable(0f) }
    var maxOffset by remember { mutableStateOf(0f) }
    var done by remember { mutableStateOf(false) }
    val progress = if (maxOffset > 0f) (offsetX.value / maxOffset).coerceIn(0f, 1f) else 0f

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(trackHeight)
            .clip(RoundedCornerShape(trackHeight / 2))
            .background(VerdictColors.skipContainer)
            .onSizeChanged {
                // Ход ручки = ширина трека − ширина ручки − отступы по краям.
                maxOffset = (it.width - thumbPx - edgePx * 2).coerceAtLeast(0f)
            },
        contentAlignment = Alignment.CenterStart,
    ) {
        Text(
            text = "Проведите вправо, чтобы завершить смену",
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = thumbSize + edge, end = 12.dp)
                .alpha(1f - progress),
            textAlign = TextAlign.Center,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            fontWeight = FontWeight.SemiBold,
            style = MaterialTheme.typography.titleSmall,
            color = VerdictColors.onSkipContainer,
        )
        Box(
            modifier = Modifier
                .padding(edge)
                .offset { IntOffset(offsetX.value.roundToInt(), 0) }
                .size(thumbSize)
                .clip(CircleShape)
                .background(VerdictColors.skip)
                .draggable(
                    orientation = Orientation.Horizontal,
                    enabled = !done,
                    state = rememberDraggableState { delta ->
                        scope.launch {
                            offsetX.snapTo((offsetX.value + delta).coerceIn(0f, maxOffset))
                        }
                    },
                    onDragStopped = {
                        scope.launch {
                            if (maxOffset > 0f && offsetX.value >= maxOffset * 0.9f) {
                                // Доведено до конца — фиксируем и завершаем смену.
                                offsetX.animateTo(maxOffset, tween(durationMillis = 120))
                                done = true
                                onEndShift()
                            } else {
                                // Отпущено раньше — пружиной обратно в начало.
                                offsetX.animateTo(
                                    0f,
                                    spring(
                                        dampingRatio = Spring.DampingRatioMediumBouncy,
                                        stiffness = Spring.StiffnessMediumLow,
                                    ),
                                )
                            }
                        }
                    },
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = "Завершить смену",
                tint = Color.White,
            )
        }
    }
}

@Composable
internal fun GpsHintBlock(gpsHint: GpsHintUiState, onRefresh: () -> Unit, onComplete: () -> Unit) {
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


