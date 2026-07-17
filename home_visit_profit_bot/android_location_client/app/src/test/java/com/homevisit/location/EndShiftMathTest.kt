package com.homevisit.location

import com.homevisit.location.domain.EndDayPreview
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Регресс Этапа 23: «тихие глотатели ввода» в мастере завершения смены.
 *
 * Поля мастера предзаполнены реальными суммами дня; опечатка при правке молча
 * превращалась в 0.0 на сервере — тот же механизм «сервер подставляет присланное
 * вместо накопленного», которым уже теряли vehicle_expenses. Теперь нераспознанный
 * непустой ввод называется по имени и блокирует отправку.
 */
class EndShiftMathTest {

    private fun preview(meal: Double = 0.0) = EndDayPreview(
        gpsKm = 38.0,
        plannedKm = 40.0,
        suggestedKm = 40.0,
        kmSource = "route",
        startOdometer = 1000.0,
        suggestedEndOdometer = 1040.0,
        totalWorkMinutes = 480.0,
        drivingMinutes = 90.0,
        avgServiceMinutes = 20.0,
        completedVisitsCount = 5,
        minutesSource = "route",
        foodMealExpenses = meal,
        coffeeExpenses = 0.0,
        drinksExpenses = 0.0,
        parkingExpenses = 0.0,
        tollExpenses = 0.0,
        otherExpenses = 0.0,
        lastFuelPricePerLiter = 0.0,
        fuelConsumptionLitersPer100Km = 0.0,
        fuelPriceWarnRatio = 0.3,
    )

    @Test
    fun `опечатка в денежном поле называется по имени`() {
        val bad = invalidEndShiftInputs(
            meal = "35о", // буква «о» вместо нуля — классика
            coffee = "", drinks = "", toll = "", parking = "", other = "",
            fuelAmount = "", fuelLiters = "", odometer = "",
            drivingHours = "", workHours = "", serviceMinutes = "",
        )
        assertEquals(listOf("Еда"), bad)
    }

    @Test
    fun `отрицательное — тоже нераспознанное, а не молча ноль`() {
        val bad = invalidEndShiftInputs(
            meal = "", coffee = "", drinks = "", toll = "-50", parking = "", other = "",
            fuelAmount = "", fuelLiters = "", odometer = "",
            drivingHours = "", workHours = "", serviceMinutes = "",
        )
        assertEquals(listOf("Платная дорога"), bad)
    }

    @Test
    fun `пустые поля — осознанное «не было», не ошибка`() {
        val bad = invalidEndShiftInputs(
            meal = "", coffee = "", drinks = "", toll = "", parking = "", other = "",
            fuelAmount = "", fuelLiters = "", odometer = "",
            drivingHours = "", workHours = "", serviceMinutes = "",
        )
        assertTrue(bad.isEmpty())
    }

    @Test
    fun `валидные числа с запятой и пробелами проходят`() {
        val bad = invalidEndShiftInputs(
            meal = "350,5", coffee = "1 200", drinks = "0", toll = "", parking = "", other = "",
            fuelAmount = "2500", fuelLiters = "45,2", odometer = "1043",
            drivingHours = "1,5", workHours = "8", serviceMinutes = "20",
        )
        assertTrue(bad.toString(), bad.isEmpty())
    }

    @Test
    fun `несколько кривых полей перечисляются все`() {
        val bad = invalidEndShiftInputs(
            meal = " x", coffee = "", drinks = "", toll = "", parking = "", other = "",
            fuelAmount = "", fuelLiters = "", odometer = "12o4",
            drivingHours = "", workHours = "восемь", serviceMinutes = "",
        )
        assertEquals(listOf("Еда", "Одометр", "Всего работали"), bad)
    }

    @Test
    fun `пустое денежное поле уходит нулём — контракт «пустое значит не было»`() {
        val details = buildEndDayDetails(
            preview = preview(meal = 350.0),
            meal = "", coffee = "", drinks = "", toll = "", parking = "", other = "",
            fuelAmount = "", fuelLiters = "", odometer = "",
            drivingHours = "", workHours = "", serviceMinutes = "",
        )
        // Пустое поле — осознанный ноль; защита от опечаток живёт ДО этого вызова,
        // в invalidEndShiftInputs: с нераспознанным вводом сюда просто не доходят.
        assertEquals(0.0, details.foodMealExpenses, 1e-9)
    }
}
