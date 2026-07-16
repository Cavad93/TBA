package com.homevisit.location

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AssistChip
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.homevisit.location.ui.PersonalTripUi

/**
 * Результат «личной поездки» (Ф11.5). Ни дохода, ни вердикта «стоит ли ехать» — человек
 * не зарабатывает, а хочет знать, во сколько ему обойдётся съездить туда и обратно.
 * Крупно — итог, ниже — разложение (дорога, время в пути, парковка) и +час на месте.
 */
@Composable
internal fun PersonalTripCard(state: PersonalTripUi) {
    when {
        state.isLoading -> InputCard("Личная поездка") {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                CircularProgressIndicator()
                Text("Считаю поездку…", style = MaterialTheme.typography.bodyMedium)
            }
        }
        state.message.isNotBlank() -> InputCard("Личная поездка") {
            Text(
                state.message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        state.result != null -> PersonalTripResult(state.result)
    }
}

@Composable
private fun PersonalTripResult(check: com.homevisit.location.domain.MinimumCheck) {
    // «Только туда» — тот же движок, без второй формулы: дорога и время ровно вдвое
    // меньше (round_trip = 2× one-way), парковка — разовый расход за визит, не делится.
    var oneWay by rememberSaveable { mutableStateOf(false) }
    val factor = if (oneWay) 0.5 else 1.0
    val carCost = check.carCost * factor
    val timeCost = check.timeCost * factor
    val km = check.roundTripKm * factor
    val minutes = check.roundTripMinutes * factor
    val total = carCost + timeCost + check.parkingCost

    InputCard("Личная поездка") {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = !oneWay,
                onClick = { oneWay = false },
                label = { Text("Туда-обратно") },
            )
            FilterChip(
                selected = oneWay,
                onClick = { oneWay = true },
                label = { Text("Только туда") },
            )
        }
        Text(
            if (oneWay) "≈ ${money(total)} в одну сторону" else "≈ ${money(total)} туда и обратно",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
        )
        Text(
            "${fmtKm(km)} · ${minutes.toInt()} мин в пути",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            TripCostRow("Дорога (топливо, износ)", carCost)
            TripCostRow("Время в пути", timeCost)
            if (check.parkingCost > 0) TripCostRow("Парковка", check.parkingCost)
        }
        if (check.hourlyOnSite > 0) {
            Text(
                "+ ${money(check.hourlyOnSite)} за каждый час на месте",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        TicketsChip(check.tickets, oneWay)
        if (check.fallback) {
            Text(
                "Адрес вне покрытия карт — оценка по прямой, грубо.",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.error,
            )
        }
    }
}

/**
 * Маленькая кнопка «дешевле долететь» (Ф11.6). Появляется только при реальной выгоде.
 *
 * Никаких решений здесь нет: сервер присылает блок ТОЛЬКО когда билет дешевле машины
 * минимум на порог (дефолт 10%) на межгороде в личном режиме. Нет блока — нет кнопки.
 * Цифры берём готовой фразой сервера, а не пересобираем: иначе однажды разойдёмся с тем,
 * по чему он принимал решение.
 *
 * `oneWay` гасит кнопку, и это не мелочь. Сервер сравнивал КРУГОВУЮ машину с КРУГОВЫМ
 * билетом (`price` у Travelpayouts — перелёт туда И обратно). В режиме «только туда»
 * цена машины делится пополам, а билет — нет: рядом с половинной суммой «самолёт дешевле»
 * стало бы прямой неправдой. Молчим, а не показываем сомнительное.
 */
@Composable
private fun TicketsChip(tickets: com.homevisit.location.domain.TicketsOffer?, oneWay: Boolean) {
    if (tickets == null || oneWay) return
    val context = LocalContext.current
    AssistChip(
        onClick = {
            runCatching {
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(tickets.url)))
            }
        },
        label = { Text("✈ ${tickets.text}") },
    )
}

@Composable
private fun TripCostRow(label: String, value: Double) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium)
        Text(money(value), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
    }
}

private fun fmtKm(km: Double): String =
    if (km >= 10) "${km.toInt()} км" else "%.1f км".format(km)
