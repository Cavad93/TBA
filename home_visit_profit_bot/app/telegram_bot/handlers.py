from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.db import connect
from app.repositories import (
    AddressCacheRepository,
    BurnoutSurveyRepository,
    DailyStatsRepository,
    DrivingBehaviorRepository,
    ExpenseRepository,
    FatigueFeedbackRepository,
    LocationEventRepository,
    OfficeRepository,
    SettingsRepository,
    TelemedRepository,
    VisitRepository,
    WorkDayRepository,
)
from app.services.correlation_service import apply_feedback_learning, build_correlation_report
from app.services.fatigue_service import estimate_active_day_fatigue
from app.services.geocoding_service import GeocodingError, geocode_address, parse_coordinates
from app.services.phrase_service import clinic_phrase
from app.services.clinic_report_service import build_active_clinic_breakdown, build_period_clinic_breakdown
from app.services.profitability_service import calculate_candidate_impact, calculate_remaining_route_summary
from app.telegram_bot.keyboards import clinic_keyboard, main_menu_keyboard, stop_classification_keyboard, telemed_clinic_keyboard
from app.telegram_bot.messages import fatigue_correlation_message, optimized_route_message, stats_period_message, summary_message
from app.telegram_bot.conversations import (
    ADD_ADDRESS,
    ADD_CLINIC,
    ADD_COORDS,
    ADD_DISTRICT,
    ADD_INCOME,
    ADD_KM,
    ADD_MINUTES,
    END_COMP,
    END_COUNT,
    END_FOOD,
    END_COFFEE,
    END_DRINKS,
    END_FUEL,
    END_FUEL_CONSUMPTION,
    END_FUEL_COMP,
    END_FUEL_LITERS,
    END_KM,
    END_ODOMETER,
    END_OTHER,
    END_PARKING,
    END_PARKING_COMP,
    END_TELEMED,
    END_TELEMED_MINUTES,
    END_TOLL,
    END_TOLL_COMP,
    END_ROUTE_HOURS,
    END_WORK_HOURS,
    NEW_FINISH,
    NEW_FINISH_COORDS,
    NEW_ODOMETER,
    NEW_SERVICE,
    NEW_SLEEP,
    NEW_SLEEP_QUALITY,
    NEW_SPEED,
    NEW_START,
    NEW_START_COORDS,
    add_address,
    add_clinic,
    add_coords,
    add_district,
    add_income,
    add_km,
    add_minutes,
    add_start,
    cancel,
    end_comp,
    end_count,
    end_food,
    end_coffee,
    end_drinks,
    end_fuel,
    end_fuel_consumption,
    end_fuel_comp,
    end_fuel_liters,
    end_km,
    end_odometer,
    end_other,
    end_parking,
    end_parking_comp,
    end_telemed,
    end_telemed_minutes,
    end_toll,
    end_toll_comp,
    end_route_hours,
    end_work_hours,
    endday_start,
    newday_finish_coords,
    newday_finish_point,
    newday_odometer,
    newday_service,
    newday_sleep,
    newday_sleep_quality,
    newday_speed,
    newday_start,
    newday_start_coords,
    newday_start_point,
)
from app.utils.money_utils import rub
from app.utils.text_utils import parse_amount_command, parse_float


FINISH_ADDRESS, FINISH_COORDS = range(100, 102)
TELEMED_AMOUNT, TELEMED_CLINIC = range(200, 202)
CBI_QUESTION = 300
OFFICE_ADDRESS, OFFICE_MINUTES, OFFICE_INCOME, OFFICE_CLINIC = range(400, 404)
TELEMED_CLINICS = {"пск": "ПСК", "днд": "ДНД"}
OFFICE_CLINICS = {"династия": "Династия", "пск": "ПСК", "витамед": "ВИТАМЕД", "днд": "ДНД"}
CBI_QUESTIONS = [
    "Физическое истощение за последнюю неделю?",
    "Было трудно восстановиться после рабочего дня?",
    "Работа эмоционально выматывала?",
    "Раздражали пациенты, клиники или организация процесса?",
    "Хотелось избегать новых вызовов?",
    "Было ощущение, что работа забирает слишком много сил?",
    "Было ощущение, что в таком темпе сложно продолжать ещё неделю?",
]


def _repos(context: ContextTypes.DEFAULT_TYPE):
    config = context.application.bot_data["config"]
    connection = connect(config.database_path)
    return (
        connection,
        SettingsRepository(connection),
        WorkDayRepository(connection),
        VisitRepository(connection),
        ExpenseRepository(connection),
    )


def _stop_classification_markup(connection, visit_id: int):
    events = LocationEventRepository(connection)
    minutes = events.duration_minutes(visit_id)
    if minutes <= 40:
        return None, ""
    return (
        stop_classification_keyboard(visit_id),
        f"\n\nGPS-остановка у адреса: {minutes:.0f} мин. Уточните, что это было:",
    )


def _cbi_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("0"), KeyboardButton("1"), KeyboardButton("2"), KeyboardButton("3"), KeyboardButton("4")]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="0-4",
    )


def _rebuild_active_route(day, settings, visits):
    all_visits = visits.list_for_day(day.id, ("accepted", "completed"))
    route_summary = calculate_remaining_route_summary(day, all_visits, settings, strict_routing=False)
    active_ids = {visit.id for visit in all_visits if visit.status == "accepted"}
    active_order = [visit_id for visit_id in route_summary.order if visit_id in active_ids]
    if active_order:
        visits.update_order_numbers(active_order)
        all_visits = visits.list_for_day(day.id, ("accepted", "completed"))
        route_summary = calculate_remaining_route_summary(day, all_visits, settings, strict_routing=False)
    return all_visits, route_summary


