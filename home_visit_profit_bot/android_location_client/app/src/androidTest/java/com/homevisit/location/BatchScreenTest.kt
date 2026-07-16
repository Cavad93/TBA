package com.homevisit.location

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.homevisit.location.domain.AddressCandidate
import com.homevisit.location.domain.BatchOrder
import org.junit.Rule
import org.junit.Test

/**
 * Экран подтверждения пакета заказов (Ф15.2) на живом устройстве/эмуляторе: зелёные/
 * жёлтые/красные показаны, кнопка «Добавить все зелёные» считает готовые.
 */
class BatchScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun showsStatusesAndGreenCount() {
        val orders = listOf(
            BatchOrder("Ленина 5", 1500.0,
                resolved = AddressCandidate("ул. Ленина, 5", 59.9, 30.3), candidates = emptyList()),
            BatchOrder("Мира 12", null, resolved = null,
                candidates = listOf(AddressCandidate("Мира 12а", 59.91, 30.31),
                    AddressCandidate("Мира 12б", 59.92, 30.32))),
            BatchOrder("абвгд непонятно", null, resolved = null, candidates = emptyList()),
        )
        composeRule.setContent {
            HomeVisitTheme {
                BatchOrdersScreen(orders, onAddGreen = {}, onClose = {})
            }
        }
        composeRule.onNodeWithText("Ленина 5").assertIsDisplayed()
        composeRule.onNodeWithText("Мира 12").assertIsDisplayed()
        composeRule.onNodeWithText("абвгд непонятно").assertIsDisplayed()
        // Одна зелёная → кнопка со счётчиком 1.
        composeRule.onNodeWithText("Добавить все зелёные (1)").assertIsDisplayed()
    }
}
