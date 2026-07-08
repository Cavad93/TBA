from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from app.db import connect
from app.models import AddVisitInput, EndDayData
from app.repositories import (
    AddressCacheRepository,
    DailyStatsRepository,
    LocationEventRepository,
    LocationSampleRepository,
    SettingsRepository,
    VisitRepository,
    WorkDayLocationRepository,
    WorkDayRepository,
)
from app.services.geocoding_service import (
    GeocodingError,
    detect_base_district_by_location,
    geocode_address,
    is_base_district,
    manual_geocoding_result,
    parse_coordinates,
)
from app.services.profitability_service import calculate_candidate_impact
from app.services.routing_service import RoutingError
from app.services.location_service import calculate_location_day_estimate
from app.services.stats_service import calculate_rolling_averages, finalize_day
from app.telegram_bot.keyboards import candidate_keyboard
from app.telegram_bot.messages import candidate_calculation_message, daily_stats_message
from app.telegram_bot.safe_send import safe_reply_text
from app.utils.text_utils import parse_float

NEW_START, NEW_START_COORDS, NEW_FINISH, NEW_FINISH_COORDS, NEW_SPEED, NEW_SERVICE, NEW_ODOMETER = range(7)
ADD_ADDRESS, ADD_INCOME, ADD_KM, ADD_MINUTES, ADD_DISTRICT, ADD_COORDS = range(10, 16)
(
    END_KM,
    END_ODOMETER,
    END_COUNT,
    END_WORK_HOURS,
    END_ROUTE_HOURS,
    END_FUEL,
    END_FUEL_LITERS,
    END_FUEL_CONSUMPTION,
    END_TELEMED,
    END_TELEMED_MINUTES,
    END_FOOD,
    END_PARKING,
    END_PARKING_COMP,
    END_FUEL_COMP,
    END_TOLL,
    END_TOLL_COMP,
    END_COMP,
    END_OTHER,
) = range(20, 38)


def _repos(context: ContextTypes.DEFAULT_TYPE):
    config = context.application.bot_data["config"]
    connection = connect(config.database_path)
    return (
        connection,
        SettingsRepository(connection),
        WorkDayRepository(connection),
        VisitRepository(connection),
        DailyStatsRepository(connection),
    )


async def newday_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    connection, settings, _, _, stats = _repos(context)
    with connection:
        rolling = calculate_rolling_averages(stats, settings)
        context.user_data["newday"] = {
            "speed": rolling.avg_speed_kmh,
            "service": rolling.service_minutes,
            "route_time_factor": rolling.route_time_factor,
            "default_start": settings.get("default_start_address", "Дом") or "Дом",
            "default_finish": settings.get("default_finish_address", "Дом") or "Дом",
            "default_start_lat": _optional_float(settings.get("default_start_lat")),
            "default_start_lon": _optional_float(settings.get("default_start_lon")),
            "default_finish_lat": _optional_float(settings.get("default_finish_lat")),
            "default_finish_lon": _optional_float(settings.get("default_finish_lon")),
            "last_odometer": _optional_float(settings.get("last_odometer_reading")),
        }
    connection.close()
    await update.effective_message.reply_text(
        f"Начинаем новый рабочий день.\n"
        f"Стартовая точка сегодня? По умолчанию: {context.user_data['newday']['default_start']}.\n"
        f"Напишите адрес или '-' для значения по умолчанию."
    )
    return NEW_START


async def newday_start_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    data = context.user_data["newday"]
    data["start"] = data["default_start"] if value == "-" else value
    if not _fill_point_from_settings(data, "start", "default_start") and not await _geocode_newday_point(update, context, "start"):
        await update.effective_message.reply_text(
            "Не смог найти стартовую точку по адресу. Введите координаты в формате `59.9386, 30.3141`.",
            parse_mode="Markdown",
        )
        return NEW_START_COORDS
    return await _ask_newday_finish(update, context)


