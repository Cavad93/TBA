package com.homevisit.location

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.homevisit.location.domain.BatchOrder

/**
 * Экран подтверждения пакета заказов (Ф15.2): список из вставки/шаринга/скриншота,
 * прогнанный слоёным геокодингом. Зелёные (resolved) — готовы; жёлтые (кандидаты) —
 * выбрать вариант; красные (не понято) — ручная правка. Молча ничего не добавляем:
 * одна кнопка «Добавить все зелёные», остальное — по одному тапу человека.
 */
@Composable
internal fun BatchOrdersScreen(
    orders: List<BatchOrder>,
    onAddGreen: (List<BatchOrder>) -> Unit,
    onClose: () -> Unit,
) {
    val green = orders.filter { it.status == BatchOrder.Status.GREEN }
    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Список заказов",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "Зелёные готовы, жёлтые уточните, красные не распознаны.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (orders.isEmpty()) {
                Text("Не удалось разобрать ни одной строки.", style = MaterialTheme.typography.bodyMedium)
            }
            orders.forEach { order -> BatchOrderRow(order) }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                Button(
                    modifier = Modifier.weight(1f),
                    enabled = green.isNotEmpty(),
                    onClick = { onAddGreen(green) },
                ) {
                    Text(if (green.isEmpty()) "Нет готовых" else "Добавить все зелёные (${green.size})")
                }
                TextButton(onClick = onClose) { Text("Закрыть") }
            }
        }
    }
}

@Composable
private fun BatchOrderRow(order: BatchOrder) {
    val accent = when (order.status) {
        BatchOrder.Status.GREEN -> VerdictColors.go
        BatchOrder.Status.YELLOW -> VerdictColors.edge
        BatchOrder.Status.RED -> VerdictColors.skip
    }
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = accent.copy(alpha = 0.08f)),
        border = BorderStroke(1.dp, accent),
    ) {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(order.address, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurface)
            val subtitle = when (order.status) {
                BatchOrder.Status.GREEN -> "Адрес распознан" + (order.income?.let { " · ${it.toInt()} ₽" } ?: "")
                BatchOrder.Status.YELLOW -> "Уточните: ${order.candidates.size} вариант(а)"
                BatchOrder.Status.RED -> "Не понято — впишите вручную"
            }
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = accent)
        }
    }
}
