@file:OptIn(androidx.compose.ui.text.ExperimentalTextApi::class)

package com.homevisit.location

import androidx.compose.material3.Typography
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight

// Дизайн-система Визиторкрут: Golos Text — весь UI/текст; JetBrains Mono — числа.
// Шрифты вариативные (ось wght); веса задаём через FontVariation (API 26+, minSdk=26).

private fun golos(weight: Int) = Font(
    resId = R.font.golos_text,
    weight = FontWeight(weight),
    variationSettings = FontVariation.Settings(FontVariation.weight(weight)),
)

val GolosText = FontFamily(golos(400), golos(500), golos(600), golos(700), golos(800))

private fun mono(weight: Int) = Font(
    resId = R.font.jetbrains_mono,
    weight = FontWeight(weight),
    variationSettings = FontVariation.Settings(FontVariation.weight(weight)),
)

/** JetBrains Mono — для чисел (₽ / км / мин / ₽·ч), табличные цифры ведут вёрстку. */
val JetBrainsMono = FontFamily(mono(400), mono(500), mono(600), mono(700))

private val base = Typography()

val AppTypography = Typography(
    displayLarge = base.displayLarge.copy(fontFamily = GolosText),
    displayMedium = base.displayMedium.copy(fontFamily = GolosText),
    displaySmall = base.displaySmall.copy(fontFamily = GolosText),
    headlineLarge = base.headlineLarge.copy(fontFamily = GolosText),
    headlineMedium = base.headlineMedium.copy(fontFamily = GolosText),
    headlineSmall = base.headlineSmall.copy(fontFamily = GolosText),
    titleLarge = base.titleLarge.copy(fontFamily = GolosText),
    titleMedium = base.titleMedium.copy(fontFamily = GolosText),
    titleSmall = base.titleSmall.copy(fontFamily = GolosText),
    bodyLarge = base.bodyLarge.copy(fontFamily = GolosText),
    bodyMedium = base.bodyMedium.copy(fontFamily = GolosText),
    bodySmall = base.bodySmall.copy(fontFamily = GolosText),
    labelLarge = base.labelLarge.copy(fontFamily = GolosText),
    labelMedium = base.labelMedium.copy(fontFamily = GolosText),
    labelSmall = base.labelSmall.copy(fontFamily = GolosText),
)