async def newday_start_coords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    coordinates = parse_coordinates(update.effective_message.text)
    if coordinates is None:
        await update.effective_message.reply_text("Введите координаты в формате: 59.9386, 30.3141")
        return NEW_START_COORDS
    context.user_data["newday"]["start_lat"], context.user_data["newday"]["start_lon"] = coordinates
    return await _ask_newday_finish(update, context)


async def newday_finish_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    data = context.user_data["newday"]
    data["finish"] = data["default_finish"] if value == "-" else value
    if not _fill_point_from_settings(data, "finish", "default_finish") and not await _geocode_newday_point(update, context, "finish"):
        await update.effective_message.reply_text(
            "Не смог найти финальную точку по адресу. Введите координаты в формате `59.9386, 30.3141`.",
            parse_mode="Markdown",
        )
        return NEW_FINISH_COORDS
    return await _ask_newday_speed(update, context)


async def newday_finish_coords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    coordinates = parse_coordinates(update.effective_message.text)
    if coordinates is None:
        await update.effective_message.reply_text("Введите координаты в формате: 59.9386, 30.3141")
        return NEW_FINISH_COORDS
    context.user_data["newday"]["finish_lat"], context.user_data["newday"]["finish_lon"] = coordinates
    return await _ask_newday_speed(update, context)


async def _ask_newday_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data["newday"]
    await update.effective_message.reply_text(
        f"Финальная точка сегодня? По умолчанию: {data['default_finish']}.\n"
        "Напишите адрес или '-' для значения по умолчанию."
    )
    return NEW_FINISH


async def _ask_newday_speed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data["newday"]
    await update.effective_message.reply_text(
        f"Средняя скорость сегодня? По умолчанию/7 дней: {data['speed']:.1f} км/ч.\n"
        f"Коэффициент времени дороги: x{data['route_time_factor']:.2f}.\n"
        "Введите число или '-' для значения по умолчанию."
    )
    return NEW_SPEED


async def newday_speed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    data = context.user_data["newday"]
    if value != "-":
        try:
            data["speed"] = parse_float(value)
        except ValueError:
            await update.effective_message.reply_text("Скорость должна быть числом. Попробуйте ещё раз.")
            return NEW_SPEED
    await update.effective_message.reply_text(
        f"Среднее время на адресе? По умолчанию/7 дней: {data['service']:.1f} мин.\n"
        "Введите число или '-' для значения по умолчанию."
    )
    return NEW_SERVICE


async def newday_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    data = context.user_data["newday"]
    if value != "-":
        try:
            data["service"] = parse_float(value)
        except ValueError:
            await update.effective_message.reply_text("Время должно быть числом. Попробуйте ещё раз.")
            return NEW_SERVICE
    last_odometer = data.get("last_odometer")
    default_text = f" Можно написать '-' для прошлого значения {last_odometer:.0f}." if last_odometer else ""
    await update.effective_message.reply_text(
        "Какое текущее показание одометра в начале дня?" + default_text
    )
    return NEW_ODOMETER


async def newday_odometer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    data = context.user_data["newday"]
    if value == "-":
        if not data.get("last_odometer"):
            await update.effective_message.reply_text("Прошлого показания ещё нет. Введите текущее показание одометра числом.")
            return NEW_ODOMETER
        data["start_odometer"] = float(data["last_odometer"])
    else:
        try:
            data["start_odometer"] = parse_float(value)
        except ValueError:
            await update.effective_message.reply_text("Показание одометра должно быть числом.")
            return NEW_ODOMETER
        if data["start_odometer"] < 0:
            await update.effective_message.reply_text("Показание одометра не может быть отрицательным.")
            return NEW_ODOMETER
    connection, _, days, _, _ = _repos(context)
    day = days.create(
        data["start"],
        data["finish"],
        data["speed"],
        data["service"],
        data.get("start_lat"),
        data.get("start_lon"),
        data.get("finish_lat"),
        data.get("finish_lon"),
        route_time_factor=data["route_time_factor"],
        start_odometer=data["start_odometer"],
    )
    connection.close()
    await update.effective_message.reply_text(
        f"Рабочий день создан.\n"
        f"Старт: {day.start_address}\n"
        f"Финиш: {day.finish_address}\n"
        f"Координаты старта: {day.start_lat:.6f}, {day.start_lon:.6f}\n"
        f"Координаты финиша: {day.finish_lat:.6f}, {day.finish_lon:.6f}\n"
        f"Скорость: {day.planned_avg_speed_kmh:.1f} км/ч\n"
        f"Время на адресе: {day.planned_service_minutes:.1f} мин\n"
        f"Поправка OSRM по времени: x{day.planned_route_time_factor:.2f}\n"
        f"Стартовый одометр: {day.start_odometer:.0f}"
    )
    context.user_data.pop("newday", None)
    return ConversationHandler.END