def _parse_stats_period(text: str) -> tuple[str, str, str]:
    parts = text.split()
    if len(parts) == 1:
        today = date.today()
        start = today.replace(day=1)
        end = _add_month(start)
        return f"Статистика за {start:%Y-%m}", start.isoformat(), end.isoformat()
    if len(parts) != 3:
        raise ValueError(
            "Формат:\n"
            "/stats day 2026-07-07\n"
            "/stats month 2026-07\n"
            "/stats year 2026"
        )
    period = parts[1].lower()
    value = parts[2]
    try:
        if period in {"day", "день"}:
            start = datetime.strptime(value, "%Y-%m-%d").date()
            end = start + timedelta(days=1)
            return f"Статистика за {start.isoformat()}", start.isoformat(), end.isoformat()
        if period in {"month", "месяц"}:
            start = datetime.strptime(value, "%Y-%m").date().replace(day=1)
            end = _add_month(start)
            return f"Статистика за {start:%Y-%m}", start.isoformat(), end.isoformat()
        if period in {"year", "год"}:
            start = datetime.strptime(value, "%Y").date().replace(month=1, day=1)
            end = start.replace(year=start.year + 1)
            return f"Статистика за {start:%Y}", start.isoformat(), end.isoformat()
    except ValueError as error:
        raise ValueError("Дата должна быть в формате 2026-07-07, месяц 2026-07, год 2026.") from error
    raise ValueError("Период должен быть day, month или year.")


