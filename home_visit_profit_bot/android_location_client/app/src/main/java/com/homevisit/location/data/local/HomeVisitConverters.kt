package com.homevisit.location.data.local

import androidx.room.TypeConverter
import com.homevisit.location.domain.Clinic
import com.homevisit.location.domain.ExpenseCategory
import com.homevisit.location.domain.VisitStatus
import com.homevisit.location.domain.WorkDayStatus

class HomeVisitConverters {
    @TypeConverter
    fun fromClinic(value: Clinic?): String? = value?.name

    @TypeConverter
    fun toClinic(value: String?): Clinic? = value?.let { Clinic.valueOf(it) }

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
