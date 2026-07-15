package com.homevisit.location

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.homevisit.location.domain.ArrivalWindow
import com.homevisit.location.domain.FixTimePrice
import org.junit.Rule
import org.junit.Test

/**
 * Рендер карточек Ленты на живом устройстве/эмуляторе (Фаза 4.2/4.3): окно прибытия
 * и цена фикс-времени показывают текст, который сервер уже собрал. Пустые списки —
 * карточки не рисуются (тут проверяем непустые).
 */
class RouteCardsTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun arrivalWindowShowsHumanText() {
        composeRule.setContent {
            HomeVisitTheme {
                ArrivalWindowsCard(
                    listOf(ArrivalWindow(visitId = 1, address = "Ленина 40", text = "примерно 14:00–16:00")),
                )
            }
        }
        composeRule.onNodeWithText("Когда вас ждать").assertIsDisplayed()
        composeRule.onNodeWithText("Ленина 40: примерно 14:00–16:00").assertIsDisplayed()
    }

    @Test
    fun fixTimePriceShowsSurchargeHint() {
        composeRule.setContent {
            HomeVisitTheme {
                FixTimePricesCard(
                    listOf(
                        FixTimePrice(
                            anchorVisitId = 1, idleMinutes = 90, deltaHourly = 180,
                            suggestedSurcharge = 300,
                            text = "фикс-время съедает ~180 ₽/час дня (простой 90 мин); добавь к цене ~300 ₽",
                        ),
                    ),
                )
            }
        }
        composeRule.onNodeWithText("Цена фиксированного времени").assertIsDisplayed()
    }
}