def _add_month(value: date) -> date:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1)
    return value.replace(month=value.month + 1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection, repo, _, _, _ = _repos(context)
    repo.set("telegram_chat_id", str(update.effective_chat.id))
    connection.close()
    await update.effective_message.reply_text(
        "Бот для расчёта рентабельности вызовов врача на дом.\n\n"
        "Главные команды:\n"
        "/newday — начать день\n"
        "/add адрес | доход — добавить кандидат с авторасчётом маршрута, затем бот спросит клинику\n"
        "/telemed — добавить телемедицину с выбором ПСК/ДНД\n"
        "/office — добавить приём в офисе предприятия\n"
        "/accept или /reject — принять/отклонить последний кандидат\n"
        "/complete <номер> — завершить адрес\n"
        "/cancel_visit <номер> — отменить активный адрес\n"
        "/finish — изменить точку финиша\n"
        "/cbi — короткий недельный опрос выгорания\n"
        "/fatigue_corr 14 или 28 — матрица корреляций усталости\n"
        "/fatigue_feedback 0-100 — ручная оценка усталости последнего дня\n"
        "/endday — завершить день вопросами\n"
        "/summary — сводка\n"
        "/stats — статистика за месяц\n"
        "/settings — настройки\n\n"
        "Этот чат сохранён для GPS-уведомлений с Android-приложения.\n\n"
        "Если адрес найден странно, используйте /clear_address_cache <адрес> и добавьте его заново.\n\n"
        "Не вводите ФИО пациентов, диагнозы, телефоны и медицинские комментарии."
        ,
        reply_markup=main_menu_keyboard(),
    )


async def accept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return
    candidate = visits.latest_candidate(day.id)
    if candidate is None:
        connection.close()
        await update.effective_message.reply_text("Нет кандидата для принятия. Добавьте адрес через /add.")
        return
    visits.accept(candidate.id)
    all_visits, route_summary = _rebuild_active_route(day, settings, visits)
    connection.close()
    await update.effective_message.reply_text("Адрес принят.\n\n" + optimized_route_message(day, all_visits, route_summary))


async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return
    candidate = visits.latest_candidate(day.id)
    if candidate is None:
        connection.close()
        await update.effective_message.reply_text("Нет кандидата для отказа.")
        return
    visits.reject(candidate.id)
    connection.close()
    await update.effective_message.reply_text("Адрес отклонён.")


async def complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    parts = update.effective_message.text.split()
    if len(parts) != 2:
        await update.effective_message.reply_text("Формат: /complete <номер>")
        return
    try:
        order_number = int(parts[1])
    except ValueError:
        await update.effective_message.reply_text("Номер адреса должен быть целым числом.")
        return

    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return
    current = next(
        (
            visit
            for visit in visits.list_for_day(day.id, ("accepted",))
            if visit.order_number == order_number
        ),
        None,
    )
    if current is None:
        connection.close()
        await update.effective_message.reply_text(f"Адрес №{order_number} не найден.")
        return
    completed = visits.complete_order(day.id, order_number)
    if completed is None:
        connection.close()
        await update.effective_message.reply_text(f"Активный адрес №{order_number} не найден.")
        return
    all_visits, route_summary = _rebuild_active_route(day, settings, visits)
    next_visit = next((visit for visit in all_visits if visit.status == "accepted" and visit.order_number == 1), None)
    stop_markup, stop_text = _stop_classification_markup(connection, cancelled.id)
    connection.close()

    message = f"Адрес завершён: {completed.address}."
    if next_visit:
        message += (
            f"\nСледующий адрес: №{next_visit.order_number}, {next_visit.address}.\n"
            f"\n{optimized_route_message(day, all_visits, route_summary)}"
        )
    else:
        message += "\nПринятых незавершённых адресов больше нет."
    await update.effective_message.reply_text(message + stop_text, reply_markup=stop_markup)


async def complete_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.", reply_markup=main_menu_keyboard())
        return
    current = next(
        (visit for visit in visits.list_for_day(day.id, ("accepted",)) if visit.order_number == 1),
        None,
    )
    if current is None:
        connection.close()
        await update.effective_message.reply_text("Нет текущего активного адреса для завершения.", reply_markup=main_menu_keyboard())
        return
    completed = visits.complete_visit(current.id)
    all_visits, route_summary = _rebuild_active_route(day, settings, visits)
    next_visit = next((visit for visit in all_visits if visit.status == "accepted" and visit.order_number == 1), None)
    stop_markup, stop_text = _stop_classification_markup(connection, completed.id if completed else current.id)
    connection.close()

    message = f"Адрес завершён: {completed.address if completed else current.address}."
    if next_visit:
        message += (
            f"\nСледующий адрес: №{next_visit.order_number}, {next_visit.address}.\n"
            f"\n{optimized_route_message(day, all_visits, route_summary)}"
        )
    else:
        message += "\nПринятых незавершённых адресов больше нет."
    await update.effective_message.reply_text(message + stop_text, reply_markup=stop_markup or main_menu_keyboard())


async def cancel_visit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    parts = update.effective_message.text.split()
    requested_order = None
    if parts and parts[0].startswith("/") and len(parts) == 2:
        try:
            requested_order = int(parts[1])
        except ValueError:
            await update.effective_message.reply_text("Номер адреса должен быть целым числом.", reply_markup=main_menu_keyboard())
            return

    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.", reply_markup=main_menu_keyboard())
        return

    if requested_order is None:
        current = next(
            (visit for visit in visits.list_for_day(day.id, ("accepted",)) if visit.order_number == 1),
            None,
        )
        cancelled = visits.cancel_visit(current.id) if current else None
    else:
        cancelled = visits.cancel_order(day.id, requested_order)

    if cancelled is None:
        connection.close()
        await update.effective_message.reply_text("Активный адрес для отмены не найден.", reply_markup=main_menu_keyboard())
        return

    all_visits, route_summary = _rebuild_active_route(day, settings, visits)
    next_visit = next((visit for visit in all_visits if visit.status == "accepted" and visit.order_number == 1), None)
    stop_markup, stop_text = _stop_classification_markup(connection, cancelled.id)
    connection.close()

    message = f"Адрес отменён: {cancelled.address}."
    if next_visit:
        message += (
            f"\nСледующий адрес: №{next_visit.order_number}, {next_visit.address}.\n\n"
            f"{optimized_route_message(day, all_visits, route_summary)}"
        )
    else:
        message += "\nПринятых незавершённых адресов больше нет."
    await update.effective_message.reply_text(message + stop_text, reply_markup=stop_markup or main_menu_keyboard())


async def location_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not query.data:
        return
    action, _, visit_id_text = query.data.partition(":")
    try:
        visit_id = int(visit_id_text)
    except ValueError:
        await query.edit_message_text("Не смог распознать адрес из уведомления.")
        return
    if action == "location_ignore":
        await query.edit_message_text("Ок, заявку не закрываю.")
        return
    if action != "location_complete":
        return

    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await query.edit_message_text("Активного рабочего дня уже нет.")
        return
    completed = visits.complete_visit(visit_id)
    if completed is None:
        connection.close()
        await query.edit_message_text("Этот адрес уже закрыт или не найден среди активных.")
        return
    all_visits, route_summary = _rebuild_active_route(day, settings, visits)
    next_visit = next((visit for visit in all_visits if visit.status == "accepted" and visit.order_number == 1), None)
    stop_markup, stop_text = _stop_classification_markup(connection, completed.id)
    connection.close()

    message = f"Адрес закрыт по GPS-подсказке: {completed.address}."
    if next_visit:
        message += (
            f"\nСледующий адрес: №{next_visit.order_number}, {next_visit.address}.\n\n"
            f"{optimized_route_message(day, all_visits, route_summary)}"
        )
    else:
        message += "\nПринятых незавершённых адресов больше нет."
    await query.edit_message_text(message + stop_text, reply_markup=stop_markup)


async def fatigue_stop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split(":")
    if len(parts) != 3:
        await query.edit_message_text("Не смог распознать уточнение остановки.")
        return
    _, label, visit_id_text = parts
    labels = {
        "pause": "обед/пауза",
        "waiting": "ожидание",
        "normal": "обычный вызов",
        "heavy": "тяжёлый вызов",
        "conflict": "конфликтный/эмоционально тяжёлый вызов",
    }
    if label not in labels:
        await query.edit_message_text("Не понял тип остановки.")
        return
    try:
        visit_id = int(visit_id_text)
    except ValueError:
        await query.edit_message_text("Не смог распознать адрес.")
        return
    connection = connect(context.application.bot_data["config"].database_path)
    LocationEventRepository(connection).set_fatigue_label(visit_id, label)
    connection.close()
    await query.edit_message_text(f"Остановка учтена как: {labels[label]}.")


async def finish_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    connection, _, days, _, _ = _repos(context)
    day = days.active()
    connection.close()
    if day is None:
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    context.user_data["finish"] = {}
    await update.effective_message.reply_text(
        "Введите новую точку финиша: адрес или координаты `59.9386, 30.3141`.",
        parse_mode="Markdown",
    )
    return FINISH_ADDRESS


async def finish_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    coordinates = parse_coordinates(value)
    if coordinates is not None:
        return await _save_finish(update, context, value, coordinates[0], coordinates[1])

    connection, settings, _, _, _ = _repos(context)
    try:
        geo = geocode_address(
            value,
            settings.base_districts(),
            default_city=settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
            default_region=settings.get("default_region", "Ленинградская область") or "Ленинградская область",
            nominatim_url=settings.get("nominatim_url", "https://nominatim.openstreetmap.org") or "https://nominatim.openstreetmap.org",
            user_agent=settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
            timeout_seconds=settings.get_float("request_timeout_seconds", 10),
        )
    except GeocodingError:
        geo = None
    connection.close()
    if geo is None or geo.lat is None or geo.lon is None:
        context.user_data["finish"] = {"address": value}
        await update.effective_message.reply_text(
            "Не смог найти финиш по адресу. Введите координаты в формате `59.9386, 30.3141`.",
            parse_mode="Markdown",
        )
        return FINISH_COORDS
    return await _save_finish(update, context, geo.normalized_address or value, geo.lat, geo.lon)


async def finish_coords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    coordinates = parse_coordinates(update.effective_message.text)
    if coordinates is None:
        await update.effective_message.reply_text("Введите координаты в формате: 59.9386, 30.3141")
        return FINISH_COORDS
    address = context.user_data.get("finish", {}).get("address", "Финиш")
    return await _save_finish(update, context, address, coordinates[0], coordinates[1])


async def _save_finish(update: Update, context: ContextTypes.DEFAULT_TYPE, address: str, lat: float, lon: float) -> int:
    connection, _, days, _, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Активный день уже не найден.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    days.update_finish(day.id, address, lat, lon)
    connection.close()
    context.user_data.pop("finish", None)
    await update.effective_message.reply_text(
        f"Финиш обновлён:\n{address}\nКоординаты: {lat:.6f}, {lon:.6f}",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def route(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return
    all_visits, route_summary = _rebuild_active_route(day, settings, visits)
    message = optimized_route_message(day, all_visits, route_summary)
    connection.close()
    await update.effective_message.reply_text(message)


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return
    day_visits = visits.list_for_day(day.id)
    active_visits = [visit for visit in day_visits if visit.status in {"accepted", "completed"}]
    telemed_entries = TelemedRepository(connection).list_for_day(day.id)
    office_entries = OfficeRepository(connection).list_for_day(day.id)
    fuel_cost_per_km = settings.get_float("car_cost_per_km", 17.05)
    amortization_factor = settings.get_float("amortization_factor", 0.8)
    km = sum(visit.estimated_extra_km for visit in active_visits)
    fuel_expenses = day.fuel_expenses if day.fuel_expenses > 0 else km * fuel_cost_per_km
    total_expenses = (
        fuel_expenses
        + fuel_expenses * amortization_factor
        + day.parking_expenses
        + day.food_expenses
        + day.food_meal_expenses
        + day.coffee_expenses
        + day.drinks_expenses
        + day.toll_expenses
        + day.other_expenses
    )
    clinic_breakdown = build_active_clinic_breakdown(
        visits=active_visits,
        telemed_entries=telemed_entries,
        service_minutes_per_visit=day.planned_service_minutes,
        total_expenses=total_expenses,
        total_telemed_income=day.telemed_income,
        total_telemed_minutes=day.telemed_minutes,
        office_entries=office_entries,
    )
    fatigue = estimate_active_day_fatigue(
        day=day,
        visits=active_visits,
        settings_repo=settings,
        stats_repo=DailyStatsRepository(connection),
        location_events=LocationEventRepository(connection),
    )
    message = summary_message(
        day,
        day_visits,
        fuel_cost_per_km,
        amortization_factor,
        clinic_breakdown,
        fatigue,
    )
    connection.close()
    await update.effective_message.reply_text(message)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        title, start_date, end_date = _parse_stats_period(update.effective_message.text)
    except ValueError as error:
        await update.effective_message.reply_text(str(error))
        return
    config = context.application.bot_data["config"]
    connection = connect(config.database_path)
    repo = DailyStatsRepository(connection)
    aggregate = repo.aggregate_between(start_date, end_date)
    clinic_breakdown = build_period_clinic_breakdown(
        visit_totals=repo.clinic_visit_totals_between(start_date, end_date),
        telemed_totals=TelemedRepository(connection).aggregate_between(start_date, end_date),
        office_totals=OfficeRepository(connection).aggregate_between(start_date, end_date),
        total_expenses=float(aggregate.get("total_expenses") or 0),
    )
    connection.close()
    await update.effective_message.reply_text(stats_period_message(title, aggregate, clinic_breakdown))


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection, repo, _, _, _ = _repos(context)
    values = repo.all()
    connection.close()
    important = [
        ("Дом", values.get("home_address", "Дом")),
        ("Старт по умолчанию", values.get("default_start_address", "Дом")),
        ("Финиш по умолчанию", values.get("default_finish_address", "Дом")),
        ("Топливо за км", f"{values.get('car_cost_per_km', '17.05')} ₽/км"),
        ("Цена литра", f"{values.get('fuel_price_per_liter', '70')} ₽/л"),
        ("Расход топлива", f"{values.get('fuel_consumption_l_per_100km', '10')} л/100 км"),
        ("Амортизация", f"x{values.get('amortization_factor', '0.8')} от топлива"),
        ("Минимум", f"{values.get('min_hourly_income', '600')} ₽/час"),
        ("Минимум адреса", f"{values.get('min_marginal_hourly_income', '600')} ₽/час"),
        ("Минимум вне зоны", f"{values.get('outside_zone_min_hourly_income', '600')} ₽/час"),
        ("Надбавка вне зоны", f"{values.get('outside_zone_min_extra_payment', '0')} ₽"),
        ("Учёт усталости", values.get("fatigue_enabled", "true")),
        ("Автообучение усталости", values.get("fatigue_learning_enabled", "true")),
        ("Последний CBI", f"{values.get('latest_cbi_score', '0')} / 100"),
        ("Скорость по умолчанию", f"{values.get('default_avg_speed_kmh', '30')} км/ч"),
        ("Время на адресе", f"{values.get('default_service_minutes', '20')} мин"),
        ("Телемедицина по умолчанию", f"{values.get('default_telemed_minutes', '3')} мин"),
        ("Поправка OSRM по времени", f"x{values.get('default_route_time_factor', '1.0')}"),
        ("Базовые районы", values.get("base_districts", "")),
        ("OSRM URL", values.get("osrm_url", "")),
        ("Fallback без OSRM", values.get("routing_fallback_to_estimate", "true")),
        ("Коэффициент дорог", values.get("straight_line_factor", "1.35")),
        ("GPS радиус", f"{values.get('location_geofence_radius_m', '120')} м"),
        ("GPS задержка", f"{values.get('location_dwell_minutes', '12')} мин"),
        ("GPS cooldown", f"{values.get('location_notification_cooldown_minutes', '60')} мин"),
    ]
    await update.effective_message.reply_text(
        "Настройки:\n" + "\n".join(f"- {name}: {value}" for name, value in important)
    )


async def set_numeric_setting(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, label: str) -> None:
    parts = update.effective_message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.effective_message.reply_text(f"Формат: /{parts[0][1:]} <число>")
        return
    try:
        value = parse_float(parts[1])
    except ValueError:
        await update.effective_message.reply_text("Значение должно быть числом.")
        return
    connection, repo, _, _, _ = _repos(context)
    repo.set(key, str(value))
    connection.close()
    await update.effective_message.reply_text(f"{label}: {value}")


async def set_car_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "car_cost_per_km", "Топливо за км обновлено")


async def set_amortization_factor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "amortization_factor", "Коэффициент амортизации обновлён")


async def set_fuel_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "fuel_price_per_liter", "Цена литра обновлена")


