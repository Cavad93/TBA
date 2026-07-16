package com.homevisit.location

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.homevisit.location.domain.OrderDetails

/**
 * Подробная карточка заказа: открывается по клику и из архива, и из активных вызовов.
 *
 * Раньше подробностей по заказу не было нигде: в Ленте карточка показывает только
 * адрес и деньги, а «История» в настройках — одни агрегаты. Человеку негде было
 * посмотреть, что именно за заказ он взял и чем тот кончился.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrderDetailsSheet(details: OrderDetails?, onDismiss: () -> Unit) {
    if (details == null) return
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(details.address, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(
                details.statusText,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            DetailRow("Доход", money(details.income))
            if (details.clinic.isNotBlank()) {
                DetailRow(OrderSource.current.nomSingle, details.clinic)
            }
            DetailRow("Добавлен", details.addedAtText)
            if (details.closedAtText.isNotBlank()) {
                DetailRow("Закрыт", details.closedAtText)
            }
            details.driveMinutes?.let { DetailRow("В пути", minutesText(it)) }
            details.onSiteMinutes?.let { DetailRow("На адресе", minutesText(it)) }
            details.plannedStartAt?.let { DetailRow("Приём к", it) }
        }
    }
}

@Composable
private fun DetailRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}
