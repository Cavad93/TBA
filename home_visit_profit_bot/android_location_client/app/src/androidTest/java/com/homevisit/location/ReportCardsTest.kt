package com.homevisit.location

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.homevisit.location.domain.ReportCancellations
import org.junit.Rule
import org.junit.Test

/**
 * Карточка потерь (Фаза 11.4) на живом устройстве/эмуляторе: отмены в пути, пустые
 * отклики и совет о предоплате — правда о том, что съедает доход.
 */
class ReportCardsTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun cancellationsCardShowsLossesAndAdvice() {
        composeRule.setContent {
            HomeVisitTheme {
                CancellationsCard(
                    ReportCancellations(
                        cancelCount = 2, cancelMoney = 900.0, emptyLeadsMoney = 1200.0,
                        advice = "Отмены и пустые отклики съели 30% дохода. Стоит брать предоплату.",
                    ),
                )
            }
        }
        composeRule.onNodeWithText("Потери: отмены и пустые отклики").assertIsDisplayed()
        composeRule.onNodeWithText("Отмены и пустые отклики съели 30% дохода. Стоит брать предоплату.")
            .assertIsDisplayed()
    }
}
