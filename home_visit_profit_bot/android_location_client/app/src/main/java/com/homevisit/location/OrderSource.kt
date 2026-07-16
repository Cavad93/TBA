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
    val genSingle: String,  // компании   — родительный ед. («Без компании»)
    val datSingle: String,  // компании   — «по компании»
    val datPlural: String,  // компаниям  — «По компаниям»
)

/**
 * Глобальное наблюдаемое состояние выбранного пресета. Значение читается в
 * Compose-подписях и в сообщениях ViewModel; сохраняется в SharedPreferences
 * (см. MainActivity: загрузка в onCreate, персист через LaunchedEffect).
 */
object OrderSource {
    // genSingle — именно родительный ед. («Без клиники»), а не дательный datSingle
    // («клинике»): подставь дательный, и получилось бы «Без клинике».
    val presets = listOf(
        OrderSourcePreset("company", "Компания", "Компании", "компаний", "компании", "компании", "компаниям"),
        OrderSourcePreset("clinic", "Клиника", "Клиники", "клиник", "клиники", "клинике", "клиникам"),
        OrderSourcePreset("park", "Парк", "Парки", "парков", "парка", "парку", "паркам"),
        OrderSourcePreset("service", "Сервис", "Сервисы", "сервисов", "сервиса", "сервису", "сервисам"),
        OrderSourcePreset("platform", "Площадка", "Площадки", "площадок", "площадки", "площадке", "площадкам"),
    )

    val default: OrderSourcePreset = presets.first()

    fun byKey(key: String?): OrderSourcePreset =
        presets.firstOrNull { it.key == key } ?: default

    var current: OrderSourcePreset by mutableStateOf(default)
}
