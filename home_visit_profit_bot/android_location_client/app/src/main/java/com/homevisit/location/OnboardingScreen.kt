package com.homevisit.location

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
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.homevisit.location.domain.SettingType
import com.homevisit.location.domain.SettingsSection
import com.homevisit.location.ui.AppSettingsUiState

/**
 * Онбординг после регистрации: проводим по ВСЕМ секциям настроек (Этап 26/28,
 * поручение владельца). Смысл — не анкета ради анкеты: себестоимость километра,
 * планка ₽/час, тип занятости и способ заработка — входы каждого вердикта
 * «стоит ли ехать». Без них расчёт опирается на средние и советует абстрактно.
 *
 * Каталог и пояснения полей — серверные, рендер — тот же AppSettingsSection, что
 * в Настройках. Правки живут ДЕЛЬТОЙ (только тронутые ключи): фоновая загрузка
 * снапшота не может стереть ввод. Тексты — по бренд-гайду: на «ты», без эмодзи;
 * зелёный — только у главного действия.
 */

/** Секции для онбординга: зоны обслуживания живут на своей странице настроек. */
internal fun onboardingSections(sections: List<SettingsSection>): List<SettingsSection> =
    sections.filter { section -> section.fields.any { it.type != SettingType.Zones } }

@Composable
fun OnboardingScreen(
    appSettings: AppSettingsUiState,
    onRefresh: () -> Unit,
    onSave: (Map<String, Any?>) -> Unit,
    onFinish: () -> Unit,
    onSuggestAddress: (String, String) -> Unit = { _, _ -> },
) {
    val snapshot = appSettings.snapshot
    // Дельта тронутых полей — как в Настройках. Никаких fill/clear по снапшоту:
    // нетронутое всегда рисуется из свежего снапшота, тронутое — из рук человека.
    val textEdits = remember { mutableStateMapOf<String, String>() }
    val boolEdits = remember { mutableStateMapOf<String, Boolean>() }

    var page by rememberSaveable { mutableStateOf(0) }
    var saveRequested by rememberSaveable { mutableStateOf(false) }
    val sections = onboardingSections(snapshot?.sections.orEmpty())
    // Страницы: 0 — зачем это; 1..N — секции; N+1 — сохранение.
    val lastPage = sections.size + 1

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            LinearProgressIndicator(
                progress = { (page + 1).toFloat() / (lastPage + 1) },
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                "Шаг ${page + 1} из ${lastPage + 1}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            when {
                page == 0 -> IntroPage(onStart = { page = 1 }, onSkip = onFinish)

                snapshot == null -> {
                    Text(
                        "Загружаю каталог настроек…",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (appSettings.message.isNotBlank()) {
                        Text(appSettings.message, style = MaterialTheme.typography.bodySmall)
                    }
                    OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = onRefresh) {
                        Text("Повторить загрузку")
                    }
                    TextButton(modifier = Modifier.fillMaxWidth(), onClick = onFinish) {
                        Text("Настроить позже")
                    }
                }

                page <= sections.size -> {
                    val section = sections[page - 1]
                    Text(
                        "Эти параметры входят в расчёт каждого заказа. Заполни, что знаешь, " +
                            "— остальное можно уточнить позже в Настройках.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    AppSettingsSection(
                        section = section,
                        textEdits = textEdits,
                        boolEdits = boolEdits,
                        rejectedReasons = appSettings.rejected.associate { it.key to it.reason },
                        addressCandidates = appSettings.addressCandidates,
                        onSuggestAddress = onSuggestAddress,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(modifier = Modifier.weight(1f), onClick = { page -= 1 }) {
                            Text("Назад")
                        }
                        Button(
                            modifier = Modifier.weight(1f),
                            colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
                            onClick = { page += 1 },
                        ) {
                            Text("Дальше")
                        }
                    }
                }

                else -> {
                    Text(
                        "Готово",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        "Сохраняем ответы — с этого момента вердикты считаются по твоим " +
                            "цифрам, а не по средним.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (saveRequested && appSettings.message.isNotBlank()) {
                        Text(appSettings.message, style = MaterialTheme.typography.bodyMedium)
                    }
                    if (saveRequested && appSettings.rejected.isNotEmpty()) {
                        appSettings.rejected.forEach { bad ->
                            Text(
                                "${bad.label} — ${bad.reason.substringAfter(": ", bad.reason)}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                        OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = { page = 1 }) {
                            Text("Вернуться и поправить")
                        }
                    }
                    if (!saveRequested) {
                        Button(
                            modifier = Modifier.fillMaxWidth(),
                            enabled = !appSettings.isLoading,
                            colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
                            onClick = {
                                onSave(collectSettingsChanges(snapshot.sections, textEdits, boolEdits))
                                saveRequested = true
                            },
                        ) {
                            Text("Сохранить и начать работу")
                        }
                        OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = { page -= 1 }) {
                            Text("Назад")
                        }
                    } else {
                        Button(
                            modifier = Modifier.fillMaxWidth(),
                            enabled = !appSettings.isLoading,
                            colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
                            onClick = onFinish,
                        ) {
                            Text(if (appSettings.isLoading) "Сохраняю…" else "В приложение")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun IntroPage(onStart: () -> Unit, onSkip: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "Пара минут — и советы станут твоими",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                "Сейчас приложение спросит то, из чего складывается каждый вердикт " +
                    "«стоит ли ехать»: сколько стоит твой километр, ниже какой планки " +
                    "₽/час заказ не интересен, как ты зарабатываешь и на чём ездишь.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Это важно: без твоих цифр расчёты опираются на средние значения — " +
                    "советы будут абстрактными и могут звать на невыгодное. " +
                    "С твоими ответами каждый вердикт персональный.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Не знаешь какое-то значение — оставь как есть и уточни позже: " +
                    "всё меняется в Настройках в любой момент.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
    Button(
        modifier = Modifier.fillMaxWidth(),
        colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
        onClick = onStart,
    ) {
        Text("Начать")
    }
    TextButton(modifier = Modifier.fillMaxWidth(), onClick = onSkip) {
        Text("Настроить позже (советы будут по средним)")
    }
}
