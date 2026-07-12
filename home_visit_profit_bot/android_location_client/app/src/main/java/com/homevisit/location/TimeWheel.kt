package com.homevisit.location

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.snapping.rememberSnapFlingBehavior
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val ITEM_HEIGHT = 44.dp
private const val VISIBLE_ITEMS = 3

/**
 * Барабан выбора времени: часы и минуты крутятся отдельно, выбранное значение
 * встаёт в рамку по центру — как будильник в телефоне.
 *
 * Ввод времени с клавиатуры для работы на точке неудобен: это не произвольный текст,
 * а одно из 288 значений с шагом 5 минут, и промахнуться в цифре легко.
 */
@Composable
internal fun TimeWheel(
    minutesOfDay: Int,
    onChange: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val hour = (minutesOfDay / 60).coerceIn(0, 23)
    val minute = (minutesOfDay % 60).coerceIn(0, 59)

    Box(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            WheelColumn(
                values = (0..23).toList(),
                selected = hour,
                onSelect = { onChange(it * 60 + minute) },
                modifier = Modifier.weight(1f),
            )
            WheelColumn(
                values = (0..55 step 5).toList(),
                // Ближайшее кратное пяти: значение могло прийти из старой записи.
                selected = (minute / 5) * 5,
                onSelect = { onChange(hour * 60 + it) },
                modifier = Modifier.weight(1f),
            )
        }
        // Рамка выбранного значения — по центру барабана.
        Box(
            modifier = Modifier
                .align(Alignment.Center)
                .fillMaxWidth()
                .height(ITEM_HEIGHT)
                .clip(RoundedCornerShape(10.dp))
                .background(VerdictColors.goContainer.copy(alpha = 0.45f)),
        )
    }
}

@Composable
private fun WheelColumn(
    values: List<Int>,
    selected: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val startIndex = values.indexOf(selected).coerceAtLeast(0)
    val listState = rememberLazyListState(initialFirstVisibleItemIndex = startIndex)
    val flingBehavior = rememberSnapFlingBehavior(lazyListState = listState)

    // Значение под рамкой — то, что «первое видимое»: сверху и снизу добавлены
    // пустые ячейки, поэтому центр списка совпадает с первым видимым элементом.
    val centered by remember {
        derivedStateOf { values.getOrNull(listState.firstVisibleItemIndex) ?: selected }
    }
    LaunchedEffect(listState) {
        snapshotFlow { listState.isScrollInProgress to listState.firstVisibleItemIndex }
            .collect { (scrolling, _) ->
                if (!scrolling && centered != selected) {
                    onSelect(centered)
                }
            }
    }
    // Значение поменяли снаружи (например, кнопкой) — подкручиваем барабан.
    LaunchedEffect(selected) {
        val target = values.indexOf(selected)
        if (target >= 0 && target != listState.firstVisibleItemIndex && !listState.isScrollInProgress) {
            listState.scrollToItem(target)
        }
    }

    LazyColumn(
        modifier = modifier.height(ITEM_HEIGHT * VISIBLE_ITEMS),
        state = listState,
        flingBehavior = flingBehavior,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        item { Spacer() }
        items(values) { value ->
            val isSelected = value == selected
            Text(
                text = value.toString().padStart(2, '0'),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(ITEM_HEIGHT)
                    .clip(RoundedCornerShape(8.dp))
                    .clickable { onSelect(value) }
                    .padding(top = 9.dp),
                textAlign = TextAlign.Center,
                fontSize = if (isSelected) 22.sp else 18.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                color = if (isSelected) VerdictColors.go else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item { Spacer() }
    }
}

/** Пустая ячейка сверху и снизу: без неё крайние значения не встают под рамку. */
@Composable
private fun Spacer() {
    Box(Modifier.height(ITEM_HEIGHT))
}

/** Барабан с подписью и текущим значением — то, что вставляется в форму. */
@Composable
internal fun LabeledTimeWheel(
    label: String,
    minutesOfDay: Int,
    onChange: (Int) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.weight(1f),
            )
            Text(
                minutesText24(minutesOfDay),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = VerdictColors.go,
            )
        }
        TimeWheel(minutesOfDay = minutesOfDay, onChange = onChange)
    }
}

/** 540 → «09:00». */
internal fun minutesText24(minutesOfDay: Int): String {
    val h = (minutesOfDay / 60).coerceIn(0, 23)
    val m = (minutesOfDay % 60).coerceIn(0, 59)
    return "${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}"
}
