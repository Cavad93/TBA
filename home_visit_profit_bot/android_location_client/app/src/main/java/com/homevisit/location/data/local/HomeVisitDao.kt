package com.homevisit.location.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.homevisit.location.domain.WorkDayStatus
import com.homevisit.location.domain.VisitStatus
import kotlinx.coroutines.flow.Flow

@Dao
interface HomeVisitDao {
    @Query("SELECT * FROM work_days ORDER BY startEpochMillis DESC LIMIT 1")
    fun observeLatestWorkDay(): Flow<WorkDayEntity?>

    @Query("SELECT * FROM work_days WHERE status = :status ORDER BY startEpochMillis DESC LIMIT 1")
    suspend fun getLatestWorkDayByStatus(status: WorkDayStatus): WorkDayEntity?

    @Query("SELECT * FROM work_days WHERE id = :id LIMIT 1")
    suspend fun getWorkDay(id: String): WorkDayEntity?

    @Query("SELECT * FROM visits WHERE workDayId = :workDayId ORDER BY createdAtEpochMillis ASC")
    fun observeVisits(workDayId: String): Flow<List<VisitEntity>>

    @Query("SELECT * FROM office_entries WHERE workDayId = :workDayId ORDER BY createdAtEpochMillis ASC")
    fun observeOfficeEntries(workDayId: String): Flow<List<OfficeEntryEntity>>

    @Query("SELECT * FROM telemed_entries WHERE workDayId = :workDayId ORDER BY createdAtEpochMillis ASC")
    fun observeTelemedEntries(workDayId: String): Flow<List<TelemedEntryEntity>>

    @Query("SELECT * FROM expenses WHERE workDayId = :workDayId ORDER BY createdAtEpochMillis ASC")
    fun observeExpenses(workDayId: String): Flow<List<ExpenseEntity>>

    @Query("SELECT * FROM sync_queue WHERE status = :status ORDER BY createdAtEpochMillis ASC LIMIT :limit")
    suspend fun getSyncQueue(status: String = SyncStatus.Pending.value, limit: Int = 50): List<SyncQueueEntity>

    @Query("SELECT * FROM sync_queue WHERE status IN (:statuses) ORDER BY createdAtEpochMillis ASC LIMIT :limit")
    suspend fun getSyncQueueByStatuses(statuses: List<String>, limit: Int = 50): List<SyncQueueEntity>

    @Query("SELECT COUNT(*) FROM sync_queue WHERE status = :status")
    fun observeSyncCount(status: String): Flow<Int>

    @Query("SELECT * FROM work_days ORDER BY startEpochMillis ASC")
    suspend fun getAllWorkDays(): List<WorkDayEntity>

    @Query("SELECT * FROM visits ORDER BY createdAtEpochMillis ASC")
    suspend fun getAllVisits(): List<VisitEntity>

    @Query("SELECT * FROM office_entries ORDER BY createdAtEpochMillis ASC")
    suspend fun getAllOfficeEntries(): List<OfficeEntryEntity>

    @Query("SELECT * FROM telemed_entries ORDER BY createdAtEpochMillis ASC")
    suspend fun getAllTelemedEntries(): List<TelemedEntryEntity>

    @Query("SELECT * FROM expenses ORDER BY createdAtEpochMillis ASC")
    suspend fun getAllExpenses(): List<ExpenseEntity>

    @Query("SELECT * FROM settings ORDER BY key ASC")
    suspend fun getAllSettings(): List<SettingEntity>

    @Query("SELECT * FROM sync_queue ORDER BY createdAtEpochMillis ASC")
    suspend fun getAllSyncQueue(): List<SyncQueueEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveWorkDay(entity: WorkDayEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveVisit(entity: VisitEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveOfficeEntry(entity: OfficeEntryEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveTelemedEntry(entity: TelemedEntryEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveExpense(entity: ExpenseEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveSetting(entity: SettingEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun enqueueSync(entity: SyncQueueEntity)

    @Query("UPDATE sync_queue SET status = :status, attempts = attempts + 1, updatedAtEpochMillis = :updatedAt WHERE id = :id")
    suspend fun updateSyncStatus(id: String, status: String, updatedAt: Long)

    @Query("UPDATE visits SET status = :status, updatedAtEpochMillis = :updatedAt WHERE id = :id")
    suspend fun updateVisitStatus(id: String, status: VisitStatus, updatedAt: Long)
}

enum class SyncStatus(val value: String) {
    Pending("pending"),
    Sent("sent"),
    Failed("failed"),
}
