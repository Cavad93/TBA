package com.homevisit.location.domain

/** Аккаунт пользователя, как его отдаёт сервер (`/api/auth/*`). */
data class AuthUser(
    val id: Int,
    val email: String,
    val nickname: String,
    val emailVerified: Boolean,
    val orderSourceLabel: String,
    val occupation: String?,
)

/**
 * Результат вызова auth-эндпоинта. `ok` — успех; `message` — текст для показа
 * пользователю (сообщение сервера или причина ошибки). Для входа заполняются
 * `token` и `user`.
 */
data class AuthOutcome(
    val ok: Boolean,
    val message: String,
    val token: String? = null,
    val user: AuthUser? = null,
)