async def set_fuel_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "fuel_consumption_l_per_100km", "Расход топлива обновлён")


async def set_min_hourly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "min_hourly_income", "Минимальная доходность обновлена")


async def set_min_marginal_hourly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "min_marginal_hourly_income", "Минимальная доходность адреса обновлена")


async def set_outside_min_hourly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "outside_zone_min_hourly_income", "Минимальная доходность вне зоны обновлена")


async def set_outside_extra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "outside_zone_min_extra_payment", "Минимальная надбавка вне зоны обновлена")


async def set_text_setting(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, label: str) -> None:
    value = update.effective_message.text.partition(" ")[2].strip()
    if not value:
        await update.effective_message.reply_text("Укажите значение после команды.")
        return
    connection, repo, _, _, _ = _repos(context)
    repo.set(key, value)
    connection.close()
    await update.effective_message.reply_text(f"{label}: {value}")


async def set_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_text_setting(update, context, "home_address", "Дом обновлён")


async def set_default_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_text_setting(update, context, "default_start_address", "Старт по умолчанию обновлён")


async def set_default_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_text_setting(update, context, "default_finish_address", "Финиш по умолчанию обновлён")


async def set_base_districts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_text_setting(update, context, "base_districts", "Базовые районы обновлены")


async def set_osrm_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_text_setting(update, context, "osrm_url", "OSRM URL обновлён")


