package com.homevisit.location.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.homevisit.location.data.HomeVisitRepository
import com.homevisit.location.domain.AuthUser
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class AuthMode { Login, Register, Verify, Forgot, Reset }

data class AuthUiState(
    val mode: AuthMode = AuthMode.Login,
    val isLoading: Boolean = false,
    val message: String = "",
    /** E-mail, ожидающий подтверждения кода (Verify) или сброса пароля (Reset). */
    val pendingEmail: String = "",
)

/**
 * Экран входа/регистрации. Держит серверный URL внутри (api.vizitorkrut.ru), а
 * наружу отдаёт токен сессии через onAuthenticated — его MainActivity сохраняет
 * в prefs как Bearer для всех запросов.
 */
class AuthViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = HomeVisitRepository.create(application)
    var serverUrl: String = ""

    // Пароль из формы регистрации, чтобы автоматически войти после подтверждения кода.
    // Не персистится и не попадает в UI-состояние.
    private var pendingPassword: String = ""

    private val _state = MutableStateFlow(AuthUiState())
    val state: StateFlow<AuthUiState> = _state

    fun switchMode(mode: AuthMode) {
        _state.update { it.copy(mode = mode, message = "") }
    }

    fun register(email: String, password: String, nickname: String, occupation: String?) {
        if (!validCredentials(email, password) || nickname.isBlank()) {
            _state.update { it.copy(message = "Заполните e-mail, ник и пароль (от 8 символов)") }
            return
        }
        launchGuard {
            val result = repository.register(serverUrl, email, password, nickname, occupation)
            if (result.ok) {
                pendingPassword = password
                _state.update { it.copy(mode = AuthMode.Verify, pendingEmail = email.trim(), message = result.message) }
            } else {
                _state.update { it.copy(message = result.message) }
            }
        }
    }

    fun verify(verificationCode: String, onAuthenticated: (String, AuthUser?) -> Unit) {
        val email = _state.value.pendingEmail
        if (verificationCode.isBlank()) {
            _state.update { it.copy(message = "Введите код из письма") }
            return
        }
        launchGuard {
            val verified = repository.verifyEmail(serverUrl, email, verificationCode)
            if (!verified.ok) {
                _state.update { it.copy(message = verified.message) }
                return@launchGuard
            }
            // Код верный — сразу входим с паролем из регистрации.
            if (pendingPassword.isNotBlank()) {
                val login = repository.login(serverUrl, email, pendingPassword)
                pendingPassword = ""
                if (login.ok && login.token != null) {
                    onAuthenticated(login.token, login.user)
                    return@launchGuard
                }
            }
            _state.update { it.copy(mode = AuthMode.Login, message = "E-mail подтверждён. Войдите.") }
        }
    }

    fun resend() {
        val email = _state.value.pendingEmail
        launchGuard {
            _state.update { it.copy(message = repository.resendCode(serverUrl, email).message) }
        }
    }

    fun login(email: String, password: String, onAuthenticated: (String, AuthUser?) -> Unit) {
        if (email.isBlank() || password.isBlank()) {
            _state.update { it.copy(message = "Введите e-mail и пароль") }
            return
        }
        launchGuard {
            val result = repository.login(serverUrl, email, password)
            if (result.ok && result.token != null) {
                onAuthenticated(result.token, result.user)
            } else if (result.message.contains("Подтвердите", ignoreCase = true)) {
                // Незавершённая регистрация — уводим на ввод кода и запоминаем пароль,
                // чтобы после подтверждения войти автоматически.
                pendingPassword = password
                _state.update { it.copy(mode = AuthMode.Verify, pendingEmail = email.trim(), message = result.message) }
            } else {
                _state.update { it.copy(message = result.message) }
            }
        }
    }

    fun forgot(email: String) {
        if (email.isBlank()) {
            _state.update { it.copy(message = "Введите e-mail") }
            return
        }
        launchGuard {
            val result = repository.forgotPassword(serverUrl, email)
            _state.update {
                it.copy(
                    mode = if (result.ok) AuthMode.Reset else it.mode,
                    pendingEmail = if (result.ok) email.trim() else it.pendingEmail,
                    message = result.message,
                )
            }
        }
    }

    fun reset(verificationCode: String, newPassword: String) {
        val email = _state.value.pendingEmail
        if (verificationCode.isBlank() || newPassword.length < 8) {
            _state.update { it.copy(message = "Введите код и новый пароль (от 8 символов)") }
            return
        }
        launchGuard {
            val result = repository.resetPassword(serverUrl, email, verificationCode, newPassword)
            if (result.ok) {
                _state.update { it.copy(mode = AuthMode.Login, message = "Пароль изменён. Войдите с новым паролем.") }
            } else {
                _state.update { it.copy(message = result.message) }
            }
        }
    }

    private fun validCredentials(email: String, password: String): Boolean {
        return email.contains("@") && password.length >= 8
    }

    private fun launchGuard(block: suspend () -> Unit) {
        if (_state.value.isLoading) return
        _state.update { it.copy(isLoading = true, message = "") }
        viewModelScope.launch {
            try {
                block()
            } finally {
                _state.update { it.copy(isLoading = false) }
            }
        }
    }
}
