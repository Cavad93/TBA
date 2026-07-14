package com.homevisit.location

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.NearMe
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.homevisit.location.domain.NavTarget
import com.homevisit.location.domain.ServerRouteLeg

/**
 * Кнопка «Поехали» и всё, что вокруг неё.
 *
 * Главный принцип экрана: пока человек едет — главное действие «Поехали»; когда GPS
 * говорит, что он на адресе, главным становится «Готово». Обе кнопки в карточке
 * всегда, но выделена ровно одна — та, которую сейчас разумно нажать. За рулём
 * различать их надо не читая.
 */

/** Что мы посчитали САМИ — OSRM, наши деньги. Ни одна цифра здесь не из Яндекса. */
@Composable
internal fun NavFacts(leg: ServerRouteLeg?, net: Double?) {
    val parts = buildList {
        if (leg != null && leg.km > 0) add("${oneDecimal(leg.km)} км")
        if (leg != null && leg.minutes > 0) add("${leg.minutes.toInt()} мин")
        if (net != null && net != 0.0) add("${money(net)} чистыми")
    }
    if (parts.isEmpty()) return
    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        parts.forEach { part ->
            Box(
                Modifier
                    .clip(RoundedCornerShape(7.dp))
                    .background(MaterialTheme.colorScheme.surfaceContainerHighest)
                    .padding(horizontal = 8.dp, vertical = 4.dp),
            ) {
                Text(
                    part,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

/**
 * Крупная кнопка «Поехали».
 *
 * [primary] = true, пока человек в дороге. Когда он на адресе, кнопка гаснет до
 * контурной: уехать всё ещё можно (вдруг ошибся домом), но глаз за неё не цепляется.
 */
@Composable
internal fun GoButton(
    target: NavTarget?,
    primary: Boolean,
    remaining: Int,
    onGo: () -> Unit,
    onCopyCoordinates: () -> Unit,
) {
    if (target == null) {
        // Координат у заказа нет — вести некуда. Показывать кнопку, которая
        // отправит Яндексу строку адреса и уведёт не туда, честнее не показывать вовсе.
        return
    }
    if (remaining <= 0) {
        // Переходы за сутки кончились. Шестое нажатие открыло бы рекламную страницу
        // Яндекса вместо навигатора — это выглядело бы как поломка приложения. Лучше
        // сказать правду и отдать координаты.
        ExhaustedGoButton(onCopyCoordinates)
        return
    }
    if (primary) {
        Button(
            modifier = Modifier.fillMaxWidth().height(54.dp),
            onClick = onGo,
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = VerdictColors.route,
                contentColor = Color.White,
            ),
        ) {
            Icon(Icons.Filled.NearMe, contentDescription = null, modifier = Modifier.size(20.dp))
            Text(
                "  Поехали",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
        }
    } else {
        OutlinedButton(
            modifier = Modifier.fillMaxWidth(),
            onClick = onGo,
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, VerdictColors.route),
        ) {
            Icon(
                Icons.Filled.NearMe,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
                tint = VerdictColors.route,
            )
            Text("  Поехали", color = VerdictColors.route)
        }
    }
    if (remaining in 1..NavQuota.WARN_BELOW) {
        Text(
            "Осталось запусков сегодня: $remaining. Дальше отдам координаты — " +
                "вставите в навигатор сами. Работаем над тем, чтобы лимита не было.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

/**
 * Кнопка, когда переходы за сутки исчерпаны.
 *
 * Лимит не наш — Яндекс пускает по ссылке пять раз в сутки, пока у нас нет ключа
 * доступа. Ключ дают тем, у кого уже есть работающий сервис и статистика, так что
 * это временно. Молчать об этом нельзя: человек должен понимать, что происходит,
 * иначе решит, что приложение сломалось.
 */
@Composable
private fun ExhaustedGoButton(onCopyCoordinates: () -> Unit) {
    OutlinedButton(
        modifier = Modifier.fillMaxWidth().height(50.dp),
        onClick = onCopyCoordinates,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, VerdictColors.route),
    ) {
        Icon(
            Icons.Filled.ContentCopy,
            contentDescription = null,
            modifier = Modifier.size(18.dp),
            tint = VerdictColors.route,
        )
        Text("  Скопировать координаты", color = VerdictColors.route)
    }
    Text(
        "Пять запусков навигатора за сутки — лимит Яндекса, пока у нас нет их ключа " +
            "доступа. Мы над этим работаем. Координаты лягут в буфер обмена: вставьте " +
            "их в навигатор и поезжайте.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

/**
 * Отсчёт перед автозапуском навигатора.
 *
 * Приложение вот-вот заберёт экран себе. Без крупного счётчика и кнопки «Не надо»
 * это ощущается как потеря управления телефоном — поэтому и то, и другое здесь есть.
 */
@Composable
internal fun AutoOpenCountdownCard(
    address: String,
    secondsLeft: Int,
    totalSeconds: Int,
    onGoNow: () -> Unit,
    onCancel: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = VerdictColors.routeContainer),
        border = BorderStroke(1.dp, VerdictColors.route),
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                CountdownRing(secondsLeft = secondsLeft, totalSeconds = totalSeconds)
                Column(Modifier.weight(1f)) {
                    Text(
                        "Следующий: $address",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = VerdictColors.onRouteContainer,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        "Открою навигатор через $secondsLeft ${secondsWord(secondsLeft)}",
                        style = MaterialTheme.typography.bodySmall,
                        color = VerdictColors.onRouteContainer,
                    )
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(
                    modifier = Modifier.weight(1f),
                    onClick = onGoNow,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = VerdictColors.route,
                        contentColor = Color.White,
                    ),
                ) {
                    Text("Ехать сейчас")
                }
                OutlinedButton(modifier = Modifier.weight(1f), onClick = onCancel) {
                    Text("Не надо")
                }
            }
        }
    }
}

@Composable
private fun CountdownRing(secondsLeft: Int, totalSeconds: Int) {
    val fraction = if (totalSeconds <= 0) 0f else (secondsLeft.toFloat() / totalSeconds).coerceIn(0f, 1f)
    val track = MaterialTheme.colorScheme.surfaceContainerHighest
    Box(Modifier.size(46.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(46.dp)) {
            val stroke = 4.dp.toPx()
            val inset = stroke / 2
            val box = Size(size.width - stroke, size.height - stroke)
            drawArc(
                color = track,
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                topLeft = Offset(inset, inset),
                size = box,
                style = Stroke(width = stroke),
            )
            drawArc(
                color = VerdictColors.route,
                startAngle = -90f,
                sweepAngle = 360f * fraction,
                useCenter = false,
                topLeft = Offset(inset, inset),
                size = box,
                style = Stroke(width = stroke),
            )
        }
        Text(
            "$secondsLeft",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = VerdictColors.onRouteContainer,
        )
    }
}

/**
 * «Заказ закрыт сам. Вернуть?»
 *
 * Автозакрытие срабатывает по догадке: человек долго простоял у адреса. Но простоять
 * он мог и в кафе напротив. Пока полоска висит — закрытие можно откатить.
 */
@Composable
internal fun UndoAutoCloseCard(address: String, onUndo: () -> Unit, onDismiss: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = VerdictColors.goContainer),
        border = BorderStroke(1.dp, VerdictColors.go),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 8.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    "Закрыл заказ сам",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = VerdictColors.onGoContainer,
                )
                Text(
                    address,
                    style = MaterialTheme.typography.bodySmall,
                    color = VerdictColors.onGoContainer,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            TextButton(onClick = onUndo) {
                Text("Вернуть", fontWeight = FontWeight.Bold, color = VerdictColors.onGoContainer)
            }
            TextButton(onClick = onDismiss) {
                Text("Ок", color = VerdictColors.onGoContainer)
            }
        }
    }
}

private fun secondsWord(value: Int): String {
    val tens = value % 100
    if (tens in 11..14) return "секунд"
    return when (value % 10) {
        1 -> "секунду"
        2, 3, 4 -> "секунды"
        else -> "секунд"
    }
}