async def set_straight_line_factor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "straight_line_factor", "Коэффициент дорог обновлён")


async def set_route_time_factor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await set_numeric_setting(update, context, "default_route_time_factor", "Поправка OSRM по времени обновлена")


async def set_routing_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    value = update.effective_message.text.partition(" ")[2].strip().lower()
    if value not in {"true", "false", "1", "0", "yes", "no", "да", "нет", "on", "off"}:
        await update.effective_message.reply_text("Формат: /set_routing_fallback true или /set_routing_fallback false")
        return
    enabled = value in {"true", "1", "yes", "да", "on"}
    connection, repo, _, _, _ = _repos(context)
    repo.set("routing_fallback_to_estimate", str(enabled).lower())
    connection.close()
    await update.effective_message.reply_text(f"Fallback без OSRM: {str(enabled).lower()}")


async def set_fatigue_enabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    value = update.effective_message.text.partition(" ")[2].strip().lower()
    if value not in {"true", "false", "1", "0", "yes", "no", "да", "нет", "on", "off"}:
        await update.effective_message.reply_text("Формат: /set_fatigue true или /set_fatigue false")
        return
    enabled = value in {"true", "1", "yes", "да", "on"}
    connection, repo, _, _, _ = _repos(context)
    repo.set("fatigue_enabled", str(enabled).lower())
    connection.close()
    await update.effective_message.reply_text(f"Учёт усталости: {str(enabled).lower()}")


async def money_command(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, label: str) -> None:
    try:
        amount, _ = parse_amount_command(update.effective_message.text)
    except ValueError as error:
        await update.effective_message.reply_text(str(error))
        return
    connection, _, days, _, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return
    days.update_money(day.id, field, amount)
    connection.close()
    await update.effective_message.reply_text(f"{label}: {rub(amount)}")


async def telemed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = update.effective_message.text.split()
    if len(parts) == 1:
        context.user_data["telemed"] = {}
        await update.effective_message.reply_text("Сколько получили телемедициной? Введите сумму.")
        return TELEMED_AMOUNT
    try:
        amount = parse_float(parts[1])
    except ValueError:
        await update.effective_message.reply_text("Доход должен быть числом.")
        return ConversationHandler.END
    if amount <= 0:
        await update.effective_message.reply_text("Доход должен быть больше 0.")
        return ConversationHandler.END
    minutes = None
    clinic = None
    if len(parts) >= 3:
        try:
            minutes = parse_float(parts[2])
            if len(parts) >= 4:
                clinic = _normalize_telemed_clinic(parts[3])
        except ValueError:
            clinic = _normalize_telemed_clinic(parts[2])
    if len(parts) > 4 or clinic is None and len(parts) >= 4:
        await update.effective_message.reply_text("Формат: /telemed <доход> [минуты] [ПСК|ДНД].")
        return ConversationHandler.END
    connection, settings, days, _, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return ConversationHandler.END
    telemed_minutes = minutes if minutes is not None else settings.get_float("default_telemed_minutes", 3)
    if telemed_minutes < 0:
        connection.close()
        await update.effective_message.reply_text("Минуты не могут быть отрицательными.")
        return ConversationHandler.END
    if clinic is None:
        connection.close()
        context.user_data["telemed"] = {"amount": amount, "minutes": telemed_minutes}
        await update.effective_message.reply_text(
            "От какой клиники телемедицина?",
            reply_markup=telemed_clinic_keyboard(),
        )
        return TELEMED_CLINIC
    await _save_telemed(update, context, amount, telemed_minutes, clinic)
    return ConversationHandler.END


async def telemed_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Введите сумму числом.")
        return TELEMED_AMOUNT
    if amount <= 0:
        await update.effective_message.reply_text("Сумма должна быть больше 0.")
        return TELEMED_AMOUNT
    connection, settings, days, _, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    minutes = settings.get_float("default_telemed_minutes", 3)
    connection.close()
    context.user_data["telemed"] = {"amount": amount, "minutes": minutes}
    await update.effective_message.reply_text(
        "От какой клиники телемедицина?",
        reply_markup=telemed_clinic_keyboard(),
    )
    return TELEMED_CLINIC


async def telemed_clinic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clinic = _normalize_telemed_clinic(update.effective_message.text)
    if clinic is None:
        await update.effective_message.reply_text("Выберите ПСК или ДНД.", reply_markup=telemed_clinic_keyboard())
        return TELEMED_CLINIC
    data = context.user_data.get("telemed", {})
    await _save_telemed(
        update,
        context,
        float(data.get("amount", 0)),
        float(data.get("minutes", 0)),
        clinic,
    )
    context.user_data.pop("telemed", None)
    return ConversationHandler.END


async def _save_telemed(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    amount: float,
    telemed_minutes: float,
    clinic: str,
) -> None:
    connection, _, days, _, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.", reply_markup=main_menu_keyboard())
        return
    days.add_money(day.id, "telemed_income", amount)
    days.add_money(day.id, "telemed_minutes", telemed_minutes)
    TelemedRepository(connection).add(day.id, clinic, amount, telemed_minutes)
    updated = days.get(day.id)
    connection.close()
    total_income = updated.telemed_income if updated else day.telemed_income + amount
    total_minutes = updated.telemed_minutes if updated else day.telemed_minutes + telemed_minutes
    await update.effective_message.reply_text(
        f"Телемедицина добавлена: {clinic}, {rub(amount)} / {telemed_minutes:.0f} мин.\n"
        f"Итого за день: {rub(total_income)} / {total_minutes:.0f} мин.",
        reply_markup=main_menu_keyboard(),
    )


