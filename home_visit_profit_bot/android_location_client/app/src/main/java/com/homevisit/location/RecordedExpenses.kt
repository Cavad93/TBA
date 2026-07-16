package com.homevisit.location

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import com.homevisit.location.domain.EndDayPreview

/**
 * Уже записанные за смену расходы «Машина» и «Аренда» — справкой, без поля ввода.
 *
 * Человек видит полную картину при подтверждении итогов, но вписать сумму второй раз
 * не может: эти деньги уже учтены в дне, и поле ввода приглашало бы их задвоить.
 */
@Composable
internal fun RecordedExpenses(preview: EndDayPreview?) {
    val vehicle = preview?.vehicleExpenses ?: 0.0
    val rent = preview?.vehicleRent ?: 0.0
    if (vehicle <= 0 && rent <= 0) return

    Text(
        "Уже записано за смену",
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    if (vehicle > 0) {
        Text("Машина: ${money(vehicle)}", style = MaterialTheme.typography.bodyMedium)
    }
    if (rent > 0) {
        Text("Аренда машины: ${money(rent)}", style = MaterialTheme.typography.bodyMedium)
    }
}
