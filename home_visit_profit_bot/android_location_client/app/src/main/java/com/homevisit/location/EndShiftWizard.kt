package com.homevisit.location

import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.homevisit.location.domain.EndDayDetails
import com.homevisit.location.domain.EndDayPreview
import com.homevisit.location.ui.EndShiftUiState
import kotlin.math.abs

/**
 * Мастер завершения смены.
 *
 * Принцип — минимум действий: сервер уже посчитал пробег, одометр и длительности,
 * пользователь только подтверждает. Любой шаг можно пролистать, тогда остаётся
 * расчётное значение. Отказ от уточнений — не отказ от расчёта: смена всё равно
 * закрывается с расчётными цифрами, иначе статистика дня осталась бы пустой.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun EndShiftWizard(
    endShift: EndShiftUiState,
    onFinish: (EndDayDetails) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                // Клавиатура не должна прятать денежные поля расходов внизу листа.
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            if (endShift.isLoading) {
                LoadingStep()
            } else {
                WizardContent(
                    preview = endShift.preview,
                    message = endShift.message,
                    onFinish = onFinish,
                    onDismiss = onDismiss,
                )
            }
        }
    }
}

@Composable
private fun LoadingStep() {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 40.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        CircularProgressIndicator()
        Text("Считаю итоги смены…", style = MaterialTheme.typography.bodyMedium)
    }
}

/** Шаги мастера. Intro — вопрос «уточнять ли»; дальше идут сами уточнения. */
private enum class WizardStep {
    Intro,
    Expenses,
    Fuel,
    Odometer,
    Mileage,
    Driving,
    WorkTime,
    ServiceTime,
    WorkloadRating,
}

private val QUESTION_STEPS = listOf(
    WizardStep.Expenses,
    WizardStep.Fuel,
    WizardStep.Odometer,
    WizardStep.Mileage,
    WizardStep.Driving,
    WizardStep.WorkTime,
    WizardStep.ServiceTime,
    WizardStep.WorkloadRating,
)

