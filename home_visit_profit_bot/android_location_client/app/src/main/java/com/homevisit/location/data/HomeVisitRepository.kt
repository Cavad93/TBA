package com.homevisit.location.data

import android.content.Context
import androidx.room.withTransaction
import com.homevisit.location.data.local.ExpenseEntity
import com.homevisit.location.data.local.HomeVisitDatabase
import com.homevisit.location.data.local.OfficeEntryEntity
import com.homevisit.location.data.local.SettingEntity
import com.homevisit.location.data.local.SyncQueueEntity
import com.homevisit.location.data.local.SyncStatus
import com.homevisit.location.data.local.TelemedEntryEntity
import com.homevisit.location.data.local.VisitEntity
import com.homevisit.location.data.local.WorkDayEntity
import com.homevisit.location.domain.AppSettingsSnapshot
import com.homevisit.location.domain.AuthOutcome
import com.homevisit.location.domain.AuthUser
import com.homevisit.location.domain.CandidateEstimate
import com.homevisit.location.domain.CandidateRequestResult
import com.homevisit.location.domain.CbiInfo
import com.homevisit.location.domain.ClinicOptions
import com.homevisit.location.domain.ClinicReportRow
import com.homevisit.location.domain.EndDayDetails
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.FatigueCorrelationCell
import com.homevisit.location.domain.FatigueCorrelationReport
import com.homevisit.location.domain.FatigueFeedback
import com.homevisit.location.domain.FatigueFeedbackResult
import com.homevisit.location.domain.FatigueSnapshot
import com.homevisit.location.domain.FatigueSummary
import com.homevisit.location.domain.FatigueTrendPoint
import com.homevisit.location.domain.FatigueTrendReport
import com.homevisit.location.domain.GpsDayEstimate
import com.homevisit.location.domain.GpsVisitHint
import com.homevisit.location.domain.ReportPeriod
import com.homevisit.location.domain.ReportSnapshot
import com.homevisit.location.domain.ReportSummary
import com.homevisit.location.domain.ServerRouteLeg
import com.homevisit.location.domain.ServerRouteSnapshot
import com.homevisit.location.domain.SettingField
import com.homevisit.location.domain.SettingType
import com.homevisit.location.domain.SettingsSection
import com.homevisit.location.domain.StopLabel
import com.homevisit.location.domain.SyncConflict
import com.homevisit.location.domain.SyncQueueStats
import com.homevisit.location.domain.VisitStatus
import com.homevisit.location.domain.WorkDayStatus
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