def parse_add_payload(text: str) -> dict[str, object]:
    payload = text.partition(" ")[2].strip()
    parts = [part.strip() for part in payload.split("|")] if payload else []
    data: dict[str, object] = {}
    if len(parts) >= 1 and parts[0]:
        data["address"] = parts[0]
    if len(parts) >= 2 and parts[1]:
        data["income"] = parse_float(parts[1])
    if len(parts) >= 3 and parts[2]:
        data["route_km"] = parse_float(parts[2])
    if len(parts) >= 4 and parts[3]:
        data["route_minutes"] = parse_float(parts[3])
    if len(parts) >= 5 and parts[4]:
        data["district"] = parts[4]
    return data


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        data = parse_add_payload(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text(
            "Формат: /add адрес | доход | км | минуты | район\n"
            "Теперь км и минуты можно не указывать: /add Мурино, Воронцовский 5 | 2500"
        )
        return ConversationHandler.END
    context.user_data["add"] = data
    if "address" not in data:
        await update.effective_message.reply_text("Какой адрес или локация вызова? Не вводите ФИО и медданные.")
        return ADD_ADDRESS
    return await _continue_add(update, context)


async def add_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["add"]["address"] = update.effective_message.text.strip()
    return await _continue_add(update, context)


async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["add"]["income"] = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Доход должен быть числом. Попробуйте ещё раз.")
        return ADD_INCOME
    return await _continue_add(update, context)


async def add_km(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["add"]["route_km"] = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Километры должны быть числом. Попробуйте ещё раз.")
        return ADD_KM
    return await _continue_add(update, context)


async def add_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["add"]["route_minutes"] = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Минуты должны быть числом. Попробуйте ещё раз.")
        return ADD_MINUTES
    return await _continue_add(update, context)


async def add_coords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    coordinates = parse_coordinates(update.effective_message.text)
    if coordinates is None:
        await update.effective_message.reply_text("Введите координаты в формате: 59.9386, 30.3141")
        return ADD_COORDS
    context.user_data["add"]["lat"], context.user_data["add"]["lon"] = coordinates
    if "district" not in context.user_data["add"]:
        await update.effective_message.reply_text(
            "Район/локация? Можно написать Приморский, Выборгский, Калининский или '-' если не знаете."
        )
        return ADD_DISTRICT
    return await _finish_add(update, context)


async def add_district(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    if value != "-":
        context.user_data["add"]["district"] = value
    return await _finish_add(update, context)


async def _continue_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data["add"]
    if "income" not in data:
        await update.effective_message.reply_text("Какой доход по этому вызову?")
        return ADD_INCOME
    if float(data["income"]) <= 0:
        await update.effective_message.reply_text("Доход должен быть больше 0.")
        return ADD_INCOME
    if "route_km" in data and float(data["route_km"]) < 0:
        await update.effective_message.reply_text("Километры не могут быть отрицательными.")
        return ADD_KM
    if "route_km" in data and "route_minutes" not in data:
        await update.effective_message.reply_text(
            await _manual_route_question(context, "Сколько минут дороги добавить в ручной расчёт?")
        )
        return ADD_MINUTES
    if "route_minutes" in data and float(data["route_minutes"]) < 0:
        await update.effective_message.reply_text("Минуты не могут быть отрицательными.")
        return ADD_MINUTES
    return await _finish_add(update, context)


async def _finish_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = AddVisitInput(**context.user_data["add"])
    connection, settings, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return ConversationHandler.END
    base_districts = settings.base_districts()
    cache = AddressCacheRepository(connection)
    manual_district = None if data.district == "-" else data.district
    if data.lat is not None and data.lon is not None:
        geo = manual_geocoding_result(data.address, data.lat, data.lon, manual_district)
    else:
        try:
            geo = geocode_address(
                data.address,
                base_districts,
                cache_repo=cache,
                default_city=settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
                default_region=settings.get("default_region", "Ленинградская область") or "Ленинградская область",
                nominatim_url=settings.get("nominatim_url", "https://nominatim.openstreetmap.org") or "https://nominatim.openstreetmap.org",
                user_agent=settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
                timeout_seconds=settings.get_float("request_timeout_seconds", 10),
            )
        except GeocodingError:
            geo = None
    if geo is None or geo.lat is None or geo.lon is None:
        connection.close()
        await update.effective_message.reply_text(
            "Не смог однозначно найти адрес. Введите координаты точки в формате `59.9386, 30.3141`.",
            parse_mode="Markdown",
        )
        return ADD_COORDS

    inferred_base_district = detect_base_district_by_location(geo.district, geo.lat, geo.lon, base_districts)
    district = manual_district or inferred_base_district or geo.district
    candidate = visits.create_candidate(
        day_id=day.id,
        address=data.address,
        income=data.income,
        route_km=data.route_km or 0,
        route_minutes=data.route_minutes or 0,
        district=district,
        is_base_district=is_base_district(district, base_districts),
        lat=geo.lat,
        lon=geo.lon,
        normalized_address=geo.normalized_address,
    )
    try:
        calculation = calculate_candidate_impact(
            day,
            candidate,
            visits,
            settings,
            strict_routing=data.route_km is None or data.route_minutes is None,
        )
    except RoutingError:
        visits.reject(candidate.id)
        connection.close()
        context.user_data["add"] = {
            "address": data.address,
            "income": data.income,
            "district": data.district,
            "lat": geo.lat,
            "lon": geo.lon,
        }
        await update.effective_message.reply_text(
            await _manual_route_question(
                context,
                "Не удалось получить маршрут автоматически. Введите километраж для ручного расчёта.",
            )
        )
        return ADD_KM
    context.user_data["last_candidate_id"] = candidate.id
    connection.close()
    sent = await safe_reply_text(
        update.effective_message,
        candidate_calculation_message(calculation),
        reply_markup=candidate_keyboard(),
    )
    if sent is None:
        # Candidate is already stored. Keep the conversation consistent and let the user retry commands.
        context.user_data["last_candidate_id"] = candidate.id
    context.user_data.pop("add", None)
    return ConversationHandler.END


def _fill_point_from_settings(data: dict, point_key: str, setting_prefix: str) -> bool:
    lat = data.get(f"{setting_prefix}_lat")
    lon = data.get(f"{setting_prefix}_lon")
    if lat is None or lon is None:
        return False
    data[f"{point_key}_lat"] = lat
    data[f"{point_key}_lon"] = lon
    return True


async def _manual_route_question(context: ContextTypes.DEFAULT_TYPE, question: str) -> str:
    add_data = context.user_data.get("add", {})
    address = str(add_data.get("address", "новый адрес"))
    from_label = _current_route_label(context)
    return (
        f"{question}\n\n"
        f"Участок для оценки:\n"
        f"Откуда: {from_label}\n"
        f"Куда: {address}\n\n"
        "Если вы вручную учитываете перестройку всего оставшегося маршрута, вводите добавочное значение для дня."
    )


def _current_route_label(context: ContextTypes.DEFAULT_TYPE) -> str:
    connection, _, days, visits, _ = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        return "текущая точка не определена"
    completed = visits.list_for_day(day.id, ("completed",))
    connection.close()
    completed_with_time = [visit for visit in completed if visit.completed_at]
    if completed_with_time:
        last_completed = sorted(completed_with_time, key=lambda visit: visit.completed_at or "")[-1]
        return last_completed.address
    return day.start_address or "стартовая точка дня"


async def _geocode_newday_point(update: Update, context: ContextTypes.DEFAULT_TYPE, point_key: str) -> bool:
    connection, settings, _, _, _ = _repos(context)
    data = context.user_data["newday"]
    base_districts = settings.base_districts()
    try:
        result = geocode_address(
            data[point_key],
            base_districts,
            cache_repo=AddressCacheRepository(connection),
            default_city=settings.get("default_city", "Санкт-Петербург") or "Санкт-Петербург",
            default_region=settings.get("default_region", "Ленинградская область") or "Ленинградская область",
            nominatim_url=settings.get("nominatim_url", "https://nominatim.openstreetmap.org") or "https://nominatim.openstreetmap.org",
            user_agent=settings.get("geo_user_agent", "home-visit-profit-bot/1.0") or "home-visit-profit-bot/1.0",
            timeout_seconds=settings.get_float("request_timeout_seconds", 10),
        )
    except GeocodingError:
        result = None
    connection.close()
    if result is None or result.lat is None or result.lon is None:
        return False
    data[f"{point_key}_lat"] = result.lat
    data[f"{point_key}_lon"] = result.lon
    return True


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


async def endday_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    connection, settings, days, _, stats = _repos(context)
    day = days.active()
    rolling = calculate_rolling_averages(stats, settings) if day else None
    location_estimate = None
    if day:
        location_estimate = calculate_location_day_estimate(
            day=day,
            samples=LocationSampleRepository(connection),
            location_state=WorkDayLocationRepository(connection),
            events=LocationEventRepository(connection),
        )
    connection.close()
    if day is None:
        await update.effective_message.reply_text("Сейчас нет активного рабочего дня. Сначала выполните /newday.")
        return ConversationHandler.END
    context.user_data["endday"] = {
        "existing_telemed_minutes": day.telemed_minutes,
        "start_odometer": day.start_odometer,
        "default_fuel_consumption": rolling.fuel_consumption_l_per_100km if rolling else 10,
        "gps_total_work_minutes": location_estimate.total_work_minutes if location_estimate else 0,
        "gps_route_minutes": location_estimate.route_minutes if location_estimate else 0,
        "gps_avg_service_minutes": location_estimate.avg_service_minutes if location_estimate else 0,
        "gps_detected_visits_count": location_estimate.detected_visits_count if location_estimate else 0,
    }
    await update.effective_message.reply_text("Сколько всего километров проехали сегодня?")
    return END_KM


async def _collect_float(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, next_state: int, question: str, *, positive: bool = False) -> int:
    try:
        value = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Введите число.")
        return next_state - 1
    if value < 0 or (positive and value <= 0):
        await update.effective_message.reply_text("Значение должно быть положительным.")
        return next_state - 1
    context.user_data["endday"][key] = value
    await update.effective_message.reply_text(question)
    return next_state


def _parse_hours_to_minutes(text: str) -> float:
    value = text.strip().replace(",", ".")
    if ":" in value:
        hours_text, minutes_text = value.split(":", maxsplit=1)
        hours = int(hours_text)
        minutes = int(minutes_text)
        if hours < 0 or minutes < 0 or minutes >= 60:
            raise ValueError
        return hours * 60 + minutes
    hours_float = parse_float(value)
    if hours_float < 0:
        raise ValueError
    return hours_float * 60


def _minutes_to_hours_text(minutes: float) -> str:
    hours = int(minutes // 60)
    rest = int(round(minutes % 60))
    return f"{hours} ч {rest} мин"


async def end_km(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    start_odometer = float(context.user_data["endday"].get("start_odometer", 0) or 0)
    question = (
        f"Какое текущее показание одометра в конце дня? Утром было {start_odometer:.0f}."
        if start_odometer > 0
        else "Стартового одометра нет. Введите общий пробег по приборной панели за день."
    )
    return await _collect_float(
        update,
        context,
        "actual_km",
        END_ODOMETER,
        question,
    )


async def end_odometer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Введите показание одометра числом.")
        return END_ODOMETER
    actual_km = float(context.user_data["endday"].get("actual_km", 0))
    start_odometer = float(context.user_data["endday"].get("start_odometer", 0) or 0)
    if start_odometer > 0:
        if value < start_odometer:
            await update.effective_message.reply_text("Вечернее показание не может быть меньше утреннего.")
            return END_ODOMETER
        odometer_km = value - start_odometer
        if odometer_km < actual_km:
            await update.effective_message.reply_text(
                "Разница одометра меньше рабочих километров. Проверьте рабочие км или показание одометра."
            )
            return END_ODOMETER
        context.user_data["endday"]["end_odometer"] = value
        context.user_data["endday"]["odometer_km"] = odometer_km
    else:
        if value < actual_km:
            await update.effective_message.reply_text(
                "Пробег по панели не может быть меньше рабочих километров. Проверьте число."
            )
            return END_ODOMETER
        context.user_data["endday"]["end_odometer"] = 0.0
        context.user_data["endday"]["odometer_km"] = value
    context.user_data["endday"]["start_odometer"] = start_odometer
    await update.effective_message.reply_text("Сколько адресов фактически завершили?")
    return END_COUNT


async def end_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        count = int(update.effective_message.text.strip())
    except ValueError:
        await update.effective_message.reply_text("Введите целое число.")
        return END_COUNT
    if count < 0:
        await update.effective_message.reply_text("Количество не может быть отрицательным.")
        return END_COUNT
    context.user_data["endday"]["completed_visits_count"] = count
    gps_minutes = float(context.user_data["endday"].get("gps_total_work_minutes", 0) or 0)
    suffix = f"\nЯ вычислил по GPS: {_minutes_to_hours_text(gps_minutes)}. Напишите '-' чтобы взять это значение." if gps_minutes > 0 else ""
    await update.effective_message.reply_text(
        "Сколько часов работали сегодня? Например 8.5 или 8:30." + suffix
    )
    return END_WORK_HOURS


async def end_work_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    if value == "-":
        minutes = float(context.user_data["endday"].get("gps_total_work_minutes", 0) or 0)
        if minutes <= 0:
            await update.effective_message.reply_text("GPS-оценки нет. Введите часы числом: 8.5 или 8:30.")
            return END_WORK_HOURS
    else:
        try:
            minutes = _parse_hours_to_minutes(value)
        except ValueError:
            await update.effective_message.reply_text("Введите часы числом: 8.5 или 8:30.")
            return END_WORK_HOURS
    if minutes <= 0:
        await update.effective_message.reply_text("Время работы должно быть больше 0.")
        return END_WORK_HOURS
    context.user_data["endday"]["total_work_minutes"] = minutes
    gps_route = float(context.user_data["endday"].get("gps_route_minutes", 0) or 0)
    suffix = f"\nЯ вычислил по GPS: {_minutes_to_hours_text(gps_route)}. Напишите '-' чтобы взять это значение." if gps_route > 0 else ""
    await update.effective_message.reply_text(
        "Сколько часов были в дороге? Например 2.25 или 2:15." + suffix
    )
    return END_ROUTE_HOURS


async def end_route_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    if value == "-":
        minutes = float(context.user_data["endday"].get("gps_route_minutes", 0) or 0)
        if minutes <= 0:
            await update.effective_message.reply_text("GPS-оценки дороги нет. Введите часы дороги числом: 2.25 или 2:15.")
            return END_ROUTE_HOURS
    else:
        try:
            minutes = _parse_hours_to_minutes(value)
        except ValueError:
            await update.effective_message.reply_text("Введите часы дороги числом: 2.25 или 2:15.")
            return END_ROUTE_HOURS
    total_work = float(context.user_data["endday"].get("total_work_minutes", 0))
    if minutes < 0 or minutes > total_work:
        await update.effective_message.reply_text("Время дороги не может быть больше общего рабочего времени.")
        return END_ROUTE_HOURS
    context.user_data["endday"]["actual_route_minutes"] = minutes
    gps_avg_service = float(context.user_data["endday"].get("gps_avg_service_minutes", 0) or 0)
    detected_count = int(context.user_data["endday"].get("gps_detected_visits_count", 0) or 0)
    service_text = (
        f"\nПо GPS среднее время на адресе: {gps_avg_service:.0f} мин "
        f"(распознано адресов: {detected_count})."
        if gps_avg_service > 0
        else ""
    )
    await update.effective_message.reply_text(
        "Сколько потратили на топливо сегодня? Если не заправлялись, введите 0." + service_text
    )
    return END_FUEL


async def end_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Введите сумму топлива числом, 0 если не заправлялись.")
        return END_FUEL
    if value < 0:
        await update.effective_message.reply_text("Сумма не может быть отрицательной.")
        return END_FUEL
    context.user_data["endday"]["fuel_expenses"] = value
    if value > 0:
        await update.effective_message.reply_text("На сколько литров заправились сегодня?")
        return END_FUEL_LITERS
    context.user_data["endday"]["fuel_liters"] = 0.0
    return await _ask_fuel_consumption(update, context)


async def end_fuel_liters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Введите объём топлива в литрах.")
        return END_FUEL_LITERS
    if value <= 0:
        await update.effective_message.reply_text("Литры должны быть больше 0.")
        return END_FUEL_LITERS
    context.user_data["endday"]["fuel_liters"] = value
    return await _ask_fuel_consumption(update, context)


async def _ask_fuel_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    default = float(context.user_data["endday"].get("default_fuel_consumption", 10))
    await update.effective_message.reply_text(
        f"Какой фактический расход топлива сегодня, л/100 км? "
        f"Введите вручную или напишите '-' для среднего {default:.1f}."
    )
    return END_FUEL_CONSUMPTION


async def end_fuel_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    if value == "-":
        context.user_data["endday"]["fuel_consumption_l_per_100km"] = float(
            context.user_data["endday"].get("default_fuel_consumption", 10)
        )
    else:
        try:
            consumption = parse_float(value)
        except ValueError:
            await update.effective_message.reply_text("Введите расход л/100 км числом или '-'.")
            return END_FUEL_CONSUMPTION
        if consumption <= 0:
            await update.effective_message.reply_text("Расход должен быть больше 0.")
            return END_FUEL_CONSUMPTION
        context.user_data["endday"]["fuel_consumption_l_per_100km"] = consumption
    await update.effective_message.reply_text("Сколько получили телемедициной?")
    return END_TELEMED


async def end_telemed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Введите число.")
        return END_TELEMED
    if value < 0:
        await update.effective_message.reply_text("Значение не может быть отрицательным.")
        return END_TELEMED
    context.user_data["endday"]["telemed_income"] = value
    existing = context.user_data["endday"].get("existing_telemed_minutes", 0)
    await update.effective_message.reply_text(
        f"Сколько минут заняла телемедицина сегодня? Напишите '-' чтобы оставить уже учтённые {existing:.0f} мин."
    )
    return END_TELEMED_MINUTES


async def end_telemed_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.effective_message.text.strip()
    if value == "-":
        context.user_data["endday"]["telemed_minutes"] = float(
            context.user_data["endday"].get("existing_telemed_minutes", 0)
        )
    else:
        try:
            minutes = parse_float(value)
        except ValueError:
            await update.effective_message.reply_text("Введите число минут или '-'.")
            return END_TELEMED_MINUTES
        if minutes < 0:
            await update.effective_message.reply_text("Минуты не могут быть отрицательными.")
            return END_TELEMED_MINUTES
        context.user_data["endday"]["telemed_minutes"] = minutes
    await update.effective_message.reply_text("Сколько потратили на еду и напитки во время работы?")
    return END_FOOD


async def end_parking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _collect_float(
        update,
        context,
        "parking_expenses",
        END_PARKING_COMP,
        "Сколько компенсировали за парковку?",
    )


async def end_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _collect_float(
        update,
        context,
        "food_expenses",
        END_PARKING,
        "Сколько потратили на парковку?",
    )


async def end_fuel_comp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _collect_float(
        update,
        context,
        "fuel_compensation",
        END_TOLL,
        "Сколько потратили на платную дорогу?",
    )


async def end_parking_comp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _collect_float(
        update,
        context,
        "parking_compensation",
        END_FUEL_COMP,
        "Сколько компенсировали за топливо?",
    )


async def end_toll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _collect_float(
        update,
        context,
        "toll_expenses",
        END_TOLL_COMP,
        "Сколько компенсировали за платную дорогу?",
    )


async def end_toll_comp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _collect_float(
        update,
        context,
        "toll_compensation",
        END_COMP,
        "Сколько было прочих компенсаций от клиник?",
    )


async def end_comp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _collect_float(update, context, "clinic_compensation", END_OTHER, "Были ли прочие расходы? Введите сумму, 0 если нет.")


async def end_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["endday"]["other_expenses"] = parse_float(update.effective_message.text)
    except ValueError:
        await update.effective_message.reply_text("Введите число.")
        return END_OTHER
    data_dict = dict(context.user_data["endday"])
    data_dict.pop("existing_telemed_minutes", None)
    data_dict.pop("gps_total_work_minutes", None)
    data_dict.pop("gps_route_minutes", None)
    data_dict.pop("gps_avg_service_minutes", None)
    data_dict.pop("gps_detected_visits_count", None)
    data = EndDayData(**data_dict)
    connection, settings, days, visits, stats_repo = _repos(context)
    day = days.active()
    if day is None:
        connection.close()
        await update.effective_message.reply_text("Активный день уже не найден.")
        return ConversationHandler.END
    try:
        stats = finalize_day(day, data, days, visits, stats_repo, settings)
    except ValueError:
        connection.close()
        await update.effective_message.reply_text(
            "Похоже, фактические данные противоречат друг другу: время дороги больше общего рабочего времени. "
            "Проверьте километры, скорость или время смены."
        )
        return ConversationHandler.END
    rolling = calculate_rolling_averages(stats_repo, settings)
    if stats.fuel_purchase_expenses > 0 and rolling.fuel_cost_per_km > 0:
        settings.set("car_cost_per_km", f"{rolling.fuel_cost_per_km:.4f}")
    if stats.fuel_price_per_liter > 0:
        settings.set("fuel_price_per_liter", f"{stats.fuel_price_per_liter:.4f}")
    if stats.fuel_consumption_l_per_100km > 0:
        settings.set("fuel_consumption_l_per_100km", f"{stats.fuel_consumption_l_per_100km:.4f}")
    if stats.end_odometer > 0:
        settings.set("last_odometer_reading", f"{stats.end_odometer:.4f}")
    connection.close()
    await update.effective_message.reply_text(
        daily_stats_message(stats)
        + f"\n\nНовое среднее за 7 дней:\n- скорость: {rolling.avg_speed_kmh:.1f} км/ч\n"
        + f"- время на адресе: {rolling.service_minutes:.1f} мин\n"
        + f"- поправка OSRM по времени: x{rolling.route_time_factor:.2f}\n"
        + f"- топливо: {rolling.fuel_cost_per_km:.1f} ₽/км "
        + f"({rolling.fuel_price_per_liter:.1f} ₽/л, {rolling.fuel_consumption_l_per_100km:.1f} л/100 км)"
    )
    context.user_data.pop("endday", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("newday", None)
    context.user_data.pop("add", None)
    context.user_data.pop("endday", None)
    await update.effective_message.reply_text("Ок, диалог отменён.")
    return ConversationHandler.END
