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
    version = 3,
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
                    .addMigrations(MIGRATION_1_2, MIGRATION_2_3)
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