@Composable
private fun WizardContent(
    preview: EndDayPreview?,
    message: String,
    onFinish: (EndDayDetails) -> Unit,
    onDismiss: () -> Unit,
) {
    var step by rememberSaveable { mutableStateOf(WizardStep.Intro) }

    // Предзаполняем расчётными значениями: пользователю остаётся подтвердить.
    var meal by rememberSaveable { mutableStateOf(preview.moneyText { it.foodMealExpenses }) }
    var coffee by rememberSaveable { mutableStateOf(preview.moneyText { it.coffeeExpenses }) }
    var drinks by rememberSaveable { mutableStateOf(preview.moneyText { it.drinksExpenses }) }
    var toll by rememberSaveable { mutableStateOf(preview.moneyText { it.tollExpenses }) }
    var parking by rememberSaveable { mutableStateOf(preview.moneyText { it.parkingExpenses }) }
    var other by rememberSaveable { mutableStateOf(preview.moneyText { it.otherExpenses }) }

    var fuelAmount by rememberSaveable { mutableStateOf("") }
    var fuelLiters by rememberSaveable { mutableStateOf("") }
    var fuelPriceConfirmed by rememberSaveable { mutableStateOf(false) }

    var odometer by rememberSaveable { mutableStateOf(preview?.suggestedEndOdometer.numberText()) }
    // Какой пробег человек выбрал рабочим, когда GPS и одометр разошлись. 0 — не спрашивали.
    var chosenKm by rememberSaveable { mutableStateOf(0.0) }
    var drivingHours by rememberSaveable { mutableStateOf(preview?.drivingMinutes.hoursText()) }
    var workHours by rememberSaveable { mutableStateOf(preview?.totalWorkMinutes.hoursText()) }
    var serviceMinutes by rememberSaveable { mutableStateOf(preview?.avgServiceMinutes.numberText()) }
    var workloadRating by rememberSaveable { mutableStateOf(0) }

    fun details(): EndDayDetails = buildEndDayDetails(
        preview = preview,
        meal = meal,
        coffee = coffee,
        drinks = drinks,
        toll = toll,
        parking = parking,
        other = other,
        fuelAmount = fuelAmount,
        fuelLiters = fuelLiters,
        odometer = odometer,
        chosenKm = chosenKm,
        drivingHours = drivingHours,
        workHours = workHours,
        serviceMinutes = serviceMinutes,
        workloadRating = workloadRating,
    )

    // Нераспознанные правки: показать и не отправлять. Молчание здесь = потеря денег.
    var inputError by rememberSaveable { mutableStateOf("") }

    fun finish() {
        val bad = invalidEndShiftInputs(
            meal, coffee, drinks, toll, parking, other,
            fuelAmount, fuelLiters, odometer, drivingHours, workHours, serviceMinutes,
        )
        if (bad.isNotEmpty()) {
            inputError = "Не распознано: ${bad.joinToString(", ")}. " +
                "Поправьте число или очистите поле — пустое значит «не было»."
            return
        }
        inputError = ""
        onFinish(details())
    }

    fun next() {
        val index = QUESTION_STEPS.indexOf(step)
        if (step == WizardStep.WorkloadRating || index == QUESTION_STEPS.lastIndex) {
            finish()
        } else {
            step = QUESTION_STEPS[index + 1]
        }
    }

    if (step != WizardStep.Intro) {
        StepHeader(step)
    }
    if (inputError.isNotEmpty()) {
        Text(
            inputError,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.error,
        )
    }

    when (step) {
        WizardStep.Intro -> IntroStep(
            message = message,
            onYes = { step = WizardStep.Expenses },
            onNo = { finish() },
        )

        WizardStep.Expenses -> {
            Text(
                "Что потратили за смену. Пустое поле — значит не было.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            MoneyField(meal, { meal = it }, "Еда, ₽")
            MoneyField(coffee, { coffee = it }, "Кофе, ₽")
            MoneyField(drinks, { drinks = it }, "Вода/напитки, ₽")
            MoneyField(toll, { toll = it }, "Платная дорога, ₽")
            MoneyField(parking, { parking = it }, "Парковка, ₽")
            MoneyField(other, { other = it }, "Прочее, ₽")
            // Машина и аренда уже записаны за смену — показываем как справку, без поля
            // ввода: человек видит полную картину расходов, но не может случайно
            // задвоить сумму, вписав её ещё раз.
            RecordedExpenses(preview)
            StepButtons(
                onNext = { next() },
                onSkip = {
                    // «Пропустить» = вернуть расчётные значения, а не унести правку молча.
                    meal = preview.moneyText { it.foodMealExpenses }
                    coffee = preview.moneyText { it.coffeeExpenses }
                    drinks = preview.moneyText { it.drinksExpenses }
                    toll = preview.moneyText { it.tollExpenses }
                    parking = preview.moneyText { it.parkingExpenses }
                    other = preview.moneyText { it.otherExpenses }
                    next()
                },
            )
        }

        WizardStep.Fuel -> {
            FuelStep(
                preview = preview,
                amount = fuelAmount,
                liters = fuelLiters,
                onAmount = { fuelAmount = it; fuelPriceConfirmed = false },
                onLiters = { fuelLiters = it; fuelPriceConfirmed = false },
                priceConfirmed = fuelPriceConfirmed,
                onConfirmPrice = { fuelPriceConfirmed = true },
                onNext = { next() },
                onSkip = {
                    fuelAmount = ""
                    fuelLiters = ""
                    fuelPriceConfirmed = false
                    next()
                },
            )
        }

        WizardStep.Odometer -> {
            val startOdometer = preview?.startOdometer ?: 0.0
            ValueStep(
                value = odometer,
                onValue = { odometer = it },
                label = "Одометр на конец смены, км",
                hint = if (preview == null) {
                    "Введите показание одометра"
                } else {
                    "Утром было ${formatKm(startOdometer)} · за смену " +
                        "${formatKm(preview.suggestedKm)} (${preview.kmSourceTitle()})"
                },
                onNext = { next() },
                onReset = { odometer = preview?.suggestedEndOdometer.numberText() },
            )
            val driven = parseNumber(odometer)?.minus(startOdometer)
            if (preview != null && driven != null && driven < preview.suggestedKm - 0.5) {
                Warning(
                    "Получается меньше, чем проехано по заказам (${formatKm(preview.suggestedKm)}). " +
                        "Проверьте показание — иначе рабочий пробег занизится."
                )
            }
        }

        WizardStep.Mileage -> {
            val gap = mileageGapFor(preview, odometer)
            if (gap == null) {
                // Спрашивать не о чем — расхождение мало или решено настройкой.
                LaunchedEffect(step) { next() }
            } else {
                MileageStep(gap = gap, onChoose = { chosenKm = it; next() })
            }
        }

        WizardStep.Driving -> ValueStep(
            value = drivingHours,
            onValue = { drivingHours = it },
            label = "За рулём, часов",
            hint = preview?.let { "Расчёт: ${minutesText(it.drivingMinutes)} (${it.minutesSourceTitle()})" }
                ?: "Сколько часов провели за рулём",
            onNext = { next() },
            onReset = { drivingHours = preview?.drivingMinutes.hoursText() },
        )

        WizardStep.WorkTime -> {
            ValueStep(
                value = workHours,
                onValue = { workHours = it },
                label = "Всего работали, часов",
                hint = preview?.let { "Расчёт: ${minutesText(it.totalWorkMinutes)} (${it.minutesSourceTitle()})" }
                    ?: "От выезда до возвращения",
                onNext = { next() },
                onReset = { workHours = preview?.totalWorkMinutes.hoursText() },
            )
            val work = parseNumber(workHours)
            val driving = parseNumber(drivingHours)
            if (work != null && driving != null && work < driving) {
                Warning("Общее время меньше времени за рулём — проверьте значения.")
            }
        }

        WizardStep.ServiceTime -> ValueStep(
            value = serviceMinutes,
            onValue = { serviceMinutes = it },
            label = "В среднем на адресе, минут",
            hint = preview?.let {
                "Расчёт: ${minutesText(it.avgServiceMinutes)} · заказов ${it.completedVisitsCount}"
            } ?: "Сколько в среднем занимает один адрес",
            onNext = { next() },
            onReset = { serviceMinutes = preview?.avgServiceMinutes.numberText() },
        )

        WizardStep.WorkloadRating -> WorkloadRatingStep(
            value = workloadRating,
            onValue = { workloadRating = it },
            onNext = { next() },
        )
    }

    if (step != WizardStep.Intro) {
        TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) {
            Text("Отмена")
        }
    }
}