def _normalize_telemed_clinic(value: str | None) -> str | None:
    if value is None:
        return None
    return TELEMED_CLINICS.get(value.strip().lower().replace("ё", "е"))


async def office_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    connection, _, days, _, _ = _repos(context)
    day = days.active()
    connection.close()
    if day is None:
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    context.user_data["office"] = {}
    await update.effective_message.reply_text("Адрес офиса предприятия?")
    return OFFICE_ADDRESS


async def office_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    address = update.effective_message.text.strip()
    if not address:
        await update.effective_message.reply_text("Введите адрес офиса.")
        return OFFICE_ADDRESS
    context.user_data["office"]["address"] = address
    await update.effective_message.reply_text("Сколько минут длился приём в офисе?")
    return OFFICE_MINUTES


async def office_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        minutes = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Длительность должна быть числом минут.")
        return OFFICE_MINUTES
    if minutes <= 0:
        await update.effective_message.reply_text("Длительность должна быть больше 0.")
        return OFFICE_MINUTES
    context.user_data["office"]["minutes"] = minutes
    await update.effective_message.reply_text("Сколько оплатили за офисный приём?")
    return OFFICE_INCOME


async def office_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        income = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Стоимость должна быть числом.")
        return OFFICE_INCOME
    if income <= 0:
        await update.effective_message.reply_text("Стоимость должна быть больше 0.")
        return OFFICE_INCOME
    context.user_data["office"]["income"] = income
    await update.effective_message.reply_text("В рамках какой клиники офисный приём?", reply_markup=clinic_keyboard())
    return OFFICE_CLINIC


async def office_clinic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clinic = _normalize_office_clinic(update.effective_message.text)
    if clinic is None:
        await update.effective_message.reply_text("Выберите клинику из списка.", reply_markup=clinic_keyboard())
        return OFFICE_CLINIC
    data = context.user_data.get("office", {})
    connection, _, days, _, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        context.user_data.pop("office", None)
        await update.effective_message.reply_text("Активный день уже не найден.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    address = str(data.get("address", "")).strip()
    minutes = float(data.get("minutes", 0) or 0)
    income = float(data.get("income", 0) or 0)
    if not address or minutes <= 0 or income <= 0:
        connection.close()
        context.user_data.pop("office", None)
        await update.effective_message.reply_text("Данные офиса неполные. Начните заново через кнопку ОФИС.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    days.add_money(day.id, "office_income", income)
    days.add_money(day.id, "office_minutes", minutes)
    OfficeRepository(connection).add(day.id, address, clinic, income, minutes)
    updated = days.get(day.id)
    connection.close()
    context.user_data.pop("office", None)
    total_income = updated.office_income if updated else day.office_income + income
    total_minutes = updated.office_minutes if updated else day.office_minutes + minutes
    await update.effective_message.reply_text(
        f"Офис добавлен: {clinic}, {address}, {rub(income)} / {minutes:.0f} мин.\n"
        f"Итого офис за день: {rub(total_income)} / {total_minutes:.0f} мин.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


def _normalize_office_clinic(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("ё", "е")
    by_number = {"1": "Династия", "2": "ПСК", "3": "ВИТАМЕД", "4": "ДНД"}
    return by_number.get(normalized) or OFFICE_CLINICS.get(normalized)


async def parking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "parking_expenses", "Парковки учтены")


async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "food_expenses", "Еда учтена")


async def meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "food_meal_expenses", "Еда учтена")


async def coffee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "coffee_expenses", "Кофе/энергетики учтены")


async def drinks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "drinks_expenses", "Вода/напитки учтены")


async def compensation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "clinic_compensation", "Прочие компенсации учтены")


async def fuel_compensation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "fuel_compensation", "Компенсация топлива учтена")


async def parking_compensation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "parking_compensation", "Компенсация парковки учтена")


async def toll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "toll_expenses", "Платная дорога учтена")


async def toll_compensation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await money_command(update, context, "toll_compensation", "Компенсация платной дороги учтена")


async def expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        amount, comment = parse_amount_command(update.effective_message.text)
    except ValueError as error:
        await update.effective_message.reply_text(str(error))
        return
    connection, _, days, _, expenses = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return
    expenses.add(day.id, "other", amount, comment)
    days.update_money(day.id, "other_expenses", day.other_expenses + amount)
    connection.close()
    await update.effective_message.reply_text(f"Прочий расход добавлен: {rub(amount)}")


async def phrase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection, settings_repo, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return
    candidate = visits.latest_candidate(day.id)
    if candidate is None:
        connection.close()
        await update.effective_message.reply_text("Нет кандидата для фразы. Сначала добавьте адрес через /add.")
        return
    calculation = calculate_candidate_impact(
        day,
        candidate,
        visits,
        settings_repo,
        DailyStatsRepository(connection),
        LocationEventRepository(connection),
    )
    text = clinic_phrase(calculation, settings_repo.get_float("min_hourly_income", 600))
    connection.close()
    await update.effective_message.reply_text(text)


