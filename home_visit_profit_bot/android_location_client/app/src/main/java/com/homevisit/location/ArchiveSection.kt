package com.homevisit.location

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.homevisit.location.domain.ArchiveRange
import com.homevisit.location.domain.ArchiveSort
import com.homevisit.location.domain.ArchiveUiState
import com.homevisit.location.domain.ArchivedVisit

/**
 * «+ архив» под ползунком завершения смены.
 *
 * Заказы с временем добавления, временем закрытия и результатом (выполнен/отменён).
 * Список компактный: подробности раскрываются по клику, чтобы не загромождать. По
 * умолчанию — закрытые сегодня; период выбирается «с … по …».
 */
@Composable
fun ArchiveSection(
    archive: ArchiveUiState,
    onRange: (ArchiveRange) -> Unit,
    onSort: (ArchiveSort) -> Unit,
    onOpen: (String) -> Unit,
) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    Spacer(Modifier.height(2.dp))
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .clickable { expanded = !expanded }
            .padding(horizontal = 6.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            "Архив",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.weight(1f),
        )
        Icon(
            imageVector = if (expanded) Icons.Filled.Remove else Icons.Filled.Add,
            contentDescription = if (expanded) "Скрыть архив" else "Показать архив",
            tint = MaterialTheme.colorScheme.primary,
        )
    }
    if (!expanded) return

    OptionGrid(
        options = ArchiveRange.entries.toList(),
        selected = archive.range,
        label = { it.title },
        onSelect = onRange,
    )
    OptionGrid(
        options = ArchiveSort.entries.toList(),
        selected = archive.sort,
        label = { it.title },
        onSelect = onSort,
    )

    if (archive.visits.isEmpty()) {
        CompactCard(
            "Пусто",
            "За выбранный период нет ни завершённых, ни отменённых заказов.",
        )
        return
    }

    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        archive.visits.forEach { visit ->
            ArchiveRow(visit = visit, onOpen = { onOpen(visit.id) })
        }
    }
}

/** Строка архива: адрес, когда закрыт и чем кончилось. Клик — подробности заказа. */
@Composable
private fun ArchiveRow(visit: ArchivedVisit, onOpen: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onOpen() },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    visit.address,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                )
                Text(
                    "добавлен ${visit.addedAtText} · закрыт ${visit.closedAtText}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                )
            }
            OutcomeBadge(done = visit.done)
        }
    }
}

@Composable
private fun OutcomeBadge(done: Boolean) {
    Box(
        Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(if (done) VerdictColors.goContainer else VerdictColors.skipContainer)
            .padding(horizontal = 8.dp, vertical = 4.dp),
    ) {
        Text(
            if (done) "выполнен" else "отменён",
            style = MaterialTheme.typography.labelSmall,
            color = if (done) VerdictColors.onGoContainer else VerdictColors.onSkipContainer,
        )
    }
}
