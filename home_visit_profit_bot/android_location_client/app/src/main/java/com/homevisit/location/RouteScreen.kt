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

@Composable
internal fun RouteScreen(uiState: HomeVisitUiState, workActions: WorkActions, settingsState: GpsSettingsState) {
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
        ChangeFinishCard(
            isLoading = uiState.serverRoute.isLoading,
            onUpdateFinish = workActions.onUpdateFinish,
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
internal fun ChangeFinishCard(isLoading: Boolean, onUpdateFinish: (String) -> Unit) {
    var finishAddress by rememberSaveable { mutableStateOf("") }
    InputCard("Изменить финиш") {
        Text(
            "Смените конечную точку среди дня — сервер геокодирует адрес и пересчитает маршрут.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = finishAddress,
            onValueChange = { finishAddress = it },
            singleLine = true,
            label = { Text("Новый адрес финиша") },
        )
        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading && finishAddress.isNotBlank(),
            onClick = {
                onUpdateFinish(finishAddress.trim())
                finishAddress = ""
            },
        ) {
            Text("Применить финиш")
        }
    }
}

@Composable
internal fun ActiveVisitCard(
    activeVisit: RouteVisitUi?,
    gpsHint: GpsHintUiState,
    onRefreshGpsHint: () -> Unit,
    onComplete: () -> Unit,
    onCancel: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
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
                    "Нет принятого адреса. После расчёта и принятия заказа он появится здесь.",
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

@Composable
internal fun ServerRouteCard(route: RouteUiState, onRefresh: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
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
                    "Пока нет серверного порядка адресов. Нажмите обновить после принятия заказа.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                if (snapshot.fromCache) OfflineBadge()
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
internal fun StopClassificationCard(activeVisit: RouteVisitUi?, isLoading: Boolean, onSelect: (StopLabel) -> Unit) {
    var selected by rememberSaveable { mutableStateOf(StopLabel.Normal) }
    InputCard("Тип GPS-остановки") {
        Text(
            "Уточнение влияет только на нагрузку и долг восстановления, экономический расчёт не меняет.",
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
internal fun RouteListCard(routeVisits: List<RouteVisitUi>) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
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

