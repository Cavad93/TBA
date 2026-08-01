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
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.homevisit.location.domain.AddressCandidate
import com.homevisit.location.domain.BasketPreview
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
    basket: BasketPreview? = null,
    basketLoading: Boolean = false,
    onCountBasket: (List<BatchOrder>) -> Unit = {},
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
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Прокручивается СПИСОК, а кнопки закреплены снизу. Пока список был
            // коротким, прокрутка всего экрана сходила с рук; с карточкой «Пачка
            // целиком» кнопка «Добавить» уехала за нижний край — главное действие
            // экрана перестало быть видно, и это поймали инструментальные тесты.
            // Действие обязано быть под рукой независимо от длины списка.
            Column(
                modifier = Modifier
                    .weight(1f, fill = false)
                    .verticalScroll(rememberScrollState()),
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
            // Вердикт на пачку ЦЕЛИКОМ. Раньше экран не показывал ни рубля: человек
            // добавлял вслепую, а заказы прогонялись по одному, и общий подъезд куста
            // доставался первому — он и объявлялся невыгодным (отчёты 878/881).
            if (prepared.isNotEmpty()) {
                BasketSummary(
                    basket = basket,
                    loading = basketLoading,
                    count = prepared.size,
                    onCount = { onCountBasket(prepared) },
                )
                }
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
            if (basket != null && basket.verdict == "skip") {
                // Не запрещаем — решает человек. Но и не молчим: раньше кнопка добавляла
                // пачку независимо от экономики, а зелёный на строках означал всего лишь
                // «адрес распознан», и это читалось как одобрение.
                Text(
                    "Пачка не окупает время, которое на неё уйдёт. Добавить можно, но это осознанный минус.",
                    style = MaterialTheme.typography.bodySmall,
                    color = VerdictColors.skip,
                )
            }
        }
    }
}

/**
 * Итог по пачке: доход, общий крюк, ставка и вердикт — одним блоком.
 *
 * Отдельной строкой назван ОБЩИЙ ПОДЪЕЗД: километры, которые платишь, пока едешь хоть за
 * одним заказом куста. Приписать их одному заказу нельзя, и именно из-за такой попытки
 * первый заказ дальней связки всегда выглядел убыточным.
 */
@Composable
private fun BasketSummary(
    basket: BasketPreview?,
    loading: Boolean,
    count: Int,
    onCount: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                "Пачка целиком",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            when {
                loading -> Text(
                    "Считаем один маршрут по всем $count адресам…",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                basket == null -> {
                    Text(
                        "Заказы связкой почти всегда выгоднее, чем поодиночке: дорога до куста " +
                            "одна на всех. Посчитайте пачку целиком, прежде чем решать.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    TextButton(onClick = onCount) { Text("Посчитать пачку") }
                }

                else -> {
                    val accent = when (basket.verdict) {
                        "go" -> VerdictColors.go
                        "skip" -> VerdictColors.skip
                        else -> VerdictColors.edge
                    }
                    Text(
                        basket.decision,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = accent,
                    )
                    Text(
                        basket.reason,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    BasketLine("Доход пачки", money(basket.income))
                    BasketLine(
                        "Общий крюк",
                        oneDecimal(basket.extraKm) + " км · " + minutesText(basket.extraMinutes),
                    )
                    BasketLine("Чистыми", money(basket.marginalProfit))
                    BasketLine("Ставка пачки", money(basket.marginalHourly) + "/час")
                    if (basket.sharedKm >= 1) {
                        BasketLine(
                            "Из них общий подъезд",
                            oneDecimal(basket.sharedKm) + " км на всю пачку",
                        )
                    }
                    if (basket.skipped.isNotEmpty()) {
                        Text(
                            "Не попали в расчёт: " + basket.skipped.joinToString(", "),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    TextButton(onClick = onCount) { Text("Пересчитать") }
                }
            }
        }
    }
}

/** Числа ведут макет: моноширинный, чтобы столбцы значений стояли ровно. */
@Composable
private fun BasketLine(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            value,
            style = MaterialTheme.typography.bodySmall,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Medium,
        )
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
    // Цвета качества адреса, а НЕ вердикта: здесь речь про «адрес понят», а не про
    // «стоит ехать». Раньше строка красилась зелёным из VerdictColors, и пачка выглядела
    // одобренной, хотя про деньги система в этот момент ничего не сказала (отчёт 878).
    val accent = when (effective) {
        BatchOrder.Status.GREEN -> AddressQualityColors.resolved
        BatchOrder.Status.YELLOW -> AddressQualityColors.ambiguous
        BatchOrder.Status.RED -> AddressQualityColors.unknown
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
