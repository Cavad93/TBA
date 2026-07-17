package com.homevisit.location

/**
 * Разбор и склейка адреса «Город + Улица, дом».
 *
 * Настройка старт/финиш хранится ОДНОЙ строкой (её резолвит сервер целиком —
 * потребители не трогаем). А в UI город и улица-дом разведены на два поля: город
 * съедал ширину подсказки, и номер дома был не виден (отчёт 3 из Telegram).
 * Здесь — чистая логика этого разведения, чтобы её можно было покрыть тестами.
 */

// Типы улиц: если строка начинается с одного из них, города в ней нет — это уже адрес.
private val STREET_PREFIXES = setOf(
    "ул", "улица", "пр-кт", "пр-т", "проспект", "пр", "пер", "переулок", "б-р", "бульвар",
    "ш", "шоссе", "наб", "набережная", "пл", "площадь", "проезд", "линия", "аллея",
    "туп", "тупик", "мкр", "микрорайон", "тракт", "кв-л", "квартал", "д", "дом", "стр", "к",
)

/**
 * Похоже ли начало строки на название города, а не на улицу/дом. Город — без цифр
 * и не начинается с уличного типа: «г Санкт-Петербург», «Казань» — да; «ул Ленина»,
 * «Ленина, 5» — нет (там первая часть — уже адрес).
 */
fun looksLikeCity(head: String): Boolean {
    val text = head.trim().lowercase()
    if (text.isEmpty() || text.any { it.isDigit() }) return false
    val firstWord = text.substringBefore(' ').trimEnd('.')
    return firstWord !in STREET_PREFIXES
}

/**
 * Разбить полный адрес на (город, «улица, дом»). Если первая часть до запятой не
 * похожа на город — считаем, что города нет, и вся строка уходит в адрес: лучше
 * оставить поле города пустым, чем затащить туда «ул Ленина».
 */
fun splitCityAddress(full: String): Pair<String, String> {
    val text = full.trim()
    val comma = text.indexOf(',')
    if (comma <= 0) return "" to text
    val head = text.substring(0, comma).trim()
    val tail = text.substring(comma + 1).trim()
    return if (looksLikeCity(head)) head to tail else "" to text
}

/**
 * Склеить город и улицу-дом в одну строку для сохранения. Город не дублируем, если
 * он уже есть в адресной части (тап по подсказке кладёт улицу-дом без города, но
 * ручной ввод мог включить город — тогда вторая копия не нужна).
 */
fun joinCityAddress(city: String, streetHouse: String): String {
    val cityPart = city.trim()
    val addressPart = streetHouse.trim()
    return when {
        cityPart.isEmpty() -> addressPart
        addressPart.isEmpty() -> cityPart
        addressPart.contains(cityPart, ignoreCase = true) -> addressPart
        else -> "$cityPart, $addressPart"
    }
}

/**
 * Нормализованный вид адреса для сравнения «тот же ли это адрес». Регистр, лишние
 * пробелы и знаки-разделители не должны делать один адрес двумя. Номер квартиры в
 * адресную строку заказа обычно не попадает — совпадение означает «тот же дом»,
 * а разные пациенты/квартиры в нём человек подтвердит вручную.
 */
fun normalizeAddressForCompare(address: String): String =
    address.lowercase()
        .replace(Regex("[,.;]+"), " ")
        .replace(Regex("\\s+"), " ")
        .trim()

/**
 * Есть ли уже такой адрес среди адресов активной ленты (сравнение нормализованное).
 * Пустой адрес дублем не считается — сравнивать нечего.
 */
fun addressAlreadyInRoute(address: String, routeAddresses: List<String>): Boolean {
    val target = normalizeAddressForCompare(address)
    if (target.isEmpty()) return false
    return routeAddresses.any { normalizeAddressForCompare(it) == target }
}
