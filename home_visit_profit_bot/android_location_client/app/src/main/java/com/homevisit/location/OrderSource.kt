package com.homevisit.location

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/**
 * Настраиваемый ярлык источника заказов.
 *
 * Приложение универсальное (врач на выезде, таксист, курьер, мастер), поэтому
 * пользователь выбирает под свою сферу, как называть тех, от кого приходят заказы.
 * У каждого пресета зашиты падежные формы, чтобы подписи в интерфейсе склонялись
 * верно («По паркам», «Фильтр по парку», «Список парков пуст»).
 */
data class OrderSourcePreset(
    val key: String,
    val nomSingle: String,  // Компания   — именительный ед.
    val nomPlural: String,  // Компании   — именительный мн. (= винительный мн. для неодуш.: «Добавьте компании»)
    val genPlural: String,  // компаний   — родительный мн. («Список компаний пуст»)
    val datSingle: String,  // компании   — «по компании»
    val datPlural: String,  // компаниям  — «По компаниям»
)

/**
 * Глобальное наблюдаемое состояние выбранного пресета. Значение читается в
 * Compose-подписях и в сообщениях ViewModel; сохраняется в SharedPreferences
 * (см. MainActivity: загрузка в onCreate, персист через LaunchedEffect).
 */
object OrderSource {
    val presets = listOf(
        OrderSourcePreset("company", "Компания", "Компании", "компаний", "компании", "компаниям"),
        OrderSourcePreset("clinic", "Клиника", "Клиники", "клиник", "клинике", "клиникам"),
        OrderSourcePreset("park", "Парк", "Парки", "парков", "парку", "паркам"),
        OrderSourcePreset("service", "Сервис", "Сервисы", "сервисов", "сервису", "сервисам"),
        OrderSourcePreset("platform", "Площадка", "Площадки", "площадок", "площадке", "площадкам"),
    )

    val default: OrderSourcePreset = presets.first()

    fun byKey(key: String?): OrderSourcePreset =
        presets.firstOrNull { it.key == key } ?: default

    var current: OrderSourcePreset by mutableStateOf(default)
}
