package com.homevisit.location

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

/**
 * Крупное окно очереди «Далее»: убрать отменившийся заказ и открыть подробности.
 *
 * Зачем отдельное окно. В самой Ленте строка заказа мала, а рядом живёт «Поехали» —
 * промахнуться и уехать не туда слишком легко. Отмена — необратимое действие, поэтому
 * ей нужно место и подтверждение, а не тесная строка списка.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UpNextManagerSheet(
    orders: List<RouteVisitUi>,
    onCancelVisit: (String) -> Unit,
    onOpenOrder: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    // Кого именно удаляем: подтверждение спрашиваем адресно, а не «вы уверены?» вообще.
    var confirming by remember { mutableStateOf<RouteVisitUi?>(null) }

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Следующие заказы", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(
                "Клиент отменился — уберите заказ, и день пересчитается без него.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            if (orders.isEmpty()) {
                Text(
                    "Очередь пуста.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                return@Column
            }

            orders.forEach { visit ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
                ) {
                    Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(Modifier.fillMaxWidth().clickable { onOpenOrder(visit.localId) }) {
                            Column(Modifier.weight(1f)) {
                                Text(
                                    visit.address,
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.SemiBold,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                Text(
                                    "${visit.clinic.ifBlank { "Без ${OrderSource.current.genSingle}" }} · ${money(visit.income)}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Text(
                                "подробнее",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }

                        if (confirming?.localId == visit.localId) {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedButton(
                                    modifier = Modifier.weight(1f),
                                    onClick = {
                                        onCancelVisit(visit.localId)
                                        confirming = null
                                    },
                                ) { Text("Точно убрать") }
                                TextButton(
                                    modifier = Modifier.weight(1f),
                                    onClick = { confirming = null },
                                ) { Text("Оставить") }
                            }
                        } else {
                            TextButton(onClick = { confirming = visit }) { Text("Убрать заказ") }
                        }
                    }
                }
            }
        }
    }
}
