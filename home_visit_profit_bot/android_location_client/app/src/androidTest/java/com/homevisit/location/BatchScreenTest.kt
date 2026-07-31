package com.homevisit.location

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement
import com.homevisit.location.domain.AddressCandidate
import com.homevisit.location.domain.BatchOrder
import org.junit.Rule
import org.junit.Test

/**
 * Экран подтверждения пакета заказов (Ф15.2) на живом устройстве/эмуляторе.
 *
 * Проверяем то, ради чего экран сделали редактируемым (отчёт 818): статусы видны,
 * доход вписывается у каждого пункта и доезжает до вызывающего, а тап по варианту
 * превращает жёлтую строку в готовую к добавлению.
 */
class BatchScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun orders() = listOf(
        BatchOrder("Ленина 5", 1500.0,
            resolved = AddressCandidate("ул. Ленина, 5", 59.9, 30.3), candidates = emptyList()),
        BatchOrder("Мира 12", null, resolved = null,
            candidates = listOf(AddressCandidate("Мира 12а", 59.91, 30.31),
                AddressCandidate("Мира 12б", 59.92, 30.32))),
        BatchOrder("абвгд непонятно", null, resolved = null, candidates = emptyList()),
    )

    @Test
    fun showsStatusesAndReadyCount() {
        composeRule.setContent {
            HomeVisitTheme { BatchOrdersScreen(orders(), onAddGreen = {}, onClose = {}) }
        }
        composeRule.onNodeWithText("Ленина 5").assertIsDisplayed()
        composeRule.onNodeWithText("Мира 12").assertIsDisplayed()
        composeRule.onNodeWithText("абвгд непонятно").assertIsDisplayed()
        // Готов пока один — распознанный. Жёлтый ждёт выбора варианта.
        composeRule.onNodeWithText("Добавить (1)").assertIsDisplayed()
    }

    @Test
    fun pickingCandidateMakesOrderReady() {
        composeRule.setContent {
            HomeVisitTheme { BatchOrdersScreen(orders(), onAddGreen = {}, onClose = {}) }
        }
        composeRule.onNodeWithText("Мира 12а").performClick()
        // Вариант выбран — строка стала готовой, счётчик вырос.
        composeRule.onNodeWithText("Вариант выбран").assertIsDisplayed()
        composeRule.onNodeWithText("Добавить (2)").assertIsDisplayed()
    }

    @Test
    fun incomeIsEditableAndReachesCallback() {
        var added: List<BatchOrder> = emptyList()
        composeRule.setContent {
            HomeVisitTheme { BatchOrdersScreen(orders(), onAddGreen = { added = it }, onClose = {}) }
        }
        // У распознанного заказа доход подставлен из разбора и правится руками.
        composeRule.onNodeWithText("1500").performTextReplacement("2300")
        composeRule.onNodeWithText("Добавить (1)").performClick()

        assert(added.size == 1) { "ожидался один готовый заказ, получено ${added.size}" }
        assert(added.first().income == 2300.0) { "доход не доехал: ${added.first().income}" }
    }
}
