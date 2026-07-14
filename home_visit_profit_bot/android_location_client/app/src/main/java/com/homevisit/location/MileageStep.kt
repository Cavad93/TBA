package com.homevisit.location

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kotlin.math.abs
import kotlin.math.roundToInt

/**
 * Какой пробег считать рабочим, когда GPS и одометр разошлись.
 *
 * У этой разницы ровно два объяснения, и они противоположны:
 *
 *  1. Личные поездки. GPS считает путь смены, одометр — весь путь машины. Заехали
 *     пообедать, отвезли ребёнка — одометр это увидел, а к работе это не относится.
 *
 *  2. Провал GPS. Тоннель, подземная парковка, разряженный телефон, потерянный сигнал
 *     во дворах. Тогда километры БЫЛИ рабочими, просто мы их не записали.
 *
 * Отличить одно от другого приложение не может — это знает только человек. Поэтому мы
 * спрашиваем, а не решаем за него: ошибка здесь напрямую искажает рентабельность
 * каждого заказа. И спрашиваем не «какое число взять», а что оно означает — иначе
 * человек нажмёт наугад.
 */
internal data class MileageGap(
    val gpsKm: Double,
    val odometerKm: Double,
    val gapPercent: Int,
    val differenceKm: Double,
)

/**
 * Нужно ли спрашивать. Ниже 10% — нет: GPS всегда чуть недосчитывает на поворотах, и
 * дёргать человека из-за пары процентов значит приучить его отвечать не глядя. Выше
 * 20% — спрашиваем всегда, что бы ни стояло в настройках.
 */
internal fun mileageGap(preview: EndDayPreviewGap, odometerKm: Double): MileageGap? {
    val gps = preview.gpsKm
    if (odometerKm < preview.minKm || gps <= 0) return null

    val gap = abs(gps - odometerKm) / odometerKm
    if (gap < preview.smallGap) return null

    val mustAsk = gap > preview.bigGap || preview.policy == "ask"
    if (!mustAsk) return null

    return MileageGap(
        gpsKm = gps,
        odometerKm = odometerKm,
        gapPercent = (gap * 100).roundToInt(),
        differenceKm = abs(odometerKm - gps),
    )
}

/** Ровно те поля превью, что нужны для сравнения — чтобы не тащить сюда всю модель. */
internal data class EndDayPreviewGap(
    val gpsKm: Double,
    val policy: String,
    val smallGap: Double,
    val bigGap: Double,
    val minKm: Double,
)

@Composable
internal fun MileageStep(
    gap: MileageGap,
    onChoose: (Double) -> Unit,
) {
    var manual by rememberSaveable { mutableStateOf("") }

    Text("Пробег не сходится", style = MaterialTheme.typography.titleMedium)

    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            GapRow("GPS показал", "${gap.gpsKm.roundToInt()} км")
            GapRow("Одометр показал", "${gap.odometerKm.roundToInt()} км")
            GapRow("Разница", "${gap.gapPercent}%", accent = true)
        }
    }

    Text(
        "Какой пробег учитывать для расчёта рентабельности?",
        style = MaterialTheme.typography.bodyMedium,
    )

    // Не «какое число взять», а что оно означает. Иначе человек нажмёт наугад, и
    // рентабельность каждого заказа поедет.
    MileageChoiceButton(
        title = "GPS · ${gap.gpsKm.roundToInt()} км",
        meaning = "Рабочих ${gap.gpsKm.roundToInt()} км, а ${gap.differenceKm.roundToInt()} км были личными — заезжали по своим делам.",
        onClick = { onChoose(gap.gpsKm) },
    )
    MileageChoiceButton(
        title = "Одометр · ${gap.odometerKm.roundToInt()} км",
        meaning = "Рабочих ${gap.odometerKm.roundToInt()} км: GPS потерял ${gap.differenceKm.roundToInt()} км — тоннель, подземная парковка, разряженный телефон.",
        onClick = { onChoose(gap.odometerKm) },
    )

    OutlinedTextField(
        modifier = Modifier.fillMaxWidth(),
        value = manual,
        onValueChange = { manual = it },
        label = { Text("Ввести вручную, км") },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
    )
    val typed = parseNumber(manual)
    if (typed != null && typed > gap.odometerKm) {
        Warning("Рабочий пробег не может быть больше показаний одометра.")
    }
    OutlinedButton(
        onClick = { typed?.let(onChoose) },
        enabled = typed != null && typed > 0 && typed <= gap.odometerKm,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text("Взять своё значение")
    }
}

@Composable
private fun MileageChoiceButton(title: String, meaning: String, onClick: () -> Unit) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(
                meaning,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Button(
                onClick = onClick,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.surfaceContainerHighest,
                    contentColor = MaterialTheme.colorScheme.onSurface,
                ),
            ) {
                Text("Выбрать")
            }
        }
    }
}

@Composable
private fun GapRow(label: String, value: String, accent: Boolean = false) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            value,
            style = MaterialTheme.typography.labelMedium,
            fontFamily = JetBrainsMono,
            fontWeight = if (accent) FontWeight.Bold else FontWeight.Normal,
            color = if (accent) VerdictColors.edge else MaterialTheme.colorScheme.onSurface,
        )
    }
}
