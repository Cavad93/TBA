package com.homevisit.location.data.local

import androidx.room.TypeConverter
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.VisitKind
import com.homevisit.location.domain.VisitStatus
import com.homevisit.location.domain.WorkDayStatus

class HomeVisitConverters {
    @TypeConverter
    fun fromVisitKind(value: VisitKind): String = value.name

    @TypeConverter
    fun toVisitKind(value: String): VisitKind = runCatching { VisitKind.valueOf(value) }.getOrDefault(VisitKind.Field)

    @TypeConverter
    fun fromWorkDayStatus(value: WorkDayStatus): String = value.name

    @TypeConverter
    fun toWorkDayStatus(value: String): WorkDayStatus = WorkDayStatus.valueOf(value)

    @TypeConverter
    fun fromVisitStatus(value: VisitStatus): String = value.name

    @TypeConverter
    fun toVisitStatus(value: String): VisitStatus = VisitStatus.valueOf(value)

    @TypeConverter
    fun fromExpenseCategory(value: ExpenseCategory): String = value.name

    @TypeConverter
    fun toExpenseCategory(value: String): ExpenseCategory = ExpenseCategory.valueOf(value)
}
