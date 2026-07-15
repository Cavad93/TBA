package com.homevisit.location

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.homevisit.location.domain.HomeBreakeven
import org.junit.Rule
import org.junit.Test

/**
 * Карточка безубыточности смены (Фаза 10.2) на живом устройстве/эмуляторе: пока
 * обязательные расходы не покрыты — сколько до нуля; как покрыты — «в плюс».
 */
class HomeCardsTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun breakevenShowsRemainingWhenNotPaidOff() {
        composeRule.setContent {
            HomeVisitTheme {
                BreakevenCard(
                    HomeBreakeven(
                        fixedCosts = 3000.0, accumulatedNet = 1200.0,
                        isPaidOff = false, remainingToBreakeven = 1800.0,
                    ),
                )
            }
        }
        composeRule.onNodeWithText("Безубыточность смены").assertIsDisplayed()
    }

    @Test
    fun breakevenShowsPaidOff() {
        composeRule.setContent {
            HomeVisitTheme {
                BreakevenCard(
                    HomeBreakeven(
                        fixedCosts = 3000.0, accumulatedNet = 3500.0,
                        isPaidOff = true, remainingToBreakeven = 0.0,
                    ),
                )
            }
        }
        composeRule.onNodeWithText("Смена отбита — дальше в плюс").assertIsDisplayed()
    }
}
