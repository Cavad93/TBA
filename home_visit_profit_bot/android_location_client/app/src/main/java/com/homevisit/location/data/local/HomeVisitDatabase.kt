package com.homevisit.location.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.migration.Migration
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [
        WorkDayEntity::class,
        VisitEntity::class,
        OfficeEntryEntity::class,
        TelemedEntryEntity::class,
        ExpenseEntity::class,
        SettingEntity::class,
        SyncQueueEntity::class,
    ],
    version = 6,
    exportSchema = false,
)
@TypeConverters(HomeVisitConverters::class)
abstract class HomeVisitDatabase : RoomDatabase() {
    abstract fun homeVisitDao(): HomeVisitDao

    companion object {
        @Volatile
        private var instance: HomeVisitDatabase? = null

        fun getInstance(context: Context): HomeVisitDatabase {
            return instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    context.applicationContext,
                    HomeVisitDatabase::class.java,
                    "home_visit.db",
                )
                    .addMigrations(MIGRATION_1_2, MIGRATION_2_3, MIGRATION_3_4, MIGRATION_4_5, MIGRATION_5_6)
                    .build()
                    .also { instance = it }
            }
        }

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE work_days ADD COLUMN startOdometer REAL NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE work_days ADD COLUMN endOdometer REAL")
                db.execSQL("ALTER TABLE work_days ADD COLUMN sleepHours REAL NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE work_days ADD COLUMN sleepQuality REAL NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE work_days ADD COLUMN breakHoursBefore REAL NOT NULL DEFAULT 0")
            }
        }

        // Работа на точке стала заказом в Ленте: у визита появились тип, фиксированная
        // продолжительность и время начала/окончания.
        /**
         * Выход из специальных категорий персональных данных (152-ФЗ, ст. 10).
         *
         * Сон и его качество удаляются с телефона совсем — не «перестают писаться», а
         * стираются: хранить уже собранные физиологические данные «до следующего
         * релиза» это и есть их обработка. SQLite не умеет DROP COLUMN, поэтому таблица
         * пересоздаётся.
         */
        /**
         * Качество перерыва больше не спрашивается — оно вычисляется на сервере из длины
         * перерыва и продолжительности прошлой смены. Колонка с телефона убирается.
         */
        private val MIGRATION_5_6 = object : Migration(5, 6) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE work_days_new (
                        id TEXT NOT NULL PRIMARY KEY,
                        startEpochMillis INTEGER NOT NULL,
                        endEpochMillis INTEGER,
                        status TEXT NOT NULL,
                        startAddress TEXT,
                        finishAddress TEXT,
                        startOdometer REAL NOT NULL,
                        endOdometer REAL,
                        breakHoursBefore REAL NOT NULL,
                        createdAtEpochMillis INTEGER NOT NULL,
                        updatedAtEpochMillis INTEGER NOT NULL
                    )
                    """.trimIndent()
                )
                db.execSQL(
                    """
                    INSERT INTO work_days_new(
                        id, startEpochMillis, endEpochMillis, status, startAddress,
                        finishAddress, startOdometer, endOdometer, breakHoursBefore,
                        createdAtEpochMillis, updatedAtEpochMillis
                    )
                    SELECT id, startEpochMillis, endEpochMillis, status, startAddress,
                           finishAddress, startOdometer, endOdometer, breakHoursBefore,
                           createdAtEpochMillis, updatedAtEpochMillis
                    FROM work_days
                    """.trimIndent()
                )
                db.execSQL("DROP TABLE work_days")
                db.execSQL("ALTER TABLE work_days_new RENAME TO work_days")
            }
        }

        private val MIGRATION_4_5 = object : Migration(4, 5) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE work_days_new (
                        id TEXT NOT NULL PRIMARY KEY,
                        startEpochMillis INTEGER NOT NULL,
                        endEpochMillis INTEGER,
                        status TEXT NOT NULL,
                        startAddress TEXT,
                        finishAddress TEXT,
                        startOdometer REAL NOT NULL,
                        endOdometer REAL,
                        breakUninterrupted INTEGER NOT NULL DEFAULT 1,
                        breakHoursBefore REAL NOT NULL,
                        createdAtEpochMillis INTEGER NOT NULL,
                        updatedAtEpochMillis INTEGER NOT NULL
                    )
                    """.trimIndent()
                )
                db.execSQL(
                    """
                    INSERT INTO work_days_new(
                        id, startEpochMillis, endEpochMillis, status, startAddress,
                        finishAddress, startOdometer, endOdometer, breakUninterrupted,
                        breakHoursBefore, createdAtEpochMillis, updatedAtEpochMillis
                    )
                    SELECT id, startEpochMillis, endEpochMillis, status, startAddress,
                           finishAddress, startOdometer, endOdometer, 1,
                           breakHoursBefore, createdAtEpochMillis, updatedAtEpochMillis
                    FROM work_days
                    """.trimIndent()
                )
                db.execSQL("DROP TABLE work_days")
                db.execSQL("ALTER TABLE work_days_new RENAME TO work_days")
            }
        }

        private val MIGRATION_3_4 = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE visits ADD COLUMN kind TEXT NOT NULL DEFAULT 'Field'")
                db.execSQL("ALTER TABLE visits ADD COLUMN serviceMinutes REAL")
                db.execSQL("ALTER TABLE visits ADD COLUMN plannedStartAt TEXT")
                db.execSQL("ALTER TABLE visits ADD COLUMN plannedEndAt TEXT")
            }
        }

        // Клиника теперь хранится как название (строка), а не имя enum.
        // Конвертируем старые значения enum-имён в названия; неизвестные оставляем как есть.
        private val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                for (table in listOf("visits", "office_entries", "telemed_entries")) {
                    db.execSQL(
                        """
                        UPDATE $table SET clinic = CASE clinic
                            WHEN 'Dynasty' THEN 'Династия'
                            WHEN 'Psk' THEN 'ПСК'
                            WHEN 'Vitamed' THEN 'ВИТАМЕД'
                            WHEN 'Dnd' THEN 'ДНД'
                            ELSE clinic END
                        """.trimIndent()
                    )
                }
            }
        }
    }
}
