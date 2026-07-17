package com.homevisit.location

import android.graphics.BitmapFactory
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.Image

/**
 * Состояние разбора фото, пришедшего через «Поделиться» (Ф15.4).
 *
 * Раньше состояния не было вовсе: единственной реакцией на картинку был экран пакета
 * `if (batchOrders.isNotEmpty())`. Пока OCR считает на сервере (секунды), человек не
 * видел НИЧЕГО — непонятно, приняли фото или нет. А если OCR не нашёл адресов, не
 * появлялось вообще ничего: молчаливый провал, неотличимый от «приложение сломалось».
 */
data class ShareImageUi(
    val loading: Boolean = false,
    /** OCR отработал и не нашёл ни одного адреса. */
    val failed: Boolean = false,
    /** OCR не ответил (сеть/сервис недоступен) — это НЕ «нет адресов». */
    val transportError: Boolean = false,
)

/**
 * Миниатюра из байтов картинки.
 *
 * Уменьшаем при декодировании (inSampleSize), а не после: скриншот на 12 Мп в полном
 * размере — это десятки мегабайт в памяти и реальный шанс уронить приложение по OOM.
 * Картинку никуда не сохраняем — она живёт только в памяти экрана (152-ФЗ: изображение
 * транзитное, на диск не ложится).
 */
fun decodeThumbnail(bytes: ByteArray, maxPx: Int = 256): ImageBitmap? = runCatching {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
    val longest = maxOf(bounds.outWidth, bounds.outHeight)
    if (longest <= 0) return@runCatching null

    var sample = 1
    while (longest / sample > maxPx) sample *= 2

    val options = BitmapFactory.Options().apply { inSampleSize = sample }
    BitmapFactory.decodeByteArray(bytes, 0, bytes.size, options)?.asImageBitmap()
}.getOrNull()

/**
 * Карточка «фото принято»: миниатюра + что с ним сейчас происходит.
 *
 * Показывается ровно до тех пор, пока не открылся экран пакета заказов — тогда человек
 * уже видит результат, и подтверждение ему не нужно.
 */
@Composable
fun SharedImageCard(
    preview: ImageBitmap?,
    ui: ShareImageUi,
    onDismiss: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (ui.failed) VerdictColors.skipContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
        ),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier
                    .size(56.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(MaterialTheme.colorScheme.surfaceContainerHighest),
                contentAlignment = Alignment.Center,
            ) {
                if (preview != null) {
                    Image(
                        bitmap = preview,
                        contentDescription = "Добавленное фото",
                        modifier = Modifier.fillMaxWidth(),
                        contentScale = ContentScale.Crop,
                    )
                } else {
                    // Картинку не удалось раскодировать — но фото всё равно принято,
                    // и об этом надо сказать, а не молчать.
                    Text("фото", style = MaterialTheme.typography.labelSmall)
                }
            }

            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    "Фото добавлено",
                    style = MaterialTheme.typography.titleSmall,
                )
                Text(
                    when {
                        ui.loading -> "Ищу адреса на фото…"
                        ui.transportError -> "Не удалось распознать: сервис недоступен. Попробуй ещё раз."
                        ui.failed -> "Адресов на фото не нашлось — введите вручную"
                        else -> "Готово"
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            if (ui.loading) {
                CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
            } else {
                TextButton(onClick = onDismiss) { Text("Скрыть") }
            }
        }
    }
}
