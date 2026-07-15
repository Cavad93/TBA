package com.homevisit.location

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Smoke-тесты на живом устройстве/эмуляторе (Firebase Test Lab и эмулятор в CI):
 * приложение запускается без краша, рисует экран авторизации и переход к регистрации
 * работает. Без токена сессии MainActivity показывает AuthFlow — сеть при этом не
 * дёргается, поэтому тест герметичен и не зависит от доступности сервера.
 *
 * Это главный анти-краш-барьер клиента: если onCreate/Compose падает при запуске,
 * сборка краснеет здесь, раньше, чем APK уедет к людям.
 */
@RunWith(AndroidJUnit4::class)
class AppLaunchTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun launchesToAuthScreenWithoutCrash() {
        // Бренд виден в любом режиме авторизации → Activity поднялась и Compose нарисовал.
        composeRule.onNodeWithText("Визиторкрут").assertIsDisplayed()
        // Экран входа — режим по умолчанию.
        composeRule.onNodeWithText("Вход").assertIsDisplayed()
    }

    @Test
    fun switchesToRegistration() {
        composeRule.onNodeWithText("Нет аккаунта? Зарегистрироваться").performClick()
        composeRule.onNodeWithText("Регистрация").assertIsDisplayed()
    }
}
