package com.homevisit.location

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
    InputCard("Личная поездка") {
        Text(
            "≈ ${money(check.minimumCheck)} туда и обратно",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
        )
        Text(
            "${fmtKm(check.roundTripKm)} · ${check.roundTripMinutes.toInt()} мин в пути",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            TripCostRow("Дорога (топливо, износ)", check.carCost)
            TripCostRow("Время в пути", check.timeCost)
            if (check.parkingCost > 0) TripCostRow("Парковка", check.parkingCost)
        }
        if (check.hourlyOnSite > 0) {
            Text(
                "+ ${money(check.hourlyOnSite)} за каждый час на месте",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (check.fallback) {
            Text(
                "Адрес вне покрытия карт — оценка по прямой, грубо.",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.error,
            )
        }
    }
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
