package com.homevisit.location

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.text.KeyboardOptions
import com.homevisit.location.domain.AddressCandidate
import com.homevisit.location.domain.BatchOrder

/**
 * Экран подтверждения пакета заказов (Ф15.2): список из вставки/шаринга/скриншота,
 * прогнанный слоёным геокодингом.
 *
 * Экран РЕДАКТИРУЕМЫЙ (отчёт 818 из TG). Раньше он только показывал результат, и
 * добавить заказы можно было лишь «как распознались»: доход со скриншотов агрегаторов
 * не вытаскивается вовсе (там дата/время сверху, а не «адрес + цена»), поэтому заказы
 * уходили в работу с доходом 0 — и вердикт по ним был бессмысленным. А жёлтые с
 * вариантами добавить было нельзя совсем, хотя правильный адрес лежал в списке рядом.
 *
 * Теперь: доход вписывается у каждого пункта, а у жёлтых тап по варианту делает адрес
 * подтверждённым. Молча по-прежнему ничего не добавляем — только то, что человек
 * подтвердил кнопкой.
 */
@Composable
internal fun BatchOrdersScreen(
    orders: List<BatchOrder>,
    onAddGreen: (List<BatchOrder>) -> Unit,
    onClose: () -> Unit,
) {
    // Правки живут по индексу строки: сам список приходит из ViewModel и не меняется.
    val incomes = remember(orders) { mutableStateMapOf<Int, String>() }
    val picked = remember(orders) { mutableStateMapOf<Int, AddressCandidate>() }

    // Готов к добавлению — тот, у кого есть координаты: зелёный или жёлтый с выбранным
    // вариантом. Доход берём введённый, иначе распознанный, иначе ноль.
    val prepared = orders.mapIndexedNotNull { index, order ->
        val resolved = picked[index] ?: order.resolved ?: return@mapIndexedNotNull null
        order.copy(
            address = resolved.label.ifBlank { order.address },
            resolved = resolved,
            income = incomes[index]?.replace(',', '.')?.trim()?.toDoubleOrNull() ?: order.income,
            candidates = emptyList(),
        )
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                // targetSdk 35: Android 15 рисует под системными панелями — без
                // safeDrawing низ списка прячется под навигацию. imePadding — чтобы
                // клавиатура не закрывала поле дохода нижних строк.
                .safeDrawingPadding()
                .imePadding()
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
                "Впишите доход по каждому адресу. Жёлтые — выберите верный вариант, " +
                    "красные придётся внести вручную на «Оценке».",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (orders.isEmpty()) {
                Text("Не удалось разобрать ни одной строки.", style = MaterialTheme.typography.bodyMedium)
            }
            orders.forEachIndexed { index, order ->
                BatchOrderRow(
                    order = order,
                    chosen = picked[index],
                    income = incomes[index] ?: order.income?.let { formatIncome(it) } ?: "",
                    onIncome = { incomes[index] = it },
                    onPick = { picked[index] = it },
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                Button(
                    modifier = Modifier.weight(1f),
                    enabled = prepared.isNotEmpty(),
                    onClick = { onAddGreen(prepared) },
                ) {
                    Text(if (prepared.isEmpty()) "Нет готовых" else "Добавить (${prepared.size})")
                }
                TextButton(onClick = onClose) { Text("Закрыть") }
            }
        }
    }
}

private fun formatIncome(value: Double): String =
    if (value % 1.0 == 0.0) value.toInt().toString() else value.toString()

@Composable
private fun BatchOrderRow(
    order: BatchOrder,
    chosen: AddressCandidate?,
    income: String,
    onIncome: (String) -> Unit,
    onPick: (AddressCandidate) -> Unit,
) {
    // Выбранный вариант делает жёлтую строку зелёной прямо на экране — человек видит,
    // что уточнение принято, а не гадает.
    val effective = when {
        chosen != null || order.resolved != null -> BatchOrder.Status.GREEN
        order.candidates.isNotEmpty() -> BatchOrder.Status.YELLOW
        else -> BatchOrder.Status.RED
    }
    val accent = when (effective) {
        BatchOrder.Status.GREEN -> VerdictColors.go
        BatchOrder.Status.YELLOW -> VerdictColors.edge
        BatchOrder.Status.RED -> VerdictColors.skip
    }
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = accent.copy(alpha = 0.08f)),
        border = BorderStroke(1.dp, accent),
    ) {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                chosen?.label ?: order.address,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
            )
            val subtitle = when (effective) {
                BatchOrder.Status.GREEN -> if (chosen != null) "Вариант выбран" else "Адрес распознан"
                BatchOrder.Status.YELLOW -> "Уточните: ${order.candidates.size} вариант(а)"
                BatchOrder.Status.RED -> "Не понято — впишите вручную на «Оценке»"
            }
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = accent)

            // Варианты адреса — пока не выбран. После выбора список прячем: решение принято.
            if (effective == BatchOrder.Status.YELLOW) {
                order.candidates.forEach { candidate ->
                    OutlinedButton(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = { onPick(candidate) },
                    ) {
                        Text(candidate.streetHouse?.takeIf { it.isNotBlank() } ?: candidate.label)
                    }
                }
            }

            // Доход нужен и зелёным: со скриншотов агрегаторов цена не распознаётся,
            // а без неё вердикт «стоит ли ехать» считается от нуля и всегда «невыгодно».
            if (effective != BatchOrder.Status.RED) {
                OutlinedTextField(
                    value = income,
                    onValueChange = onIncome,
                    label = { Text("Доход, ₽") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth(),
                )
                // Пустой доход не запрещаем (можно дописать позже на «Оценке»), но и не
                // делаем вид, что всё в порядке: без него вердикт считается от нуля.
                if (income.isBlank()) {
                    Text(
                        "Без дохода вердикт посчитается от нуля — заказ будет выглядеть невыгодным",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}
