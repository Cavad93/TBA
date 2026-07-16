package com.homevisit.location

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

/**
 * Чипы недавних адресов (Ф13.1) на живом устройстве/эмуляторе: показывают адреса
 * истории, тап подставляет адрес в один тап.
 */
class RecentChipsTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun tapChipPicksAddress() {
        var picked = ""
        composeRule.setContent {
            HomeVisitTheme {
                RecentAddressChips(listOf("Ленина 5", "Мира 12")) { picked = it }
            }
        }
        composeRule.onNodeWithText("Ленина 5").assertIsDisplayed()
        composeRule.onNodeWithText("Мира 12").assertIsDisplayed()
        composeRule.onNodeWithText("Мира 12").performClick()
        assertEquals("Мира 12", picked)
    }
}
