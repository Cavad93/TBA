package com.homevisit.location.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.homevisit.location.domain.AuthUser

/**
 * Экран аутентификации. Показывается, пока нет токена сессии. При успешном входе
 * вызывает onAuthenticated(token, user) — дальше приложение работает под аккаунтом.
 */
@Composable
fun AuthFlow(
    viewModel: AuthViewModel,
    onAuthenticated: (String, AuthUser?) -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Визиторкрут",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "Навигатор показывает, куда ехать.\nМы показываем — стоит ли ехать.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(8.dp))

            when (state.mode) {
                AuthMode.Login -> LoginForm(state, viewModel, onAuthenticated)
                AuthMode.Register -> RegisterForm(state, viewModel)
                AuthMode.Verify -> VerifyForm(state, viewModel, onAuthenticated)
                AuthMode.Forgot -> ForgotForm(state, viewModel)
                AuthMode.Reset -> ResetForm(state, viewModel)
            }

            if (state.message.isNotBlank()) {
                Text(
                    state.message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                    textAlign = TextAlign.Center,
                )
            }
            if (state.isLoading) {
                CircularProgressIndicator(modifier = Modifier.height(28.dp))
            }
        }
    }
}

@Composable
private fun LoginForm(state: AuthUiState, viewModel: AuthViewModel, onAuthenticated: (String, AuthUser?) -> Unit) {
    var email by rememberSaveable { mutableStateOf(state.pendingEmail) }
    var password by rememberSaveable { mutableStateOf("") }
    Text("Вход", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
    EmailField(email) { email = it }
    PasswordField(password, "Пароль") { password = it }
    Button(
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.isLoading,
        onClick = { viewModel.login(email, password, onAuthenticated) },
    ) { Text("Войти") }
    TextButton(onClick = { viewModel.switchMode(AuthMode.Register) }) {
        Text("Нет аккаунта? Зарегистрироваться")
    }
    TextButton(onClick = { viewModel.switchMode(AuthMode.Forgot) }) {
        Text("Забыли пароль?")
    }
}

@Composable
private fun RegisterForm(state: AuthUiState, viewModel: AuthViewModel) {
    var email by rememberSaveable { mutableStateOf("") }
    var nickname by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var consentGiven by rememberSaveable { mutableStateOf(false) }
    val uriHandler = LocalUriHandler.current
    Text("Регистрация", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
    EmailField(email) { email = it }
    OutlinedTextField(
        value = nickname,
        onValueChange = { nickname = it },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        label = { Text("Ник (как к вам обращаться)") },
    )
    PasswordField(password, "Пароль (от 8 символов)") { password = it }

    // Согласие на обработку ПДн (152-ФЗ): явная галочка, по умолчанию снята.
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked = consentGiven, onCheckedChange = { consentGiven = it })
        Text(
            "Я даю согласие на обработку моих персональных данных",
            style = MaterialTheme.typography.bodySmall,
        )
    }
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        TextButton(onClick = { uriHandler.openUri(AuthViewModel.CONSENT_URL) }) {
            Text("Согласие", style = MaterialTheme.typography.bodySmall)
        }
        TextButton(onClick = { uriHandler.openUri(AuthViewModel.POLICY_URL) }) {
            Text("Политика конфиденциальности", style = MaterialTheme.typography.bodySmall)
        }
    }

    Button(
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.isLoading && consentGiven,
        onClick = { viewModel.register(email, password, nickname, null) },
    ) { Text("Создать аккаунт") }
    TextButton(onClick = { viewModel.switchMode(AuthMode.Login) }) {
        Text("Уже есть аккаунт? Войти")
    }
    Text(
        "Мы собираем минимум данных: e-mail, ник и рабочие показатели. Код подтверждения придёт на почту.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Center,
    )
}

@Composable
private fun VerifyForm(state: AuthUiState, viewModel: AuthViewModel, onAuthenticated: (String, AuthUser?) -> Unit) {
    var code by rememberSaveable { mutableStateOf("") }
    Text("Подтверждение e-mail", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
    Text(
        "Код отправлен на ${state.pendingEmail}",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Center,
    )
    OutlinedTextField(
        value = code,
        onValueChange = { code = it },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        label = { Text("Код из письма") },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
    )
    Button(
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.isLoading,
        onClick = { viewModel.verify(code, onAuthenticated) },
    ) { Text("Подтвердить") }
    TextButton(onClick = { viewModel.resend() }) { Text("Отправить код повторно") }
    TextButton(onClick = { viewModel.switchMode(AuthMode.Login) }) { Text("Назад ко входу") }
}

@Composable
private fun ForgotForm(state: AuthUiState, viewModel: AuthViewModel) {
    var email by rememberSaveable { mutableStateOf(state.pendingEmail) }
    Text("Сброс пароля", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
    Text(
        "Введите e-mail — пришлём код для сброса пароля.",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Center,
    )
    EmailField(email) { email = it }
    Button(
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.isLoading,
        onClick = { viewModel.forgot(email) },
    ) { Text("Прислать код") }
    TextButton(onClick = { viewModel.switchMode(AuthMode.Login) }) { Text("Назад ко входу") }
}

@Composable
private fun ResetForm(state: AuthUiState, viewModel: AuthViewModel) {
    var code by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    Text("Новый пароль", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
    Text(
        "Код отправлен на ${state.pendingEmail}",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Center,
    )
    OutlinedTextField(
        value = code,
        onValueChange = { code = it },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        label = { Text("Код из письма") },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
    )
    PasswordField(password, "Новый пароль (от 8 символов)") { password = it }
    Button(
        modifier = Modifier.fillMaxWidth(),
        enabled = !state.isLoading,
        onClick = { viewModel.reset(code, password) },
    ) { Text("Сохранить пароль") }
    TextButton(onClick = { viewModel.switchMode(AuthMode.Login) }) { Text("Назад ко входу") }
}

@Composable
private fun EmailField(value: String, onValueChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        label = { Text("E-mail") },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
    )
}

@Composable
private fun PasswordField(value: String, label: String, onValueChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        label = { Text(label) },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
    )
}
