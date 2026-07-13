package com.homevisit.location.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.VisitKind
import com.homevisit.location.domain.VisitStatus
import com.homevisit.location.domain.WorkDayStatus

@Entity(tableName = "work_days")
data class WorkDayEntity(
    @PrimaryKey val id: String,
    val startEpochMillis: Long,
    val endEpochMillis: Long?,
    val status: WorkDayStatus,
    val startAddress: String?,
    val finishAddress: String?,
    val startOdometer: Double,
    val endOdometer: Double?,
    // Сна нет: физиологический показатель, из которого выводится состояние здоровья —
    // специальная категория ПДн (152-ФЗ). Качества перерыва тоже нет: оно вычисляется на
    // сервере из длины перерыва и продолжительности прошлой смены. Спрашивать у человека
    // то, что система знает, — лишний вопрос и повод ответить не глядя.
    val breakHoursBefore: Double,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long,
)

@Entity(
    tableName = "visits",
    indices = [Index("workDayId"), Index("status"), Index("clinic")],
)
data class VisitEntity(
    @PrimaryKey val id: String,
    val workDayId: String,
    val address: String,
    val income: Double,
    val clinic: String,
    val status: VisitStatus,
    val estimatedDriveMinutes: Double?,
    val actualDriveMinutes: Double?,
    val onSiteMinutes: Double?,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long,
    // Работа на точке: заказ с фиксированным временем — оптимизатор его не двигает.
    val kind: VisitKind = VisitKind.Field,
    val serviceMinutes: Double? = null,
    val plannedStartAt: String? = null,
    val plannedEndAt: String? = null,
)

@Entity(
    tableName = "office_entries",
    indices = [Index("workDayId"), Index("clinic")],
)
data class OfficeEntryEntity(
    @PrimaryKey val id: String,
    val workDayId: String,
    val address: String,
    val minutes: Double,
    val income: Double,
    val clinic: String,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long,
)

@Entity(
    tableName = "telemed_entries",
    indices = [Index("workDayId"), Index("clinic")],
)
data class TelemedEntryEntity(
    @PrimaryKey val id: String,
    val workDayId: String,
    val minutes: Double,
    val income: Double,
    val clinic: String,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long,
)

@Entity(
    tableName = "expenses",
    indices = [Index("workDayId"), Index("category")],
)
data class ExpenseEntity(
    @PrimaryKey val id: String,
    val workDayId: String,
    val category: ExpenseCategory,
    val amount: Double,
    val comment: String,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long,
)

@Entity(tableName = "settings")
data class SettingEntity(
    @PrimaryKey val key: String,
    val value: String,
    val updatedAtEpochMillis: Long,
)

@Entity(
    tableName = "sync_queue",
    indices = [Index("status"), Index("entityType"), Index("entityId")],
)
data class SyncQueueEntity(
    @PrimaryKey val id: String,
    val eventType: String,
    val entityType: String,
    val entityId: String,
    val payloadJson: String,
    val status: String,
    val attempts: Int,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long,
)