@Composable
private fun StepHeader(step: WizardStep) {
    val index = QUESTION_STEPS.indexOf(step)
    Spacer(Modifier.height(4.dp))
    Text(
        "Шаг ${index + 1} из ${QUESTION_STEPS.size}",
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    LinearProgressIndicator(
        progress = { (index + 1f) / QUESTION_STEPS.size },
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun IntroStep(message: String, onYes: () -> Unit, onNo: () -> Unit) {
    Spacer(Modifier.height(8.dp))
    Text(
        "Смена завершена",
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.Bold,
    )
    Text(
        "Ответите на несколько вопросов? Это уточнит расходы и время — " +
            "и ₽/ч станет считаться точнее.",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    if (message.isNotBlank()) {
        Warning(message)
    }
    Button(
        onClick = onYes,
        modifier = Modifier.fillMaxWidth(),
        colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
    ) {
        Text("Да, уточнить")
    }
    OutlinedButton(onClick = onNo, modifier = Modifier.fillMaxWidth()) {
        Text("Нет, завершить")
    }
    Text(
        "Если «нет» — сохраним расчётные значения, смена всё равно попадёт в отчёты.",
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun FuelStep(
    preview: EndDayPreview?,
    amount: String,
    liters: String,
    onAmount: (String) -> Unit,
    onLiters: (String) -> Unit,
    priceConfirmed: Boolean,
    onConfirmPrice: () -> Unit,
    onNext: () -> Unit,
    // «Пропустить» = «не заправлялся»: введённое очищается, а не уезжает молча.
    onSkip: () -> Unit = onNext,
) {
    Text(
        "Заправлялись сегодня? Если нет — пролистайте, топливо посчитаем по прошлой цене.",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    MoneyField(amount, onAmount, "Заправка, ₽")
    MoneyField(liters, onLiters, "Литров")

    val price = fuelPricePerLiter(amount, liters)
    val lastPrice = preview?.lastFuelPricePerLiter ?: 0.0
    val ratio = preview?.fuelPriceWarnRatio ?: 0.10
    val suspicious = price != null && lastPrice > 0 && abs(price - lastPrice) / lastPrice > ratio

    if (price != null) {
        Text(
            "Выходит ${money(price)} за литр" + if (lastPrice > 0) " · прошлая заправка ${money(lastPrice)}" else "",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
    if (suspicious && !priceConfirmed) {
        Warning(
            "Цена литра сильно отличается от прошлой заправки. " +
                "Проверьте сумму и объём — возможно, опечатка."
        )
        OutlinedButton(onClick = onConfirmPrice, modifier = Modifier.fillMaxWidth()) {
            Text("Всё верно, цена изменилась")
        }
    } else {
        StepButtons(onNext = onNext, onSkip = onSkip)
    }
}

/** Шаг «подтвердите значение»: поле уже заполнено расчётом, обычно достаточно нажать «Дальше». */
@Composable
private fun ValueStep(
    value: String,
    onValue: (String) -> Unit,
    label: String,
    hint: String,
    nextTitle: String = "Дальше",
    onNext: () -> Unit,
    // «Пропустить» обещает «останется расчётное» — значит правку шага надо ОТКАТИТЬ.
    // Раньше skip и «Дальше» были одним колбэком, и правка молча уезжала в итог.
    onReset: (() -> Unit)? = null,
) {
    Text(hint, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    MoneyField(value, onValue, label)
    StepButtons(onNext = onNext, onSkip = { onReset?.invoke(); onNext() }, nextTitle = nextTitle)
}

@Composable
private fun StepButtons(onNext: () -> Unit, onSkip: () -> Unit, nextTitle: String = "Дальше") {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        OutlinedButton(onClick = onSkip, modifier = Modifier.weight(1f)) {
            Text("Пропустить")
        }
        Button(
            onClick = onNext,
            modifier = Modifier.weight(1f),
            colors = ButtonDefaults.buttonColors(containerColor = VerdictColors.go),
        ) {
            Text(nextTitle)
        }
    }
}

@Composable
internal fun Warning(text: String) {
    Card(colors = CardDefaults.cardColors(containerColor = VerdictColors.edgeContainer)) {
        Text(
            text,
            modifier = Modifier.padding(12.dp),
            style = MaterialTheme.typography.bodySmall,
            color = VerdictColors.onEdgeContainer,
        )
    }
}

/**
 * Самооценка усталости 1–10 — последний шаг мастера. Она же обратная связь.
 *
 * Спрашивать «согласен ли ты с оценкой 63 из 100» неестественно — человек не мыслит
 * в наших баллах. «На сколько ты вымотался от 1 до 10» — вопрос, на который отвечают
 * не задумываясь. Ответ переводится в ту же шкалу и идёт туда же, откуда учится модель:
 * пользователь отвечает на понятный вопрос, а система получает нужный ей сигнал.
 */
@Composable
private fun WorkloadRatingStep(value: Int, onValue: (Int) -> Unit, onNext: () -> Unit) {
    Text(
        "Насколько загруженной была смена?",
        style = MaterialTheme.typography.titleMedium,
    )
    Text(
        "1 — спокойный день, 10 — плотнее некуда. Это оценка условий труда: " +
            "по ней приложение подстраивает расчёт под ваш обычный график.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        (1..10).forEach { rating ->
            val selected = value == rating
            val tone = when {
                rating <= 3 -> VerdictColors.go
                rating <= 7 -> VerdictColors.edge
                else -> VerdictColors.skip
            }
            Box(
                Modifier
                    .weight(1f)
                    .height(44.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (selected) tone else MaterialTheme.colorScheme.surfaceContainerHigh)
                    .clickable { onValue(rating) },
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    rating.toString(),
                    style = MaterialTheme.typography.labelMedium,
                    fontFamily = JetBrainsMono,
                    color = if (selected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
    Button(
        onClick = onNext,
        enabled = value > 0,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text("Завершить смену")
    }
    TextButton(onClick = onNext, modifier = Modifier.fillMaxWidth()) {
        Text("Пропустить")
    }
}


/**
 * Считать ли расхождение GPS и одометра поводом для вопроса.
 *
 * Сравниваем только после того, как человек подтвердил показание одометра: до этого
 * сравнивать не с чем. Пороги и политику присылает сервер — они настраиваются.
 */
private fun mileageGapFor(preview: EndDayPreview?, odometer: String): MileageGap? {
    if (preview == null) return null
    val odometerKm = (parseNumber(odometer) ?: return null) - preview.startOdometer
    if (odometerKm <= 0) return null

    return mileageGap(
        EndDayPreviewGap(
            gpsKm = preview.gpsKm,
            policy = preview.mileagePolicy,
            smallGap = preview.mileageSmallGap,
            bigGap = preview.mileageBigGap,
            minKm = preview.mileageMinKm,
        ),
        odometerKm = odometerKm,
    )
}