async def clear_address_cache(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    value = update.effective_message.text.partition(" ")[2].strip()
    connection = connect(context.application.bot_data["config"].database_path)
    cache = AddressCacheRepository(connection)
    if not value or value.lower() == "all":
        count = cache.clear()
        connection.close()
        await update.effective_message.reply_text(f"Кэш адресов очищен: {count} записей.")
        return
    count = cache.delete(value)
    connection.close()
    if count:
        await update.effective_message.reply_text("Адрес удалён из кэша. Попробуйте /add ещё раз.")
    else:
        await update.effective_message.reply_text("Такого адреса в кэше не было.")


async def cbi_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["cbi"] = {"answers": [], "index": 0}
    await update.effective_message.reply_text(
        "CBI/выгорание за последнюю неделю.\n"
        "0 = совсем нет, 4 = почти всегда.\n\n"
        f"1/{len(CBI_QUESTIONS)}. {CBI_QUESTIONS[0]}",
        reply_markup=_cbi_keyboard(),
    )
    return CBI_QUESTION


async def cbi_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = int(update.effective_message.text.strip())
    except ValueError:
        await update.effective_message.reply_text("Выберите число от 0 до 4.", reply_markup=_cbi_keyboard())
        return CBI_QUESTION
    if value < 0 or value > 4:
        await update.effective_message.reply_text("Ответ должен быть от 0 до 4.", reply_markup=_cbi_keyboard())
        return CBI_QUESTION
    data = context.user_data.setdefault("cbi", {"answers": [], "index": 0})
    answers = list(data.get("answers", []))
    answers.append(value)
    index = int(data.get("index", 0)) + 1
    if index < len(CBI_QUESTIONS):
        data["answers"] = answers
        data["index"] = index
        await update.effective_message.reply_text(
            f"{index + 1}/{len(CBI_QUESTIONS)}. {CBI_QUESTIONS[index]}",
            reply_markup=_cbi_keyboard(),
        )
        return CBI_QUESTION
    score = round(sum(answers) / (4 * len(answers)) * 100, 1) if answers else 0.0
    connection, settings, _, _, _ = _repos(context)
    BurnoutSurveyRepository(connection).add(score, json.dumps(answers, ensure_ascii=False))
    settings.set("latest_cbi_score", str(score))
    settings.set("latest_cbi_date", date.today().isoformat())
    connection.close()
    context.user_data.pop("cbi", None)
    await update.effective_message.reply_text(
        f"CBI сохранён: {score:.0f}/100 ({_burnout_level(score)}).\n"
        "Этот показатель будет учитываться в долге восстановления и усталостной надбавке.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


def _burnout_level(score: float) -> str:
    if score >= 75:
        return "высокий риск"
    if score >= 50:
        return "умеренный риск"
    if score >= 25:
        return "лёгкий риск"
    return "низкий риск"


async def fatigue_corr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    parts = update.effective_message.text.split()
    days = 28
    if parts and parts[0].startswith("/") and len(parts) >= 2:
        try:
            days = int(parts[1])
        except ValueError:
            await update.effective_message.reply_text("Формат: /fatigue_corr 14 или /fatigue_corr 28")
            return
    if days not in {14, 28}:
        await update.effective_message.reply_text("Пока поддерживаю 14 или 28 дней: /fatigue_corr 14")
        return
    connection = connect(context.application.bot_data["config"].database_path)
    report = build_correlation_report(DrivingBehaviorRepository(connection), days)
    connection.close()
    await update.effective_message.reply_text(fatigue_correlation_message(report))


async def fatigue_feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    parts = update.effective_message.text.split()
    if len(parts) != 2:
        await update.effective_message.reply_text("Формат: /fatigue_feedback <оценка 0-100>")
        return
    try:
        user_score = parse_float(parts[1])
    except ValueError:
        await update.effective_message.reply_text("Оценка должна быть числом от 0 до 100.")
        return
    if user_score < 0 or user_score > 100:
        await update.effective_message.reply_text("Оценка должна быть от 0 до 100.")
        return
    connection, settings_repo, days_repo, _, _ = _repos(context)
    day = days_repo.latest_closed()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Нет завершённого дня для обратной связи.")
        return
    stats_repo = DailyStatsRepository(connection)
    stats_row = stats_repo.get_by_day(day.id)
    predicted = float(stats_row["fatigue_score"] or 0) if stats_row else user_score
    weights = apply_feedback_learning(
        work_day_id=day.id,
        predicted_score=predicted,
        user_score=user_score,
        feedback_type="manual",
        settings_repo=settings_repo,
        driving_repo=DrivingBehaviorRepository(connection),
        feedback_repo=FatigueFeedbackRepository(connection),
        stats_row=stats_row,
    )
    connection.close()
    await update.effective_message.reply_text(
        f"Оценка сохранена: {user_score:.0f}/100. Ошибка модели: {user_score - predicted:+.0f}.\n"
        f"Активных весов обучения: {sum(1 for value in weights.values() if abs(value) >= 0.1)}."
    )


async def fatigue_feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = (query.data or "").split(":")
    if len(parts) != 4:
        await query.edit_message_text("Не смог распознать ответ по усталости.")
        return
    _, action, day_id_text, predicted_text = parts
    try:
        work_day_id = int(day_id_text)
        predicted = float(predicted_text)
    except ValueError:
        await query.edit_message_text("Не смог распознать день или оценку.")
        return
    if action == "manual":
        await query.edit_message_text(
            f"Введите точную оценку командой: /fatigue_feedback {int(round(predicted))}\n"
            "Например: /fatigue_feedback 72"
        )
        return
    if action == "agree":
        user_score = predicted
    elif action == "lower":
        user_score = max(0.0, predicted - 15)
    elif action == "higher":
        user_score = min(100.0, predicted + 15)
    else:
        await query.edit_message_text("Не понял вариант ответа.")
        return

    connection, settings_repo, _, _, _ = _repos(context)
    stats_repo = DailyStatsRepository(connection)
    stats_row = stats_repo.get_by_day(work_day_id)
    if stats_row is not None:
        predicted = float(stats_row["fatigue_score"] or predicted)
    weights = apply_feedback_learning(
        work_day_id=work_day_id,
        predicted_score=predicted,
        user_score=user_score,
        feedback_type=action,
        settings_repo=settings_repo,
        driving_repo=DrivingBehaviorRepository(connection),
        feedback_repo=FatigueFeedbackRepository(connection),
        stats_row=stats_row,
    )
    connection.close()
    await query.edit_message_text(
        f"Спасибо, учёл обратную связь: {user_score:.0f}/100.\n"
        f"Отклонение от оценки бота: {user_score - predicted:+.0f}.\n"
        f"Весов с заметным обучением: {sum(1 for value in weights.values() if abs(value) >= 0.1)}."
    )


async def candidate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    fake_update = Update(update.update_id, message=query.message)
    if query.data == "accept_candidate":
        await accept(fake_update, context)
    elif query.data == "reject_candidate":
        await reject(fake_update, context)
    elif query.data == "candidate_phrase":
        await phrase(fake_update, context)


def build_handlers() -> list:
    newday_conv = ConversationHandler(
        entry_points=[
            CommandHandler("newday", newday_start),
            MessageHandler(filters.Regex("^Начать день$"), newday_start),
        ],
        states={
            NEW_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_start_point)],
            NEW_SLEEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_sleep)],
            NEW_SLEEP_QUALITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_sleep_quality)],
            NEW_START_COORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_start_coords)],
            NEW_FINISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_finish_point)],
            NEW_FINISH_COORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_finish_coords)],
            NEW_SPEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_speed)],
            NEW_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_service)],
            NEW_ODOMETER: [MessageHandler(filters.TEXT & ~filters.COMMAND, newday_odometer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    add_conv = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_start),
            MessageHandler(filters.Regex("^Добавить адрес$"), add_start),
        ],
        states={
            ADD_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_address)],
            ADD_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income)],
            ADD_CLINIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_clinic)],
            ADD_KM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_km)],
            ADD_MINUTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_minutes)],
            ADD_DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_district)],
            ADD_COORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_coords)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    endday_conv = ConversationHandler(
        entry_points=[
            CommandHandler("endday", endday_start),
            MessageHandler(filters.Regex("^Завершить день$"), endday_start),
        ],
        states={
            END_KM: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_km)],
            END_ODOMETER: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_odometer)],
            END_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_count)],
            END_WORK_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_work_hours)],
            END_ROUTE_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_route_hours)],
            END_FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_fuel)],
            END_FUEL_LITERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_fuel_liters)],
            END_FUEL_CONSUMPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_fuel_consumption)],
            END_TELEMED: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_telemed)],
            END_TELEMED_MINUTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_telemed_minutes)],
            END_PARKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_parking)],
            END_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_food)],
            END_COFFEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_coffee)],
            END_DRINKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_drinks)],
            END_FUEL_COMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_fuel_comp)],
            END_PARKING_COMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_parking_comp)],
            END_TOLL: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_toll)],
            END_TOLL_COMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_toll_comp)],
            END_COMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_comp)],
            END_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_other)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    finish_conv = ConversationHandler(
        entry_points=[
            CommandHandler("finish", finish_start),
            MessageHandler(filters.Regex("^Изменить финиш$"), finish_start),
        ],
        states={
            FINISH_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_address)],
            FINISH_COORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_coords)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    telemed_conv = ConversationHandler(
        entry_points=[
            CommandHandler("telemed", telemed),
            MessageHandler(filters.Regex("^Телемедицина$"), telemed),
        ],
        states={
            TELEMED_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, telemed_amount)],
            TELEMED_CLINIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, telemed_clinic)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    cbi_conv = ConversationHandler(
        entry_points=[
            CommandHandler("cbi", cbi_start),
            MessageHandler(filters.Regex("^CBI/выгорание$"), cbi_start),
        ],
        states={
            CBI_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, cbi_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    office_conv = ConversationHandler(
        entry_points=[
            CommandHandler("office", office_start),
            MessageHandler(filters.Regex("^ОФИС$"), office_start),
        ],
        states={
            OFFICE_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, office_address)],
            OFFICE_MINUTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, office_minutes)],
            OFFICE_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, office_income)],
            OFFICE_CLINIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, office_clinic)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    return [
        CommandHandler("start", start),
        newday_conv,
        add_conv,
        endday_conv,
        finish_conv,
        telemed_conv,
        cbi_conv,
        office_conv,
        CommandHandler("accept", accept),
        CommandHandler("reject", reject),
        CommandHandler("complete", complete),
        CommandHandler("done", complete),
        CommandHandler("cancel_visit", cancel_visit),
        CommandHandler("route", route),
        CommandHandler("summary", summary),
        CommandHandler("stats", stats),
        CommandHandler("fatigue_corr", fatigue_corr),
        CommandHandler("fatigue_feedback", fatigue_feedback_command),
        CommandHandler("settings", settings),
        CommandHandler("set_car_cost", set_car_cost),
        CommandHandler("set_amortization_factor", set_amortization_factor),
        CommandHandler("set_fuel_price", set_fuel_price),
        CommandHandler("set_fuel_consumption", set_fuel_consumption),
        CommandHandler("set_min_hourly", set_min_hourly),
        CommandHandler("set_min_marginal_hourly", set_min_marginal_hourly),
        CommandHandler("set_outside_min_hourly", set_outside_min_hourly),
        CommandHandler("set_outside_extra", set_outside_extra),
        CommandHandler("set_home", set_home),
        CommandHandler("set_default_start", set_default_start),
        CommandHandler("set_default_finish", set_default_finish),
        CommandHandler("set_base_districts", set_base_districts),
        CommandHandler("set_osrm_url", set_osrm_url),
        CommandHandler("set_straight_line_factor", set_straight_line_factor),
        CommandHandler("set_route_time_factor", set_route_time_factor),
        CommandHandler("set_routing_fallback", set_routing_fallback),
        CommandHandler("set_fatigue", set_fatigue_enabled),
        CommandHandler("parking", parking),
        CommandHandler("food", food),
        CommandHandler("meal", meal),
        CommandHandler("coffee", coffee),
        CommandHandler("drinks", drinks),
        CommandHandler("compensation", compensation),
        CommandHandler("fuel_compensation", fuel_compensation),
        CommandHandler("parking_compensation", parking_compensation),
        CommandHandler("toll", toll),
        CommandHandler("toll_compensation", toll_compensation),
        CommandHandler("expense", expense),
        CommandHandler("phrase", phrase),
        CommandHandler("clear_address_cache", clear_address_cache),
        MessageHandler(filters.Regex("^Принять$"), accept),
        MessageHandler(filters.Regex("^Отклонить$"), reject),
        MessageHandler(filters.Regex("^Маршрут$"), route),
        MessageHandler(filters.Regex("^Завершить адрес$"), complete_next),
        MessageHandler(filters.Regex("^Отменить адрес$"), cancel_visit),
        MessageHandler(filters.Regex("^Сводка$"), summary),
        MessageHandler(filters.Regex("^Статистика$"), stats),
        MessageHandler(filters.Regex("^Корреляции усталости$"), fatigue_corr),
        MessageHandler(filters.Regex("^Настройки$"), settings),
        CallbackQueryHandler(location_callback, pattern="^location_(complete|ignore):"),
        CallbackQueryHandler(fatigue_stop_callback, pattern="^fatigue_stop:"),
        CallbackQueryHandler(fatigue_feedback_callback, pattern="^fatigue_feedback:"),
        CallbackQueryHandler(candidate_callback, pattern="^(accept_candidate|reject_candidate|candidate_phrase)$"),
    ]