class HomeVisitRepository private constructor(
    private val database: HomeVisitDatabase,
) {
    private val dao = database.homeVisitDao()

    fun observeLatestWorkDay(): Flow<WorkDayEntity?> = dao.observeLatestWorkDay()

    fun observeVisits(workDayId: String): Flow<List<VisitEntity>> = dao.observeVisits(workDayId)

    fun observeOfficeEntries(workDayId: String): Flow<List<OfficeEntryEntity>> = dao.observeOfficeEntries(workDayId)

    fun observeTelemedEntries(workDayId: String): Flow<List<TelemedEntryEntity>> = dao.observeTelemedEntries(workDayId)

    fun observeExpenses(workDayId: String): Flow<List<ExpenseEntity>> = dao.observeExpenses(workDayId)

    fun observeSyncQueueStats(): Flow<SyncQueueStats> = combine(
        dao.observeSyncCount(SyncStatus.Pending.value),
        dao.observeSyncCount(SyncStatus.Sent.value),
        dao.observeSyncCount(SyncStatus.Failed.value),
    ) { pending, sent, failed ->
        SyncQueueStats(
            pendingCount = pending,
            sentCount = sent,
            failedCount = failed,
        )
    }

    suspend fun startDay(
        startAddress: String? = null,
        finishAddress: String? = null,
        startOdometer: Double = 0.0,
        sleepHours: Double = 0.0,
        sleepQuality: Double = 0.0,
        breakHoursBefore: Double = 0.0,
    ): String {
        val now = now()
        return database.withTransaction {
            val activeDay = dao.getLatestWorkDayByStatus(WorkDayStatus.Active)
            if (activeDay != null) {
                return@withTransaction activeDay.id
            }

            val day = WorkDayEntity(
                id = id(),
                startEpochMillis = now,
                endEpochMillis = null,
                status = WorkDayStatus.Active,
                startAddress = startAddress?.trim()?.ifEmpty { null },
                finishAddress = finishAddress?.trim()?.ifEmpty { null },
                startOdometer = startOdometer.coerceAtLeast(0.0),
                endOdometer = null,
                sleepHours = sleepHours.coerceAtLeast(0.0),
                sleepQuality = sleepQuality.coerceIn(0.0, 5.0),
                breakHoursBefore = breakHoursBefore.coerceAtLeast(0.0),
                createdAtEpochMillis = now,
                updatedAtEpochMillis = now,
            )
            dao.saveWorkDay(day)
            dao.enqueueSync(sync("day_started", "work_day", day.id, now, workDayPayload(day)))
            day.id
        }
    }

    suspend fun endDay(workDayId: String? = null, endOdometer: Double? = null, details: EndDayDetails? = null) {
        val now = now()
        database.withTransaction {
            val day = workDayId?.let { dao.getWorkDay(it) } ?: dao.getLatestWorkDayByStatus(WorkDayStatus.Active)
            if (day != null) {
                val closed = day.copy(
                    status = WorkDayStatus.Closed,
                    endEpochMillis = now,
                    endOdometer = details?.endOdometer?.coerceAtLeast(0.0) ?: endOdometer?.coerceAtLeast(0.0),
                    updatedAtEpochMillis = now,
                )
                dao.saveWorkDay(closed)
                dao.enqueueSync(sync("day_closed", "work_day", closed.id, now, endDayPayload(closed, details)))
            }
        }
    }

    suspend fun addVisit(
        workDayId: String,
        address: String,
        income: Double,
        clinic: String,
        status: VisitStatus = VisitStatus.Accepted,
    ): String {
        val now = now()
        val visit = VisitEntity(
            id = id(),
            workDayId = workDayId,
            address = address.trim(),
            income = income,
            clinic = clinic,
            status = status,
            estimatedDriveMinutes = null,
            actualDriveMinutes = null,
            onSiteMinutes = null,
            createdAtEpochMillis = now,
            updatedAtEpochMillis = now,
        )
        dao.saveVisit(visit)
        dao.enqueueSync(sync("visit_saved", "visit", visit.id, now, visitPayload(visit)))
        return visit.id
    }

    suspend fun addOfficeEntry(
        workDayId: String,
        address: String,
        minutes: Double,
        income: Double,
        clinic: String,
    ): String {
        val now = now()
        val office = OfficeEntryEntity(
            id = id(),
            workDayId = workDayId,
            address = address.trim(),
            minutes = minutes,
            income = income,
            clinic = clinic,
            createdAtEpochMillis = now,
            updatedAtEpochMillis = now,
        )
        dao.saveOfficeEntry(office)
        dao.enqueueSync(sync("office_saved", "office_entry", office.id, now, officePayload(office)))
        return office.id
    }

    suspend fun addTelemedEntry(
        workDayId: String,
        minutes: Double,
        income: Double,
        clinic: String,
    ): String {
        val now = now()
        val telemed = TelemedEntryEntity(
            id = id(),
            workDayId = workDayId,
            minutes = minutes,
            income = income,
            clinic = clinic,
            createdAtEpochMillis = now,
            updatedAtEpochMillis = now,
        )
        dao.saveTelemedEntry(telemed)
        dao.enqueueSync(sync("telemed_saved", "telemed_entry", telemed.id, now, telemedPayload(telemed)))
        return telemed.id
    }

    suspend fun addExpense(
        workDayId: String,
        category: ExpenseCategory,
        amount: Double,
        comment: String = "",
    ): String {
        val now = now()
        val expense = ExpenseEntity(
            id = id(),
            workDayId = workDayId,
            category = category,
            amount = amount,
            comment = comment.trim(),
            createdAtEpochMillis = now,
            updatedAtEpochMillis = now,
        )
        dao.saveExpense(expense)
        dao.enqueueSync(sync("expense_saved", "expense", expense.id, now, expensePayload(expense)))
        return expense.id
    }

    suspend fun saveSetting(key: String, value: String) {
        val now = now()
        dao.saveSetting(
            SettingEntity(
                key = key,
                value = value,
                updatedAtEpochMillis = now,
            ),
        )
    }

    suspend fun syncPending(serverUrl: String, apiKey: String): Int = withContext(Dispatchers.IO) {
        val normalizedUrl = normalizeSyncUrl(serverUrl)
        if (normalizedUrl.isBlank() || apiKey.isBlank()) {
            return@withContext 0
        }
        var sent = 0
        dao.getSyncQueueByStatuses(listOf(SyncStatus.Pending.value, SyncStatus.Failed.value), limit = 25).forEach { item ->
            val ok = sendSyncEvent(normalizedUrl, apiKey, item)
            val nextAttempts = item.attempts + 1
            dao.updateSyncStatus(
                id = item.id,
                status = when {
                    ok -> SyncStatus.Sent.value
                    nextAttempts >= 3 -> SyncStatus.Failed.value
                    else -> SyncStatus.Pending.value
                },
                updatedAt = now(),
            )
            if (ok) {
                sent += 1
            }
        }
        sent
    }

    suspend fun exportBackupJson(): String = withContext(Dispatchers.IO) {
        JSONObject()
            .put("schema", "home_visit_android_backup_v1")
            .put("exported_at_epoch_millis", now())
            .put("work_days", JSONArray(dao.getAllWorkDays().map { backupWorkDayJson(it) }))
            .put("visits", JSONArray(dao.getAllVisits().map { backupVisitJson(it) }))
            .put("office_entries", JSONArray(dao.getAllOfficeEntries().map { backupOfficeJson(it) }))
            .put("telemed_entries", JSONArray(dao.getAllTelemedEntries().map { backupTelemedJson(it) }))
            .put("expenses", JSONArray(dao.getAllExpenses().map { backupExpenseJson(it) }))
            .put("settings", JSONArray(dao.getAllSettings().map { backupSettingJson(it) }))
            .put("sync_queue", JSONArray(dao.getAllSyncQueue().map { backupSyncQueueJson(it) }))
            .toString(2)
    }

    suspend fun importBackupJson(backupJson: String): Int = withContext(Dispatchers.IO) {
        val root = JSONObject(backupJson)
        require(root.optString("schema") == "home_visit_android_backup_v1") { "Неверный формат резервной копии" }
        var imported = 0
        database.withTransaction {
            root.optJSONArray("work_days")?.forEachObject { item ->
                dao.saveWorkDay(
                    WorkDayEntity(
                        id = item.optString("id"),
                        startEpochMillis = item.optLong("start_epoch_millis", 0),
                        endEpochMillis = item.nullableLong("end_epoch_millis"),
                        status = enumValueOrDefault(item.optString("status"), WorkDayStatus.Active),
                        startAddress = item.nullableString("start_address"),
                        finishAddress = item.nullableString("finish_address"),
                        startOdometer = item.optDouble("start_odometer", 0.0),
                        endOdometer = item.nullableDouble("end_odometer"),
                        sleepHours = item.optDouble("sleep_hours", 0.0),
                        sleepQuality = item.optDouble("sleep_quality", 0.0),
                        breakHoursBefore = item.optDouble("break_hours_before", 0.0),
                        createdAtEpochMillis = item.optLong("created_at_epoch_millis", now()),
                        updatedAtEpochMillis = item.optLong("updated_at_epoch_millis", now()),
                    )
                )
                imported += 1
            }
            root.optJSONArray("visits")?.forEachObject { item ->
                dao.saveVisit(
                    VisitEntity(
                        id = item.optString("id"),
                        workDayId = item.optString("work_day_id"),
                        address = item.optString("address"),
                        income = item.optDouble("income", 0.0),
                        clinic = item.optString("clinic"),
                        status = enumValueOrDefault(item.optString("status"), VisitStatus.Accepted),
                        estimatedDriveMinutes = item.nullableDouble("estimated_drive_minutes"),
                        actualDriveMinutes = item.nullableDouble("actual_drive_minutes"),
                        onSiteMinutes = item.nullableDouble("on_site_minutes"),
                        createdAtEpochMillis = item.optLong("created_at_epoch_millis", now()),
                        updatedAtEpochMillis = item.optLong("updated_at_epoch_millis", now()),
                    )
                )
                imported += 1
            }
            root.optJSONArray("office_entries")?.forEachObject { item ->
                dao.saveOfficeEntry(
                    OfficeEntryEntity(
                        id = item.optString("id"),
                        workDayId = item.optString("work_day_id"),
                        address = item.optString("address"),
                        minutes = item.optDouble("minutes", 0.0),
                        income = item.optDouble("income", 0.0),
                        clinic = item.optString("clinic"),
                        createdAtEpochMillis = item.optLong("created_at_epoch_millis", now()),
                        updatedAtEpochMillis = item.optLong("updated_at_epoch_millis", now()),
                    )
                )
                imported += 1
            }
            root.optJSONArray("telemed_entries")?.forEachObject { item ->
                dao.saveTelemedEntry(
                    TelemedEntryEntity(
                        id = item.optString("id"),
                        workDayId = item.optString("work_day_id"),
                        minutes = item.optDouble("minutes", 0.0),
                        income = item.optDouble("income", 0.0),
                        clinic = item.optString("clinic"),
                        createdAtEpochMillis = item.optLong("created_at_epoch_millis", now()),
                        updatedAtEpochMillis = item.optLong("updated_at_epoch_millis", now()),
                    )
                )
                imported += 1
            }
            root.optJSONArray("expenses")?.forEachObject { item ->
                dao.saveExpense(
                    ExpenseEntity(
                        id = item.optString("id"),
                        workDayId = item.optString("work_day_id"),
                        category = expenseCategoryFromTitle(item.optString("category")),
                        amount = item.optDouble("amount", 0.0),
                        comment = item.optString("comment"),
                        createdAtEpochMillis = item.optLong("created_at_epoch_millis", now()),
                        updatedAtEpochMillis = item.optLong("updated_at_epoch_millis", now()),
                    )
                )
                imported += 1
            }
            root.optJSONArray("settings")?.forEachObject { item ->
                dao.saveSetting(
                    SettingEntity(
                        key = item.optString("key"),
                        value = item.optString("value"),
                        updatedAtEpochMillis = item.optLong("updated_at_epoch_millis", now()),
                    )
                )
                imported += 1
            }
            root.optJSONArray("sync_queue")?.forEachObject { item ->
                dao.enqueueSync(
                    SyncQueueEntity(
                        id = item.optString("id"),
                        eventType = item.optString("event_type"),
                        entityType = item.optString("entity_type"),
                        entityId = item.optString("entity_id"),
                        payloadJson = item.optJSONObject("payload")?.toString() ?: "{}",
                        status = item.optString("status", SyncStatus.Pending.value),
                        attempts = item.optInt("attempts", 0),
                        createdAtEpochMillis = item.optLong("created_at_epoch_millis", now()),
                        updatedAtEpochMillis = item.optLong("updated_at_epoch_millis", now()),
                    )
                )
                imported += 1
            }
        }
        imported
    }

    suspend fun checkConnection(serverUrl: String, apiKey: String): String = withContext(Dispatchers.IO) {
        if (serverUrl.isBlank() || apiKey.isBlank()) {
            return@withContext "Заполните URL сервера и API ключ"
        }
        var connection: HttpURLConnection? = null
        try {
            connection = (URL(normalizeApiUrl(serverUrl, "/api/day/active")).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 10_000
                readTimeout = 10_000
                setRequestProperty("Authorization", "Bearer $apiKey")
            }
            when (val code = connection.responseCode) {
                in 200..299 -> "Связь есть: сервер отвечает и ключ принят"
                401, 403 -> "Сервер отвечает, но API ключ неверный"
                else -> "Сервер вернул код $code"
            }
        } catch (_: Exception) {
            "Сервер недоступен по этому URL"
        } finally {
            connection?.disconnect()
        }
    }

    // ---- Аккаунты (регистрация/вход/сессии) ----

    suspend fun register(
        serverUrl: String,
        email: String,
        password: String,
        nickname: String,
        occupation: String? = null,
    ): AuthOutcome = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("email", email.trim())
            .put("password", password)
            .put("nickname", nickname.trim())
        if (!occupation.isNullOrBlank()) {
            payload.put("occupation", occupation.trim())
        }
        val (code, body) = authPost(normalizeApiUrl(serverUrl, "/api/auth/register"), payload)
        authOutcome(code, body, "Код подтверждения отправлен на почту")
    }

    suspend fun verifyEmail(serverUrl: String, email: String, verificationCode: String): AuthOutcome =
        withContext(Dispatchers.IO) {
            val payload = JSONObject().put("email", email.trim()).put("code", verificationCode.trim())
            val (code, body) = authPost(normalizeApiUrl(serverUrl, "/api/auth/verify-email"), payload)
            authOutcome(code, body, "E-mail подтверждён")
        }

    suspend fun resendCode(serverUrl: String, email: String): AuthOutcome = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("email", email.trim())
        val (code, body) = authPost(normalizeApiUrl(serverUrl, "/api/auth/resend-code"), payload)
        authOutcome(code, body, "Код отправлен повторно")
    }

    suspend fun login(serverUrl: String, email: String, password: String): AuthOutcome =
        withContext(Dispatchers.IO) {
            val payload = JSONObject().put("email", email.trim()).put("password", password)
            val (code, body) = authPost(normalizeApiUrl(serverUrl, "/api/auth/login"), payload)
            if (code == HTTP_NO_CONNECTION || body == null) {
                return@withContext AuthOutcome(false, NO_CONNECTION_MESSAGE)
            }
            val error = body.optString("error").ifBlank { null }
            if (code in 200..299 && error == null) {
                val token = body.optString("token").ifBlank { null }
                    ?: return@withContext AuthOutcome(false, "Сервер не выдал токен сессии")
                return@withContext AuthOutcome(true, "Вход выполнен", token, parseAuthUser(body.optJSONObject("user")))
            }
            AuthOutcome(false, error ?: "Не удалось войти (код $code)")
        }

    suspend fun forgotPassword(serverUrl: String, email: String): AuthOutcome = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("email", email.trim())
        val (code, body) = authPost(normalizeApiUrl(serverUrl, "/api/auth/password/forgot"), payload)
        authOutcome(code, body, "Если аккаунт существует, код для сброса отправлен")
    }

    suspend fun resetPassword(serverUrl: String, email: String, verificationCode: String, newPassword: String): AuthOutcome =
        withContext(Dispatchers.IO) {
            val payload = JSONObject()
                .put("email", email.trim())
                .put("code", verificationCode.trim())
                .put("password", newPassword)
            val (code, body) = authPost(normalizeApiUrl(serverUrl, "/api/auth/password/reset"), payload)
            authOutcome(code, body, "Пароль изменён")
        }

    suspend fun fetchMe(serverUrl: String, token: String): AuthUser? = withContext(Dispatchers.IO) {
        val response = getJson(normalizeApiUrl(serverUrl, "/api/auth/me"), token) ?: return@withContext null
        if (!response.optBoolean("ok", false)) return@withContext null
        parseAuthUser(response.optJSONObject("user"))
    }

    suspend fun logout(serverUrl: String, token: String): Boolean = withContext(Dispatchers.IO) {
        if (token.isBlank()) return@withContext true
        authPost(normalizeApiUrl(serverUrl, "/api/auth/logout"), JSONObject(), token).first in 200..299
    }

    suspend fun deleteAccount(serverUrl: String, token: String): Boolean = withContext(Dispatchers.IO) {
        if (token.isBlank()) return@withContext false
        var connection: HttpURLConnection? = null
        try {
            connection = (URL(normalizeApiUrl(serverUrl, "/api/auth/account")).openConnection() as HttpURLConnection).apply {
                requestMethod = "DELETE"
                connectTimeout = 10_000
                readTimeout = 20_000
                setRequestProperty("Authorization", "Bearer $token")
            }
            connection.responseCode in 200..299
        } catch (_: Exception) {
            false
        } finally {
            connection?.disconnect()
        }
    }

    /** POST на auth-эндпоинт. Возвращает (HTTP-код, тело JSON) — тело читается и при ошибке. */
    private fun authPost(url: String, payload: JSONObject, token: String? = null): Pair<Int, JSONObject?> {
        if (url.isBlank()) return HTTP_NO_CONNECTION to null
        var connection: HttpURLConnection? = null
        return try {
            val body = payload.toString().toByteArray(StandardCharsets.UTF_8)
            connection = (URL(url).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 10_000
                readTimeout = 20_000
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                if (token != null) {
                    setRequestProperty("Authorization", "Bearer $token")
                }
            }
            connection.outputStream.use { it.write(body) }
            val responseCode = connection.responseCode
            val stream = if (responseCode in 200..399) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(StandardCharsets.UTF_8)?.use { it.readText() }.orEmpty()
            responseCode to (if (text.isBlank()) null else JSONObject(text))
        } catch (_: Exception) {
            HTTP_NO_CONNECTION to null
        } finally {
            connection?.disconnect()
        }
    }

    private fun authOutcome(code: Int, body: JSONObject?, successMessage: String): AuthOutcome {
        if (code == HTTP_NO_CONNECTION || body == null) {
            return AuthOutcome(false, NO_CONNECTION_MESSAGE)
        }
        val error = body.optString("error").ifBlank { null }
        if (code in 200..299 && error == null) {
            return AuthOutcome(true, body.optString("message").ifBlank { successMessage })
        }
        return AuthOutcome(false, error ?: "Ошибка сервера (код $code)")
    }

    private fun parseAuthUser(user: JSONObject?): AuthUser? {
        if (user == null) return null
        return AuthUser(
            id = user.optInt("id"),
            email = user.optString("email"),
            nickname = user.optString("nickname"),
            emailVerified = user.optBoolean("email_verified", false),
            orderSourceLabel = user.optString("order_source_label").ifBlank { "Компания" },
            occupation = user.optString("occupation").ifBlank { null },
        )
    }

    suspend fun fetchSyncConflicts(serverUrl: String, apiKey: String): List<SyncConflict>? = withContext(Dispatchers.IO) {
        val response = getJson(normalizeApiUrl(serverUrl, "/api/sync/conflicts?limit=10"), apiKey) ?: return@withContext null
        if (!response.optBoolean("ok", false)) {
            return@withContext null
        }
        val result = mutableListOf<SyncConflict>()
        val array = response.optJSONArray("conflicts") ?: JSONArray()
        for (index in 0 until array.length()) {
            val item = array.optJSONObject(index) ?: continue
            result.add(
                SyncConflict(
                    id = item.optInt("id", 0),
                    clientEventId = item.optString("client_event_id").ifBlank { null },
                    eventType = item.optString("event_type"),
                    entityType = item.optString("entity_type"),
                    clientEntityId = item.optString("client_entity_id"),
                    serverEntityId = item.optInt("server_entity_id", 0).takeIf { it > 0 },
                    conflictType = item.optString("conflict_type"),
                    details = item.optString("details").ifBlank { null },
                    createdAt = item.optString("created_at"),
                )
            )
        }
        result
    }

    suspend fun calculateVisitCandidate(
        serverUrl: String,
        apiKey: String,
        address: String,
        income: Double,
        clinic: String,
        routeKm: Double? = null,
        routeMinutes: Double? = null,
    ): CandidateRequestResult = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("address", address.trim())
            .put("income", income)
            .put("clinic", clinic)
        if (routeKm != null && routeMinutes != null) {
            payload.put("route_km", routeKm)
            payload.put("route_minutes", routeMinutes)
        }
        val response = postJson(normalizeApiUrl(serverUrl, "/api/visits/candidate"), apiKey, payload)
            ?: return@withContext CandidateRequestResult(ok = false, reason = "network_error")
        parseCandidateResult(response)
    }

    suspend fun acceptCandidate(
        serverUrl: String,
        apiKey: String,
        workDayId: String,
        estimate: CandidateEstimate,
    ): Boolean = withContext(Dispatchers.IO) {
        val response = postJson(normalizeApiUrl(serverUrl, "/api/visits/${estimate.visitId}/accept"), apiKey, JSONObject())
            ?: return@withContext false
        if (!response.optBoolean("ok", false)) {
            return@withContext false
        }
        saveServerVisit(workDayId, estimate, VisitStatus.Accepted)
        true
    }

    suspend fun rejectCandidate(serverUrl: String, apiKey: String, visitId: Int): Boolean = withContext(Dispatchers.IO) {
        val response = postJson(normalizeApiUrl(serverUrl, "/api/visits/$visitId/reject"), apiKey, JSONObject())
            ?: return@withContext false
        response.optBoolean("ok", false)
    }

    suspend fun completeVisit(serverUrl: String, apiKey: String, visitId: Int): Boolean = withContext(Dispatchers.IO) {
        val response = postJson(normalizeApiUrl(serverUrl, "/api/visits/$visitId/complete"), apiKey, JSONObject())
            ?: return@withContext false
        response.optBoolean("ok", false)
    }

    suspend fun cancelVisit(serverUrl: String, apiKey: String, visitId: Int): Boolean = withContext(Dispatchers.IO) {
        val response = postJson(normalizeApiUrl(serverUrl, "/api/visits/$visitId/cancel"), apiKey, JSONObject())
            ?: return@withContext false
        response.optBoolean("ok", false)
    }

    suspend fun updateDayFinish(serverUrl: String, apiKey: String, address: String): String? = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("finish_address", address)
        val response = postJson(normalizeApiUrl(serverUrl, "/api/day/finish"), apiKey, payload) ?: return@withContext null
        response.optString("reason", if (response.optBoolean("ok", false)) "finish_updated" else "error")
    }

    suspend fun fetchActiveRoute(serverUrl: String, apiKey: String): ServerRouteSnapshot? = withContext(Dispatchers.IO) {
        val response = cachedGetJson(normalizeApiUrl(serverUrl, "/api/route/active"), apiKey, "cache_route_active")
            ?: return@withContext null
        parseServerRoute(response.optJSONObject("route"))?.copy(fromCache = response.optBoolean("_from_cache", false))
    }

    suspend fun fetchGpsDayEstimate(serverUrl: String, apiKey: String): GpsDayEstimate? = withContext(Dispatchers.IO) {
        val response = getJson(normalizeApiUrl(serverUrl, "/api/day/gps-estimate"), apiKey) ?: return@withContext null
        if (!response.optBoolean("ok", false)) {
            return@withContext null
        }
        parseGpsDayEstimate(response.optJSONObject("estimate"))
    }

    suspend fun fetchCurrentGpsHint(serverUrl: String, apiKey: String): GpsVisitHint? = withContext(Dispatchers.IO) {
        val response = getJson(normalizeApiUrl(serverUrl, "/api/visits/current-gps"), apiKey) ?: return@withContext null
        parseGpsVisitHint(response.optJSONObject("hint"))
    }

    suspend fun fetchActiveReport(serverUrl: String, apiKey: String, clinic: String? = null): ReportSnapshot? = withContext(Dispatchers.IO) {
        val path = "/api/reports/summary" + clinicQuery(clinic, first = true)
        val key = "cache_report_active" + (clinic?.let { "_$it" } ?: "")
        val response = cachedGetJson(normalizeApiUrl(serverUrl, path), apiKey, key) ?: return@withContext null
        parseReportSnapshot(response)
    }

    suspend fun fetchStatsReport(serverUrl: String, apiKey: String, period: ReportPeriod, clinic: String? = null): ReportSnapshot? = withContext(Dispatchers.IO) {
        val path = "/api/reports/stats?period=${period.apiValue}" + clinicQuery(clinic, first = false)
        val key = "cache_report_stats_${period.apiValue}" + (clinic?.let { "_$it" } ?: "")
        val response = cachedGetJson(normalizeApiUrl(serverUrl, path), apiKey, key) ?: return@withContext null
        parseReportSnapshot(response)
    }

    private fun clinicQuery(clinic: String?, first: Boolean): String {
        if (clinic.isNullOrBlank()) return ""
        val encoded = java.net.URLEncoder.encode(clinic, "UTF-8")
        return if (first) "?clinic=$encoded" else "&clinic=$encoded"
    }

    suspend fun fetchFatigueSummary(serverUrl: String, apiKey: String): FatigueSnapshot? = withContext(Dispatchers.IO) {
        val response = cachedGetJson(normalizeApiUrl(serverUrl, "/api/fatigue/summary"), apiKey, "cache_fatigue_summary")
            ?: return@withContext null
        parseFatigueSnapshot(response)
    }

    suspend fun fetchAppSettings(serverUrl: String, apiKey: String): AppSettingsSnapshot? = withContext(Dispatchers.IO) {
        val response = getJson(normalizeApiUrl(serverUrl, "/api/settings"), apiKey)
        if (response == null || !response.optBoolean("ok", false)) {
            return@withContext loadCachedAppSettings()
        }
        val snapshot = parseAppSettings(response) ?: return@withContext loadCachedAppSettings()
        dao.saveSetting(SettingEntity(key = CACHE_KEY_APP_SETTINGS, value = response.toString(), updatedAtEpochMillis = now()))
        cacheClinics(extractClinics(snapshot))
        snapshot
    }

    suspend fun fetchClinics(serverUrl: String, apiKey: String): ClinicOptions = withContext(Dispatchers.IO) {
        val snapshot = fetchAppSettings(serverUrl, apiKey) ?: return@withContext loadCachedClinics()
        val options = extractClinics(snapshot)
        cacheClinics(options)
        options
    }

    suspend fun loadCachedClinics(): ClinicOptions = withContext(Dispatchers.IO) {
        ClinicOptions(
            all = parseCachedList(dao.getSetting(CACHE_KEY_CLINICS)?.value),
            telemed = parseCachedList(dao.getSetting(CACHE_KEY_TELEMED_CLINICS)?.value),
        )
    }

    private suspend fun cacheClinics(options: ClinicOptions) {
        val now = now()
        dao.saveSetting(SettingEntity(key = CACHE_KEY_CLINICS, value = options.all.joinToString(", "), updatedAtEpochMillis = now))
        dao.saveSetting(SettingEntity(key = CACHE_KEY_TELEMED_CLINICS, value = options.telemed.joinToString(", "), updatedAtEpochMillis = now))
    }

    private fun extractClinics(snapshot: AppSettingsSnapshot): ClinicOptions {
        var all = emptyList<String>()
        var telemed = emptyList<String>()
        snapshot.sections.forEach { section ->
            section.fields.forEach { field ->
                when (field.key) {
                    "clinics" -> all = field.listValue
                    "telemed_clinics" -> telemed = field.listValue
                }
            }
        }
        return ClinicOptions(all = all, telemed = telemed)
    }

    private fun parseCachedList(value: String?): List<String> {
        if (value.isNullOrBlank()) return emptyList()
        return value.split(",").map { it.trim() }.filter { it.isNotEmpty() }
    }

    private suspend fun loadCachedAppSettings(): AppSettingsSnapshot? {
        val cached = dao.getSetting(CACHE_KEY_APP_SETTINGS) ?: return null
        return try {
            parseAppSettings(JSONObject(cached.value))
        } catch (_: Exception) {
            null
        }
    }

    suspend fun queueAppSettingsUpdate(values: Map<String, Any?>) = withContext(Dispatchers.IO) {
        val now = now()
        val valuesJson = JSONObject()
        values.forEach { (key, value) ->
            when (value) {
                null -> {}
                is List<*> -> valuesJson.put(key, JSONArray(value.map { it.toString() }))
                else -> valuesJson.put(key, value)
            }
        }
        val payload = JSONObject().put("values", valuesJson).toString()
        dao.enqueueSync(sync("settings_saved", "settings", "settings", now, payload))
    }

    private fun parseAppSettings(response: JSONObject): AppSettingsSnapshot? {
        val sectionsJson = response.optJSONArray("sections") ?: return null
        val sections = mutableListOf<SettingsSection>()
        for (i in 0 until sectionsJson.length()) {
            val sectionJson = sectionsJson.optJSONObject(i) ?: continue
            val fieldsJson = sectionJson.optJSONArray("fields") ?: JSONArray()
            val fields = mutableListOf<SettingField>()
            for (j in 0 until fieldsJson.length()) {
                val fieldJson = fieldsJson.optJSONObject(j) ?: continue
                val type = SettingType.fromWire(fieldJson.optString("type"))
                fields.add(
                    SettingField(
                        key = fieldJson.optString("key"),
                        label = fieldJson.optString("label"),
                        type = type,
                        textValue = when (type) {
                            SettingType.Number -> formatSettingNumber(fieldJson.optDouble("value", 0.0))
                            SettingType.Text -> fieldJson.optString("value")
                            else -> ""
                        },
                        boolValue = type == SettingType.Bool && fieldJson.optBoolean("value", false),
                        listValue = if (type == SettingType.ListValue) {
                            val arr = fieldJson.optJSONArray("value") ?: JSONArray()
                            (0 until arr.length()).map { arr.optString(it) }.filter { it.isNotBlank() }
                        } else {
                            emptyList()
                        },
                    )
                )
            }
            sections.add(
                SettingsSection(
                    key = sectionJson.optString("key"),
                    title = sectionJson.optString("title"),
                    fields = fields,
                )
            )
        }
        return AppSettingsSnapshot(sections = sections)
    }

    private fun formatSettingNumber(value: Double): String {
        return if (value == Math.floor(value) && !value.isInfinite()) {
            value.toLong().toString()
        } else {
            value.toString()
        }
    }

    suspend fun fetchFatigueCorrelation(serverUrl: String, apiKey: String, days: Int): FatigueCorrelationReport? = withContext(Dispatchers.IO) {
        val response = cachedGetJson(normalizeApiUrl(serverUrl, "/api/fatigue/corr?days=$days"), apiKey, "cache_fatigue_corr_$days")
            ?: return@withContext null
        parseFatigueCorrelationReport(response)
    }

    suspend fun fetchFatigueTrend(serverUrl: String, apiKey: String, days: Int): FatigueTrendReport? = withContext(Dispatchers.IO) {
        val response = cachedGetJson(normalizeApiUrl(serverUrl, "/api/fatigue/trend?days=$days"), apiKey, "cache_fatigue_trend_$days")
            ?: return@withContext null
        val fromCache = response.optBoolean("_from_cache", false)
        val pointsJson = response.optJSONArray("points")
            ?: return@withContext FatigueTrendReport(response.optInt("days", days), emptyList(), fromCache)
        val points = (0 until pointsJson.length()).mapNotNull { index ->
            val obj = pointsJson.optJSONObject(index) ?: return@mapNotNull null
            FatigueTrendPoint(
                date = obj.optString("date"),
                score = obj.optDouble("score", 0.0),
                weeklyAverage = obj.optDouble("weekly_average", 0.0),
                recoveryDebt = obj.optDouble("recovery_debt", 0.0),
            )
        }
        FatigueTrendReport(days = response.optInt("days", days), points = points, fromCache = fromCache)
    }

    suspend fun saveFatigueFeedback(
        serverUrl: String,
        apiKey: String,
        action: String,
        score: Double? = null,
        workDayId: Int? = null,
    ): FatigueFeedbackResult? = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("action", action)
        score?.let { payload.put("score", it) }
        workDayId?.let { payload.put("work_day_id", it) }
        val response = postJson(normalizeApiUrl(serverUrl, "/api/fatigue/feedback"), apiKey, payload) ?: return@withContext null
        if (!response.optBoolean("ok", false)) {
            return@withContext null
        }
        FatigueFeedbackResult(
            predictedScore = response.optDouble("predicted_score", 0.0),
            userScore = response.optDouble("user_score", 0.0),
            error = response.optDouble("error", 0.0),
            activeWeightsCount = response.optInt("active_weights_count", 0),
        )
    }

    suspend fun saveCbi(serverUrl: String, apiKey: String, answers: List<Int>): CbiInfo? = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("answers", JSONArray(answers))
        val response = postJson(normalizeApiUrl(serverUrl, "/api/fatigue/cbi"), apiKey, payload) ?: return@withContext null
        if (!response.optBoolean("ok", false)) {
            return@withContext null
        }
        parseCbiInfo(response.optJSONObject("cbi"))
    }

    suspend fun setVisitStopLabel(serverUrl: String, apiKey: String, visitId: Int, label: StopLabel): String = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("label", label.apiValue)
        val response = postJson(normalizeApiUrl(serverUrl, "/api/visits/$visitId/stop-label"), apiKey, payload)
            ?: return@withContext "Не удалось отправить уточнение остановки"
        if (response.optBoolean("ok", false)) {
            return@withContext "Остановка учтена как: ${label.title}"
        }
        when (response.optString("reason")) {
            "no_gps_stop" -> "По этому адресу ещё нет GPS-остановки"
            else -> "Не удалось сохранить уточнение остановки"
        }
    }

    suspend fun markVisitStatus(localVisitId: String, status: VisitStatus) {
        dao.updateVisitStatus(localVisitId, status, now())
    }

    suspend fun saveServerVisit(workDayId: String, estimate: CandidateEstimate, status: VisitStatus) {
        val now = now()
        dao.saveVisit(
            VisitEntity(
                id = "server-${estimate.visitId}",
                workDayId = workDayId,
                address = estimate.address,
                income = estimate.income,
                clinic = estimate.clinic,
                status = status,
                estimatedDriveMinutes = estimate.extraDriveMinutes,
                actualDriveMinutes = null,
                onSiteMinutes = null,
                createdAtEpochMillis = now,
                updatedAtEpochMillis = now,
            ),
        )
    }

    private fun sync(
        eventType: String,
        entityType: String,
        entityId: String,
        now: Long,
        payloadJson: String,
    ): SyncQueueEntity {
        return SyncQueueEntity(
            id = id(),
            eventType = eventType,
            entityType = entityType,
            entityId = entityId,
            payloadJson = payloadJson,
            status = SyncStatus.Pending.value,
            attempts = 0,
            createdAtEpochMillis = now,
            updatedAtEpochMillis = now,
        )
    }

    private fun workDayPayload(day: WorkDayEntity): String = JSONObject()
        .put("id", day.id)
        .put("start_epoch_millis", day.startEpochMillis)
        .put("end_epoch_millis", day.endEpochMillis)
        .put("status", day.status.name)
        .put("start_address", day.startAddress)
        .put("finish_address", day.finishAddress)
        .put("start_odometer", day.startOdometer)
        .put("end_odometer", day.endOdometer)
        .put("sleep_hours", day.sleepHours)
        .put("sleep_quality", day.sleepQuality)
        .put("break_hours_before", day.breakHoursBefore)
        .toString()

    private fun endDayPayload(day: WorkDayEntity, details: EndDayDetails?): String {
        val payload = JSONObject(workDayPayload(day))
        if (details == null) {
            return payload.toString()
        }
        payload
            .put("actual_km", details.actualKm)
            .put("completed_visits_count", details.completedVisitsCount)
            .put("total_work_minutes", details.totalWorkMinutes)
            .put("actual_route_minutes", details.actualRouteMinutes)
            .put("start_odometer", details.startOdometer)
            .put("end_odometer", details.endOdometer)
            .put("odometer_km", (details.endOdometer - details.startOdometer).coerceAtLeast(0.0))
            .put("fuel_expenses", details.fuelExpenses)
            .put("fuel_liters", details.fuelLiters)
            .put("fuel_consumption_l_per_100km", details.fuelConsumptionLitersPer100Km)
            .put("fuel_compensation", details.fuelCompensation)
            .put("parking_compensation", details.parkingCompensation)
            .put("toll_expenses", details.tollExpenses)
            .put("toll_compensation", details.tollCompensation)
            .put("other_expenses", details.otherExpenses)
        details.userFatigueScore?.let { payload.put("user_fatigue_score", it) }
        return payload.toString()
    }

    private fun visitPayload(visit: VisitEntity): String = JSONObject()
        .put("id", visit.id)
        .put("work_day_id", visit.workDayId)
        .put("address", visit.address)
        .put("income", visit.income)
        .put("clinic", visit.clinic)
        .put("status", visit.status.name)
        .toString()

    private fun officePayload(office: OfficeEntryEntity): String = JSONObject()
        .put("id", office.id)
        .put("work_day_id", office.workDayId)
        .put("address", office.address)
        .put("minutes", office.minutes)
        .put("income", office.income)
        .put("clinic", office.clinic)
        .toString()

    private fun telemedPayload(telemed: TelemedEntryEntity): String = JSONObject()
        .put("id", telemed.id)
        .put("work_day_id", telemed.workDayId)
        .put("minutes", telemed.minutes)
        .put("income", telemed.income)
        .put("clinic", telemed.clinic)
        .toString()

    private fun expensePayload(expense: ExpenseEntity): String = JSONObject()
        .put("id", expense.id)
        .put("work_day_id", expense.workDayId)
        .put("category", expense.category.title)
        .put("amount", expense.amount)
        .put("comment", expense.comment)
        .toString()

    private fun backupWorkDayJson(day: WorkDayEntity): JSONObject {
        return JSONObject(workDayPayload(day))
            .put("created_at_epoch_millis", day.createdAtEpochMillis)
            .put("updated_at_epoch_millis", day.updatedAtEpochMillis)
    }

    private fun backupVisitJson(visit: VisitEntity): JSONObject {
        return JSONObject(visitPayload(visit))
            .put("estimated_drive_minutes", visit.estimatedDriveMinutes)
            .put("actual_drive_minutes", visit.actualDriveMinutes)
            .put("on_site_minutes", visit.onSiteMinutes)
            .put("created_at_epoch_millis", visit.createdAtEpochMillis)
            .put("updated_at_epoch_millis", visit.updatedAtEpochMillis)
    }

    private fun backupOfficeJson(office: OfficeEntryEntity): JSONObject {
        return JSONObject(officePayload(office))
            .put("created_at_epoch_millis", office.createdAtEpochMillis)
            .put("updated_at_epoch_millis", office.updatedAtEpochMillis)
    }

    private fun backupTelemedJson(telemed: TelemedEntryEntity): JSONObject {
        return JSONObject(telemedPayload(telemed))
            .put("created_at_epoch_millis", telemed.createdAtEpochMillis)
            .put("updated_at_epoch_millis", telemed.updatedAtEpochMillis)
    }

    private fun backupExpenseJson(expense: ExpenseEntity): JSONObject {
        return JSONObject(expensePayload(expense))
            .put("created_at_epoch_millis", expense.createdAtEpochMillis)
            .put("updated_at_epoch_millis", expense.updatedAtEpochMillis)
    }

    private fun backupSettingJson(setting: SettingEntity): JSONObject {
        return JSONObject()
            .put("key", setting.key)
            .put("value", setting.value)
            .put("updated_at_epoch_millis", setting.updatedAtEpochMillis)
    }

    private fun backupSyncQueueJson(item: SyncQueueEntity): JSONObject {
        return JSONObject()
            .put("id", item.id)
            .put("event_type", item.eventType)
            .put("entity_type", item.entityType)
            .put("entity_id", item.entityId)
            .put("payload", JSONObject(item.payloadJson))
            .put("status", item.status)
            .put("attempts", item.attempts)
            .put("created_at_epoch_millis", item.createdAtEpochMillis)
            .put("updated_at_epoch_millis", item.updatedAtEpochMillis)
    }

    private fun sendSyncEvent(url: String, apiKey: String, item: SyncQueueEntity): Boolean {
        var connection: HttpURLConnection? = null
        return try {
            val payload = JSONObject()
                .put("event_id", item.id)
                .put("event_type", item.eventType)
                .put("entity_type", item.entityType)
                .put("entity_id", item.entityId)
                .put("payload", JSONObject(item.payloadJson))
            val body = payload.toString().toByteArray(StandardCharsets.UTF_8)
            connection = (URL(url).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 10_000
                readTimeout = 10_000
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Authorization", "Bearer $apiKey")
            }
            connection.outputStream.use { it.write(body) }
            connection.responseCode in 200..299
        } catch (_: Exception) {
            false
        } finally {
            connection?.disconnect()
        }
    }

    private fun postJson(url: String, apiKey: String, payload: JSONObject): JSONObject? {
        if (url.isBlank() || apiKey.isBlank()) {
            return null
        }
        var connection: HttpURLConnection? = null
        return try {
            val body = payload.toString().toByteArray(StandardCharsets.UTF_8)
            connection = (URL(url).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 10_000
                readTimeout = 20_000
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Authorization", "Bearer $apiKey")
            }
            connection.outputStream.use { it.write(body) }
            val stream = if (connection.responseCode in 200..399) {
                connection.inputStream
            } else {
                connection.errorStream
            }
            val text = stream.bufferedReader(StandardCharsets.UTF_8).use { it.readText() }
            JSONObject(text)
        } catch (_: Exception) {
            null
        } finally {
            connection?.disconnect()
        }
    }

    /**
     * GET c offline-кэшем: при успешном ответе (`ok=true`) кэширует его в Room и
     * возвращает; при сети/ошибке — отдаёт последний закэшированный ответ,
     * помечая его `_from_cache=true`.
     */
    private suspend fun cachedGetJson(url: String, apiKey: String, cacheKey: String): JSONObject? {
        val response = getJson(url, apiKey)
        if (response != null && response.optBoolean("ok", false)) {
            dao.saveSetting(SettingEntity(key = cacheKey, value = response.toString(), updatedAtEpochMillis = now()))
            return response
        }
        val cached = dao.getSetting(cacheKey)?.value ?: return null
        return try {
            JSONObject(cached).put("_from_cache", true)
        } catch (_: Exception) {
            null
        }
    }

    private fun getJson(url: String, apiKey: String): JSONObject? {
        if (url.isBlank() || apiKey.isBlank()) {
            return null
        }
        var connection: HttpURLConnection? = null
        return try {
            connection = (URL(url).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 10_000
                readTimeout = 20_000
                setRequestProperty("Authorization", "Bearer $apiKey")
            }
            val stream = if (connection.responseCode in 200..399) {
                connection.inputStream
            } else {
                connection.errorStream
            }
            val text = stream.bufferedReader(StandardCharsets.UTF_8).use { it.readText() }
            JSONObject(text)
        } catch (_: Exception) {
            null
        } finally {
            connection?.disconnect()
        }
    }

    private fun parseCandidateResult(response: JSONObject): CandidateRequestResult {
        val ok = response.optBoolean("ok", false)
        val reason = response.optString("reason", "")
        val candidate = response.optJSONObject("candidate")
        val calculation = response.optJSONObject("calculation")
        val estimate = if (candidate != null && calculation != null) {
            CandidateEstimate(
                visitId = candidate.optInt("id"),
                address = candidate.optString("address"),
                income = candidate.optDouble("income", 0.0),
                clinic = candidate.optString("clinic"),
                decision = calculation.optString("decision"),
                reason = calculation.optString("reason"),
                requiredExtraPayment = calculation.optDouble("required_extra_payment", 0.0),
                requiredCandidateIncome = calculation.optDouble("required_candidate_income", 0.0),
                beforeHourly = calculation.optDouble("before_hourly", 0.0),
                afterHourly = calculation.optDouble("after_hourly", 0.0),
                marginalHourly = calculation.optDouble("marginal_hourly", 0.0),
                extraKm = calculation.optDouble("extra_km", 0.0),
                extraDriveMinutes = calculation.optDouble("extra_drive_minutes", 0.0),
                fatigueExtraPayment = calculation.optDouble("fatigue_extra_payment", 0.0),
                fatigueLevel = calculation.optString("fatigue_level"),
            )
        } else {
            null
        }
        return CandidateRequestResult(
            ok = ok,
            reason = reason,
            estimate = estimate,
            detail = response.optString("detail"),
        )
    }

    private fun parseServerRoute(route: JSONObject?): ServerRouteSnapshot? {
        if (route == null) {
            return null
        }
        val legsJson = route.optJSONArray("legs") ?: JSONArray()
        val legs = buildList {
            for (index in 0 until legsJson.length()) {
                val leg = legsJson.optJSONObject(index) ?: continue
                val visitId = if (leg.isNull("visit_id")) null else leg.optInt("visit_id")
                add(
                    ServerRouteLeg(
                        fromLabel = leg.optString("from_label"),
                        toLabel = leg.optString("to_label"),
                        visitId = visitId,
                        km = leg.optDouble("km", 0.0),
                        minutes = leg.optDouble("minutes", 0.0),
                    ),
                )
            }
        }
        return ServerRouteSnapshot(
            visitsCount = route.optInt("visits_count", 0),
            totalKm = route.optDouble("total_km", 0.0),
            totalMinutes = route.optDouble("total_minutes", 0.0),
            legs = legs,
        )
    }

    private fun parseGpsDayEstimate(estimate: JSONObject?): GpsDayEstimate? {
        if (estimate == null) {
            return null
        }
        return GpsDayEstimate(
            totalWorkMinutes = estimate.optDouble("total_work_minutes", 0.0),
            routeMinutes = estimate.optDouble("route_minutes", 0.0),
            serviceMinutes = estimate.optDouble("service_minutes", 0.0),
            avgServiceMinutes = estimate.optDouble("avg_service_minutes", 0.0),
            detectedVisitsCount = estimate.optInt("detected_visits_count", 0),
            gpsStartedAt = estimate.optString("gps_started_at").ifBlank { null },
            gpsFinishedAt = estimate.optString("gps_finished_at").ifBlank { null },
        )
    }

    private fun parseGpsVisitHint(hint: JSONObject?): GpsVisitHint? {
        if (hint == null) {
            return null
        }
        return GpsVisitHint(
            visitId = hint.optInt("visit_id"),
            address = hint.optString("address"),
            clinic = hint.optString("clinic"),
            dwellMinutes = hint.optDouble("dwell_minutes", 0.0),
            requiredDwellMinutes = hint.optDouble("required_dwell_minutes", 0.0),
            readyToComplete = hint.optBoolean("ready_to_complete", false),
            distanceMeters = hint.optDouble("distance_m", 0.0),
            accuracyMeters = hint.optDouble("accuracy_m", 0.0),
            firstSeenAt = hint.optString("first_seen_at").ifBlank { null },
            lastSeenAt = hint.optString("last_seen_at").ifBlank { null },
            fatigueLabel = hint.optString("fatigue_label").ifBlank { null },
        )
    }

    private fun parseReportSnapshot(response: JSONObject): ReportSnapshot? {
        val summary = response.optJSONObject("summary") ?: return null
        val clinics = mutableListOf<ClinicReportRow>()
        val clinicArray = response.optJSONArray("clinic_breakdown") ?: JSONArray()
        for (index in 0 until clinicArray.length()) {
            val row = clinicArray.optJSONObject(index) ?: continue
            clinics.add(
                ClinicReportRow(
                    clinic = row.optString("clinic"),
                    visitsCount = row.optInt("visits_count", 0),
                    visitIncome = row.optDouble("visit_income", 0.0),
                    telemedIncome = row.optDouble("telemed_income", 0.0),
                    telemedMinutes = row.optDouble("telemed_minutes", 0.0),
                    officeIncome = row.optDouble("office_income", 0.0),
                    officeMinutes = row.optDouble("office_minutes", 0.0),
                    workMinutes = row.optDouble("work_minutes", 0.0),
                    grossIncome = row.optDouble("gross_income", 0.0),
                    netIncome = row.optDouble("net_income", 0.0),
                    netHourlyIncome = row.optDouble("net_hourly_income", 0.0),
                )
            )
        }
        return ReportSnapshot(
            title = response.optString("title"),
            period = response.optString("period"),
            startDate = response.optString("start_date"),
            endDate = response.optString("end_date"),
            summary = ReportSummary(
                daysCount = summary.optInt("days_count", 0),
                visitsCount = summary.optInt("visits_count", 0),
                grossIncome = summary.optDouble("gross_income", 0.0),
                totalExpenses = summary.optDouble("total_expenses", 0.0),
                netProfit = summary.optDouble("net_profit", 0.0),
                netHourlyIncome = summary.optDouble("net_hourly_income", 0.0),
                totalWorkMinutes = summary.optDouble("total_work_minutes", 0.0),
                totalRouteMinutes = summary.optDouble("total_route_minutes", 0.0),
                actualKm = summary.optDouble("actual_km", 0.0),
                visitIncome = summary.optDouble("visit_income", 0.0),
                telemedIncome = summary.optDouble("telemed_income", 0.0),
                officeIncome = summary.optDouble("office_income", 0.0),
                officeMinutes = summary.optDouble("office_minutes", 0.0),
                fuelExpenses = summary.optDouble("fuel_expenses", 0.0),
                amortizationExpenses = summary.optDouble("amortization_expenses", 0.0),
                parkingExpenses = summary.optDouble("parking_expenses", 0.0),
                foodExpenses = summary.optDouble("food_expenses", 0.0),
                foodMealExpenses = summary.optDouble("food_meal_expenses", 0.0),
                coffeeExpenses = summary.optDouble("coffee_expenses", 0.0),
                drinksExpenses = summary.optDouble("drinks_expenses", 0.0),
                tollExpenses = summary.optDouble("toll_expenses", 0.0),
                otherExpenses = summary.optDouble("other_expenses", 0.0),
                fatigueScore = summary.optDouble("fatigue_score", 0.0),
                fatigueWeeklyAverage = summary.optDouble("fatigue_weekly_average", 0.0),
                recoveryDebt = summary.optDouble("recovery_debt", 0.0),
            ),
            clinics = clinics,
            fromCache = response.optBoolean("_from_cache", false),
        )
    }

    private fun parseFatigueSnapshot(response: JSONObject): FatigueSnapshot? {
        val cbi = parseCbiInfo(response.optJSONObject("cbi")) ?: return null
        val dayId = response.optInt("work_day_id", 0).takeIf { it > 0 }
        return FatigueSnapshot(
            source = response.optString("source"),
            workDayId = dayId,
            date = response.optString("date").ifBlank { null },
            summary = parseFatigueSummary(response.optJSONObject("summary")),
            latestFeedback = parseFatigueFeedback(response.optJSONObject("latest_feedback")),
            cbi = cbi,
            fromCache = response.optBoolean("_from_cache", false),
        )
    }

    private fun parseFatigueSummary(summary: JSONObject?): FatigueSummary? {
        if (summary == null) {
            return null
        }
        return FatigueSummary(
            score = summary.optDouble("score", 0.0),
            weeklyAverage = summary.optDouble("weekly_average", 0.0),
            recoveryDebt = summary.optDouble("recovery_debt", 0.0),
            level = summary.optString("level"),
            longStopCount = summary.optInt("long_stop_count", 0),
            pauseMinutes = summary.optDouble("pause_minutes", 0.0),
            heavyVisitCount = summary.optInt("heavy_visit_count", 0),
            circadianRiskMinutes = summary.optDouble("circadian_risk_minutes", 0.0),
            burnoutScore = summary.optDouble("burnout_score", 0.0),
            sleepHours = summary.optDouble("sleep_hours", 0.0),
            sleepQuality = summary.optDouble("sleep_quality", 0.0),
            breakHoursBefore = summary.optDouble("break_hours_before", 0.0),
        )
    }

    private fun parseFatigueFeedback(feedback: JSONObject?): FatigueFeedback? {
        if (feedback == null) {
            return null
        }
        return FatigueFeedback(
            predictedScore = feedback.optDouble("predicted_score", 0.0),
            userScore = feedback.optDouble("user_score", 0.0),
            feedbackType = feedback.optString("feedback_type"),
            error = feedback.optDouble("error", 0.0),
            createdAt = feedback.optString("created_at").ifBlank { null },
        )
    }

    private fun parseCbiInfo(cbi: JSONObject?): CbiInfo? {
        if (cbi == null) {
            return null
        }
        val questions = mutableListOf<String>()
        val questionArray = cbi.optJSONArray("questions") ?: JSONArray()
        for (index in 0 until questionArray.length()) {
            questions.add(questionArray.optString(index))
        }
        return CbiInfo(
            questions = questions,
            latestScore = cbi.optDouble("latest_score", 0.0),
            latestDate = cbi.optString("latest_date").ifBlank { null },
            level = cbi.optString("level"),
        )
    }

    private fun parseFatigueCorrelationReport(response: JSONObject): FatigueCorrelationReport {
        val cells = mutableListOf<FatigueCorrelationCell>()
        val array = response.optJSONArray("cells") ?: JSONArray()
        for (index in 0 until array.length()) {
            val cell = array.optJSONObject(index) ?: continue
            cells.add(
                FatigueCorrelationCell(
                    feature = cell.optString("feature"),
                    target = cell.optString("target"),
                    pearson = cell.nullableDouble("pearson"),
                    spearman = cell.nullableDouble("spearman"),
                    n = cell.optInt("n", 0),
                )
            )
        }
        return FatigueCorrelationReport(
            days = response.optInt("days", 0),
            rowsUsed = response.optInt("rows_used", 0),
            cells = cells,
            fromCache = response.optBoolean("_from_cache", false),
        )
    }

    private fun normalizeSyncUrl(value: String): String {
        val url = value.trim()
        if (url.isBlank()) {
            return ""
        }
        return when {
            url.endsWith("/api/sync") -> url
            url.endsWith("/location") -> url.removeSuffix("/location") + "/api/sync"
            url.endsWith("/") -> url + "api/sync"
            else -> "$url/api/sync"
        }
    }

    private fun normalizeApiUrl(value: String, path: String): String {
        val url = value.trim()
        if (url.isBlank()) {
            return ""
        }
        val base = when {
            url.endsWith("/location") -> url.removeSuffix("/location")
            url.endsWith("/driving") -> url.removeSuffix("/driving")
            url.endsWith("/api/sync") -> url.removeSuffix("/api/sync")
            url.endsWith("/") -> url.dropLast(1)
            else -> url
        }
        return base + path
    }

    private fun expenseCategoryFromTitle(title: String): ExpenseCategory {
        return ExpenseCategory.entries.firstOrNull { it.title == title || it.name == title } ?: ExpenseCategory.Other
    }

    private inline fun <reified T : Enum<T>> enumValueOrDefault(name: String, default: T): T {
        return enumValues<T>().firstOrNull { it.name == name } ?: default
    }

    private inline fun JSONArray.forEachObject(block: (JSONObject) -> Unit) {
        for (index in 0 until length()) {
            val item = optJSONObject(index)
            if (item != null) {
                block(item)
            }
        }
    }

    private fun JSONObject.nullableString(key: String): String? {
        if (isNull(key)) {
            return null
        }
        return optString(key).ifBlank { null }
    }

    private fun JSONObject.nullableDouble(key: String): Double? {
        if (isNull(key) || !has(key)) {
            return null
        }
        return optDouble(key)
    }

    private fun JSONObject.nullableLong(key: String): Long? {
        if (isNull(key) || !has(key)) {
            return null
        }
        return optLong(key)
    }

    private fun now(): Long = System.currentTimeMillis()

    private fun id(): String = UUID.randomUUID().toString()

    /**
     * Очищает офлайн-кэш ответов сервера (маршрут, отчёты, усталость) — все ключи
     * с префиксом `cache_`, где хранятся адреса и снимки данных. Возвращает число
     * удалённых записей для показа пользователю.
     */
    suspend fun clearAddressCache(): Int = withContext(Dispatchers.IO) {
        val count = dao.countSettingsByPrefix(CACHE_PREFIX)
        dao.deleteSettingsByPrefix(CACHE_PREFIX)
        count
    }

    companion object {
        private const val HTTP_NO_CONNECTION = -1
        private const val NO_CONNECTION_MESSAGE = "Нет связи с сервером. Проверьте интернет."
        private const val CACHE_PREFIX = "cache_"
        private const val CACHE_KEY_APP_SETTINGS = "app_settings_cache"
        private const val CACHE_KEY_CLINICS = "clinics"
        private const val CACHE_KEY_TELEMED_CLINICS = "telemed_clinics"

        fun create(context: Context): HomeVisitRepository {
            return HomeVisitRepository(HomeVisitDatabase.getInstance(context))
        }
    }
}
