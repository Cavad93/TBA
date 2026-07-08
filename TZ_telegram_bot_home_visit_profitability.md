# Техническое задание для AI-разработчика
## Telegram-бот / Python-скрипт для расчёта рентабельности вызовов врача на дому

**Версия:** 1.0  
**Назначение:** создать Telegram-бота на Python, который помогает врачу-терапевту помощи на дому принимать решение: брать новый вызов или отказаться/требовать спецтариф.  
**Главный KPI:** чистый доход за час.  
**Минимальная приемлемая доходность:** 600 ₽/час.  
**Язык интерфейса:** русский.  
**Данные пациентов:** не хранить ФИО, диагнозы, телефоны, комментарии медицинского характера. Хранить только адреса, координаты, доходы, расходы и технические параметры маршрута.

---

## 1. Контекст задачи

Пользователь — врач-терапевт помощи на дому, работает с несколькими частными клиниками. Вызовы приходят в разные районы Санкт-Петербурга и Ленинградской области. Нужно быстро понимать, выгоден ли новый адрес с учётом:

- текущей корзины адресов на день;
- маршрута и возможности менять порядок адресов;
- дороги домой в конце дня;
- среднего времени движения;
- среднего времени на адресе;
- дохода по конкретному вызову;
- расходов на машину;
- парковок;
- расходов на еду;
- компенсаций от клиник;
- базовой рабочей зоны врача.

Бот должен не просто считать расстояние до нового адреса, а оценивать **маржинальное влияние нового вызова** на уже существующий день: сколько добавится километров, времени и расходов, как изменится доходность за час.

---

## 2. Базовые правила принятия решений

### 2.1. Основной показатель

Основной показатель — **чистый доход за час**:

```text
net_hourly_income = net_profit / total_work_hours
```

где:

```text
net_profit = total_visit_income + telemed_income + clinic_compensation - car_expenses - parking_expenses - food_expenses - other_expenses
```

```text
total_work_hours = route_time_hours + service_time_hours
```

### 2.2. Маржинальный расчёт нового адреса

Для нового адреса считать не только «дом → адрес → дом», а влияние на текущую корзину:

```text
extra_km = optimized_route_km_after - optimized_route_km_before
extra_minutes = optimized_route_minutes_after - optimized_route_minutes_before
```

Маржинальная прибыль нового адреса:

```text
marginal_profit = visit_income - marginal_car_cost
```

где:

```text
marginal_car_cost = extra_km * car_cost_per_km
```

Маржинальная доходность нового адреса:

```text
marginal_hourly_income = marginal_profit / ((extra_minutes + avg_service_minutes) / 60)
```

### 2.3. Условие «однозначно да»

Если после добавления нового вызова **средняя доходность дня за час увеличивается**, бот должен писать:

```text
Решение: ОДНОЗНАЧНО ДА. Добавление адреса повышает среднюю доходность за час.
```

### 2.4. Условие «требовать спецтариф»

Базовые районы врача:

- Приморский;
- Выборгский;
- Калининский.

Все адреса вне этих районов бот должен автоматически помечать:

```text
ВНИМАНИЕ: адрес вне базовой зоны. Рекомендация: требовать спецтариф.
```

Особое правило:

- если в начале дня меньше 5 адресов в базовых районах, бот должен особенно строго относиться к адресам вне базовой зоны;
- адреса вне базовой зоны при малом количестве базовых адресов должны помечаться как потенциально рискованные, даже если текущий средний доход за час временно кажется приемлемым.

Формулировка:

```text
Адрес вне базовой зоны, а базовых адресов сегодня пока меньше 5. Рекомендация: не брать без спецтарифа, потому что адрес может сломать маршрут и снизить эффективность дня.
```

---

## 3. Важные пользовательские условия

### 3.1. Старт и финиш

- День всегда заканчивается дома, если пользователь не указал другое.
- День обычно начинается дома, но не всегда.
- В настройках должна быть возможность менять:
  - точку старта по умолчанию;
  - точку финиша по умолчанию;
  - стартовую точку конкретного рабочего дня;
  - финальную точку конкретного рабочего дня.

Пример команд:

```text
/set_home Санкт-Петербург, ...
/set_default_start Санкт-Петербург, ...
/set_default_finish Санкт-Петербург, ...
/start_point Клиника, адрес...
/finish_point Дом
```

### 3.2. Дорогу домой считать обязательно

В каждом расчёте маршрута должна учитываться конечная точка дня.

Пример:

```text
Старт → Адрес 1 → Адрес 2 → Адрес 3 → Финиш
```

а не:

```text
Старт → Адрес 1 → Адрес 2 → Адрес 3
```

### 3.3. Доход по вызову вводится вручную

Пользователь работает в разных клиниках, поэтому стоимость вызова разная. Бот не должен жёстко привязывать тариф к клинике.

При добавлении адреса пользователь указывает:

```text
/add <адрес> | <доход>
```

Пример:

```text
/add Санкт-Петербург, Богатырский проспект 10 | 2500
```

Если доход не указан, бот должен уточнить:

```text
Какой доход по этому вызову?
```

### 3.4. Компенсации от клиник

Компенсация километров есть только у одной из четырёх клиник. Поэтому компенсация не должна автоматически считаться по каждому адресу.

Компенсации вводятся вручную в конце дня:

```text
Сколько сегодня компенсировали клиники?
```

или командой:

```text
/compensation 1200
```

### 3.5. Налоги и комиссии

Налоги, НДФЛ, самозанятость, комиссии и иные удержания не учитывать.

### 3.6. Парковки и еда

Парковки и расходы на еду вводятся вручную в конце дня или отдельными командами:

```text
/parking 450
/food 700
/expense 300 мойка
```

---

## 4. Среднее время на адресе и средняя скорость

### 4.1. Стартовое значение времени на адресе

По умолчанию считать, что один вызов занимает:

```text
avg_service_minutes = 20
```

### 4.2. Обновление по завершению дня

В конце рабочего дня пользователь вводит фактические данные:

- сколько всего километров проехал;
- сколько адресов завершил;
- среднюю скорость за день;
- время начала рабочего дня;
- время окончания рабочего дня;
- парковки;
- еда;
- компенсации;
- прочие расходы.

Бот должен вычислить фактическое среднее время на адресе:

```text
actual_drive_minutes = actual_km / actual_avg_speed_kmh * 60
```

```text
actual_total_work_minutes = end_time - start_time
```

```text
actual_service_minutes_total = actual_total_work_minutes - actual_drive_minutes
```

```text
actual_service_minutes_per_visit = actual_service_minutes_total / completed_visits_count
```

Если значение получилось отрицательным или явно ошибочным, бот должен предупредить:

```text
Похоже, фактические данные противоречат друг другу: время дороги больше общего рабочего времени. Проверьте километры, скорость или время смены.
```

### 4.3. Скользящая средняя за 7 дней

Бот должен хранить историю фактического среднего времени на адресе и средней скорости.

Использовать простую скользящую среднюю за последние 7 завершённых рабочих дней:

```text
avg_service_minutes_7d = mean(actual_service_minutes_per_visit for last 7 completed days)
```

```text
avg_speed_kmh_7d = mean(actual_avg_speed_kmh for last 7 completed days)
```

Если завершённых дней меньше 7, считать среднее по доступным дням. Если данных нет, использовать значения по умолчанию:

```text
avg_service_minutes = 20
avg_speed_kmh = значение из настроек
```

---

## 5. Технологический стек

### 5.1. Основной стек

Рекомендуемый стек:

```text
Python 3.11+
python-telegram-bot
SQLite
SQLAlchemy или sqlite3
Pydantic
PyYAML
OSRM или GraphHopper
Nominatim / другой geocoder
OR-Tools для оптимизации маршрута
Docker / docker-compose опционально
```

### 5.2. Telegram

Использовать библиотеку `python-telegram-bot`.

Нужны:

- обработчики команд;
- обработчики обычных сообщений;
- пошаговые диалоги для завершения дня;
- inline-кнопки для `Принять`, `Отказаться`, `Показать расчёт`, `Перестроить маршрут`.

### 5.3. Геокодинг

Задача geocoder:

```text
текстовый адрес → координаты lat/lon
```

Требования:

- нормализовать адреса;
- добавлять город/регион по умолчанию, если пользователь написал коротко;
- кэшировать результаты;
- хранить confidence/quality, если сервис его возвращает;
- при неоднозначности адреса просить выбрать вариант.

Пример:

```text
Выберите найденный адрес:
1. Санкт-Петербург, Богатырский проспект, 10
2. Санкт-Петербург, Богатырский проспект, 10к1
3. Санкт-Петербург, Богатырский проспект, 10А
```

### 5.4. Роутинг

Задача routing engine:

```text
координаты A и B → расстояние и время пути
```

Нужны два режима:

1. расчёт маршрута между двумя точками;
2. расчёт матрицы расстояний/времени между всеми точками дня.

Матрица нужна для оптимизации порядка адресов.

### 5.5. Оптимизация маршрута

Так как врач — одна машина/один исполнитель, задача похожа на TSP:

```text
найти порядок посещения адресов, минимизирующий время/расстояние
```

В маршруте есть:

- фиксированная стартовая точка;
- фиксированная конечная точка;
- набор незавершённых адресов;
- завершённые адреса не переставляются и не участвуют в оптимизации будущего маршрута.

После добавления нового адреса бот должен:

1. взять текущую точку врача или стартовую точку дня;
2. взять все незавершённые принятые адреса;
3. добавить новый адрес;
4. перестроить оптимальный порядок;
5. присвоить новые порядковые номера;
6. показать список адресов.

---

## 6. Логика статусов адресов

У адреса должны быть статусы:

```text
candidate      — адрес предложен, но ещё не принят
accepted       — адрес принят и находится в маршруте
completed      — адрес завершён
rejected       — адрес отклонён
cancelled      — адрес отменён
```

После `/accept` адрес становится `accepted`.

После `/done <номер>` адрес становится `completed`.

После завершения адреса бот должен:

- зафиксировать время завершения;
- обновить текущую точку врача;
- показать следующий адрес;
- показать обновлённый маршрут.

Пример:

```text
/done 2
```

Ответ:

```text
Адрес №2 завершён.
Следующий адрес: №3, Санкт-Петербург, ...
Оценка дороги: 18 минут, 7.4 км.
```

---

## 7. Команды Telegram-бота

### 7.1. Начало и завершение дня

```text
/newday
```

Создать новый рабочий день.

Бот спрашивает:

1. Стартовая точка сегодня? По умолчанию — дом.
2. Финальная точка сегодня? По умолчанию — дом.
3. Использовать среднюю скорость за 7 дней или указать вручную?
4. Использовать среднее время на адресе за 7 дней или указать вручную?

```text
/endday
```

Завершить рабочий день. Бот должен запустить пошаговый диалог.

Вопросы при завершении дня:

```text
1. Сколько всего километров проехали сегодня?
2. Сколько адресов фактически завершили?
3. Какая была средняя скорость сегодня?
4. Во сколько начали рабочий день?
5. Во сколько закончили рабочий день?
6. Сколько получили телемедициной?
7. Сколько потратили на парковки?
8. Сколько потратили на еду?
9. Сколько компенсировали клиники?
10. Были ли прочие расходы?
```

После ответов бот выводит итог дня.

### 7.2. Добавление адреса

```text
/add <адрес> | <доход>
```

Пример:

```text
/add Мурино, Воронцовский бульвар 5 | 2500
```

Если адрес найден, бот должен:

1. определить район;
2. проверить, входит ли район в базовую зону;
3. посчитать текущий оптимальный маршрут без адреса;
4. посчитать оптимальный маршрут с адресом;
5. сравнить доходность до и после;
6. показать подробный расчёт;
7. предложить принять или отказаться.

### 7.3. Принять/отклонить адрес

```text
/accept
/reject
```

Также желательно сделать inline-кнопки:

```text
[Принять] [Отказаться] [Расчёт спецтарифа]
```

### 7.4. Завершить адрес

```text
/done <номер>
```

Пример:

```text
/done 1
```

После завершения бот перестраивает маршрут только по незавершённым адресам.

### 7.5. Показать маршрут

```text
/route
```

Ответ:

```text
Текущий маршрут:
Старт: Дом
1. Адрес A — доход 2500 ₽ — 18 мин от текущей точки
2. Адрес B — доход 3000 ₽ — 22 мин
3. Адрес C — доход 2500 ₽ — 14 мин
Финиш: Дом

Итого: 43 км, 1 ч 42 мин дороги.
```

### 7.6. Финансовые команды

```text
/telemed 3500
/parking 450
/food 700
/compensation 1200
/expense 300 мойка
```

### 7.7. Настройки

```text
/settings
/set_car_cost 17.05
/set_min_hourly 600
/set_home <адрес>
/set_default_start <адрес>
/set_default_finish <адрес>
/set_base_districts Приморский, Выборгский, Калининский
```

---

## 8. Расчёт нового адреса

### 8.1. Входные данные

```text
address
visit_income
current_route
current_start_point
finish_point
car_cost_per_km
avg_speed_7d
avg_service_minutes_7d
completed_visits_count
base_districts
```

### 8.2. Расчёт до добавления

```text
before_route = optimize_route(current_point, accepted_uncompleted_visits, finish_point)
before_km = before_route.total_km
before_drive_minutes = before_route.total_minutes
before_service_minutes = count(uncompleted_visits) * avg_service_minutes_7d
before_total_minutes = before_drive_minutes + before_service_minutes
before_income = sum(income for accepted_uncompleted_visits) + completed_income_today
before_car_cost = before_km * car_cost_per_km
before_net_profit = before_income - before_car_cost - known_expenses_today
before_hourly = before_net_profit / (before_total_minutes / 60)
```

### 8.3. Расчёт после добавления

```text
after_route = optimize_route(current_point, accepted_uncompleted_visits + candidate_visit, finish_point)
after_km = after_route.total_km
after_drive_minutes = after_route.total_minutes
after_service_minutes = count(uncompleted_visits + candidate_visit) * avg_service_minutes_7d
after_total_minutes = after_drive_minutes + after_service_minutes
after_income = before_income + candidate_visit.income
after_car_cost = after_km * car_cost_per_km
after_net_profit = after_income - after_car_cost - known_expenses_today
after_hourly = after_net_profit / (after_total_minutes / 60)
```

### 8.4. Маржинальное влияние

```text
extra_km = after_km - before_km
extra_drive_minutes = after_drive_minutes - before_drive_minutes
extra_total_minutes = extra_drive_minutes + avg_service_minutes_7d
extra_car_cost = extra_km * car_cost_per_km
marginal_profit = candidate_visit.income - extra_car_cost
marginal_hourly = marginal_profit / (extra_total_minutes / 60)
```

### 8.5. Решение

```text
if after_hourly > before_hourly:
    decision = "ОДНОЗНАЧНО ДА"
elif candidate_is_outside_base_zone:
    decision = "ТОЛЬКО СО СПЕЦТАРИФОМ"
elif after_hourly >= min_hourly:
    decision = "МОЖНО БРАТЬ"
else:
    decision = "НЕВЫГОДНО / ТОЛЬКО СО СПЕЦТАРИФОМ"
```

Дополнительное правило:

```text
if candidate_is_outside_base_zone and base_zone_visits_count < 5:
    decision = "ТОЛЬКО СО СПЕЦТАРИФОМ: вне базовой зоны и мало базовых адресов"
```

---

## 9. Расчёт спецтарифа

Если вызов невыгоден, бот должен посчитать минимальный доход по вызову, при котором доходность дня будет не ниже минимальной.

Целевая формула:

```text
required_total_net_profit = min_hourly * (after_total_minutes / 60)
```

```text
required_candidate_income = required_total_net_profit + after_car_cost + known_expenses_today - income_without_candidate
```

```text
required_extra_payment = required_candidate_income - candidate_visit.income
```

Если `required_extra_payment <= 0`, доплата не нужна.

Вывод:

```text
Текущий доход по вызову: 2500 ₽
Минимальный доход для рентабельности: 3470 ₽
Минимальная доплата/спецтариф: +970 ₽
```

---

## 10. Формат ответа при добавлении адреса

Бот должен выдавать подробный расчёт.

Пример:

```text
Адрес: Сертолово, ул. ...
Район/локация: вне базовой зоны
Доход по вызову: 2500 ₽

Маршрут без адреса:
- 4 адреса
- 38.2 км
- 1 ч 34 мин дороги
- прогноз доходности: 710 ₽/час

Маршрут с адресом:
- 5 адресов
- 62.7 км
- 2 ч 19 мин дороги
- добавится: +24.5 км и +45 мин дороги

Расход машины:
- 24.5 км × 17.05 ₽/км = 417.73 ₽

Время:
- дорога дополнительно: 45 мин
- среднее время на адресе: 20 мин
- итого добавочное время: 1 ч 05 мин

Маржинально по адресу:
- доход: 2500 ₽
- расход машины: 418 ₽
- маржинальная прибыль: 2082 ₽
- маржинальная доходность: 1922 ₽/час

Влияние на день:
- было: 710 ₽/час
- станет: 760 ₽/час

Решение: ОДНОЗНАЧНО ДА.
Причина: добавление адреса повышает среднюю доходность за час.

Новый оптимальный порядок:
1. Адрес A
2. Адрес C
3. Сертолово, ул. ...
4. Адрес B
5. Адрес D
Финиш: Дом
```

Если адрес вне зоны:

```text
ВНИМАНИЕ: адрес вне базовой зоны.
Рекомендация: требовать спецтариф.
```

Если невыгодно:

```text
Решение: НЕВЫГОДНО.
Минимальный спецтариф для рентабельности: 3470 ₽.
Нужна доплата: +970 ₽.
```

---

## 11. Готовая фраза для клиники

Бот должен генерировать короткую фразу, которую можно скопировать и отправить диспетчеру/клинике.

Команда:

```text
/phrase
```

Или автоматически в расчёте.

Пример для невыгодного адреса:

```text
Адрес вне моей базовой зоны. По расчёту добавляется 24.5 км и около 1 ч 05 мин рабочего времени. При текущем тарифе расчётная доходность составляет 420 ₽/час, что ниже моего минимального порога 600 ₽/час. Могу взять адрес только при спецтарифе не ниже 3470 ₽ или доплате +970 ₽.
```

Пример для спорного адреса:

```text
Адрес вне базовой зоны, а базовых адресов сегодня пока меньше 5. Чтобы не снижать эффективность маршрута, могу взять только при согласовании спецтарифа.
```

Пример для выгодного адреса:

```text
Адрес можно добавить в маршрут. После оптимизации он не снижает доходность дня за час.
```

---

## 12. Модель данных SQLite

### 12.1. Таблица `settings`

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

Ключи:

```text
home_address
home_lat
home_lon
default_start_address
default_start_lat
default_start_lon
default_finish_address
default_finish_lat
default_finish_lon
car_cost_per_km
min_hourly_income
base_districts
default_avg_speed_kmh
default_service_minutes
```

### 12.2. Таблица `work_days`

```sql
CREATE TABLE work_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    start_address TEXT,
    start_lat REAL,
    start_lon REAL,
    finish_address TEXT,
    finish_lat REAL,
    finish_lon REAL,
    started_at TEXT,
    ended_at TEXT,
    planned_avg_speed_kmh REAL,
    planned_service_minutes REAL,
    actual_km REAL,
    actual_avg_speed_kmh REAL,
    actual_service_minutes_per_visit REAL,
    telemed_income REAL DEFAULT 0,
    parking_expenses REAL DEFAULT 0,
    food_expenses REAL DEFAULT 0,
    clinic_compensation REAL DEFAULT 0,
    other_expenses REAL DEFAULT 0,
    created_at TEXT NOT NULL
);
```

### 12.3. Таблица `visits`

```sql
CREATE TABLE visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    order_number INTEGER,
    address TEXT NOT NULL,
    normalized_address TEXT,
    district TEXT,
    is_base_district INTEGER DEFAULT 0,
    lat REAL,
    lon REAL,
    income REAL NOT NULL,
    estimated_extra_km REAL,
    estimated_extra_minutes REAL,
    estimated_marginal_profit REAL,
    estimated_marginal_hourly REAL,
    estimated_day_hourly_before REAL,
    estimated_day_hourly_after REAL,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);
```

### 12.4. Таблица `expenses`

```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);
```

### 12.5. Таблица `address_cache`

```sql
CREATE TABLE address_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_text TEXT NOT NULL UNIQUE,
    normalized_address TEXT,
    district TEXT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    confidence REAL,
    source TEXT,
    created_at TEXT NOT NULL
);
```

### 12.6. Таблица `daily_stats`

```sql
CREATE TABLE daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_day_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    completed_visits_count INTEGER,
    total_income REAL,
    total_expenses REAL,
    net_profit REAL,
    total_work_minutes REAL,
    total_route_minutes REAL,
    total_service_minutes REAL,
    net_hourly_income REAL,
    actual_km REAL,
    actual_avg_speed_kmh REAL,
    actual_service_minutes_per_visit REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(work_day_id) REFERENCES work_days(id)
);
```

---

## 13. Конфигурационный файл

Создать `config.yaml`:

```yaml
bot:
  timezone: "Europe/Moscow"
  language: "ru"

finance:
  min_hourly_income: 600
  currency: "RUB"

car:
  car_cost_per_km: 17.05

defaults:
  avg_speed_kmh: 30
  service_minutes: 20

route:
  always_return_to_finish: true
  optimize_after_each_accept: true

geo:
  default_city: "Санкт-Петербург"
  default_region: "Ленинградская область"
  base_districts:
    - "Приморский"
    - "Выборгский"
    - "Калининский"
```

Секреты не хранить в `config.yaml`. Для Telegram-токена использовать `.env`:

```text
TELEGRAM_BOT_TOKEN=...
```

---

## 14. Структура проекта

```text
home_visit_profit_bot/
  app/
    main.py
    config.py
    db.py
    models.py
    repositories.py
    telegram_bot/
      handlers.py
      conversations.py
      keyboards.py
      messages.py
    services/
      geocoding_service.py
      routing_service.py
      optimization_service.py
      profitability_service.py
      stats_service.py
      phrase_service.py
    utils/
      time_utils.py
      money_utils.py
      text_utils.py
  migrations/
  tests/
    test_profitability.py
    test_route_optimization.py
    test_daily_stats.py
  config.yaml
  .env.example
  requirements.txt
  README.md
```

---

## 15. Сервисная логика

### 15.1. `geocoding_service.py`

Функции:

```python
def geocode_address(input_text: str) -> GeocodingResult:
    ...
```

```python
def detect_district(lat: float, lon: float) -> str:
    ...
```

```python
def is_base_district(district: str, base_districts: list[str]) -> bool:
    ...
```

### 15.2. `routing_service.py`

Функции:

```python
def get_route(from_point: Point, to_point: Point) -> RouteResult:
    ...
```

```python
def get_distance_matrix(points: list[Point]) -> DistanceMatrix:
    ...
```

### 15.3. `optimization_service.py`

Функции:

```python
def optimize_route(
    start: Point,
    visits: list[Visit],
    finish: Point,
    matrix: DistanceMatrix,
) -> OptimizedRoute:
    ...
```

Требование:

- завершённые адреса не включать в оптимизацию;
- если текущий адрес завершён, стартовой точкой для будущего маршрута становится координата завершённого адреса;
- если завершённых адресов нет, стартовая точка — `start_point` рабочего дня.

### 15.4. `profitability_service.py`

Функции:

```python
def calculate_candidate_impact(day_id: int, candidate_visit: Visit) -> CandidateCalculation:
    ...
```

```python
def calculate_required_extra_payment(candidate_calculation: CandidateCalculation) -> RequiredTariff:
    ...
```

```python
def make_decision(candidate_calculation: CandidateCalculation) -> Decision:
    ...
```

### 15.5. `stats_service.py`

Функции:

```python
def finalize_day(day_id: int, actual_data: EndDayData) -> DailyStats:
    ...
```

```python
def calculate_rolling_averages(days: int = 7) -> RollingAverages:
    ...
```

---

## 16. Пошаговый сценарий работы

### 16.1. Утро

Пользователь:

```text
/newday
```

Бот:

```text
Начинаем новый рабочий день.
Стартовая точка сегодня: Дом?
```

Пользователь:

```text
Да
```

Бот:

```text
Финишная точка сегодня: Дом?
```

Пользователь:

```text
Да
```

Бот:

```text
Использую среднюю скорость за 7 дней: 31 км/ч.
Использую среднее время на адресе за 7 дней: 22 мин.
Минимальная доходность: 600 ₽/час.
```

### 16.2. Добавление адреса

Пользователь:

```text
/add Санкт-Петербург, проспект Просвещения 30 | 2500
```

Бот:

```text
Адрес найден. Район: Выборгский. Это базовая зона.
Считаю влияние на маршрут...
```

Далее бот выводит подробный расчёт и кнопки.

### 16.3. Принятие адреса

Пользователь:

```text
/accept
```

Бот:

```text
Адрес принят.
Маршрут оптимизирован:
1. ...
2. ...
3. ...
Финиш: Дом
```

### 16.4. Завершение адреса

Пользователь:

```text
/done 1
```

Бот:

```text
Адрес №1 завершён.
Следующий адрес: №2, ...
До него: 17 минут, 6.8 км.
```

### 16.5. Завершение дня

Пользователь:

```text
/endday
```

Бот задаёт вопросы и после ответов выдаёт:

```text
Итог дня:
Адресов завершено: 7
Выручка по вызовам: 17 500 ₽
Телемедицина: 3 000 ₽
Компенсации: 1 200 ₽
Расходы машины: 1 705 ₽
Парковки: 450 ₽
Еда: 700 ₽
Прочие расходы: 0 ₽

Чистая прибыль: 18 845 ₽
Время работы: 9 ч 20 мин
Чистый доход/час: 2019 ₽/час

Фактическая средняя скорость: 29 км/ч
Фактическое среднее время на адресе: 24 мин
Новое среднее за 7 дней:
- скорость: 30 км/ч
- время на адресе: 22 мин
```

---

## 17. Валидация данных

Бот должен проверять:

- доход по вызову > 0;
- километры >= 0;
- скорость > 0;
- количество завершённых адресов >= 0;
- время окончания дня позже времени начала;
- адрес успешно геокодирован;
- нельзя завершить адрес, которого нет;
- нельзя завершить уже завершённый адрес;
- нельзя принять адрес, если нет активного рабочего дня;
- нельзя завершить день без активного рабочего дня.

---

## 18. Обработка ошибок

Примеры сообщений:

```text
Не смог однозначно найти адрес. Уточните корпус/город/район.
```

```text
Сейчас нет активного рабочего дня. Сначала выполните /newday.
```

```text
Адрес №3 уже завершён.
```

```text
Не удалось получить маршрут. Попробуйте позже или введите километраж вручную.
```

```text
Данные конца дня противоречивы: при указанной скорости дорога занимает больше времени, чем весь рабочий день.
```

---

## 19. Минимальная MVP-версия

MVP должен включать:

1. Telegram-бота.
2. Команды:
   - `/newday`
   - `/add`
   - `/accept`
   - `/reject`
   - `/done`
   - `/route`
   - `/endday`
   - `/summary`
   - `/settings`
3. SQLite-базу.
4. Хранение адресов без персональных данных пациентов.
5. Геокодинг адресов.
6. Расчёт маршрута.
7. Оптимизацию порядка незавершённых адресов.
8. Расчёт доходности за час.
9. Автоматическую пометку адресов вне базовых районов.
10. Расчёт спецтарифа.
11. Пошаговое завершение дня.
12. Скользящую среднюю скорости и времени на адресе за 7 дней.
13. Генерацию фразы для клиники.

---

## 20. Что можно добавить позже

### 20.1. Экспорт отчётов

Команды:

```text
/export_csv
/export_month
```

### 20.2. Аналитика по районам

Показывать:

- средний доход/час по району;
- средний километраж по району;
- среднюю маржинальность;
- какие районы чаще всего требуют спецтариф.

### 20.3. Чёрный и белый список районов

```text
/blacklist_add Всеволожск
/special_tariff_zone_add Сертолово
```

### 20.4. Шаблоны клиник

Позже можно добавить клиники как справочник, но не делать это обязательным в MVP.

```text
/clinic_add Клиника1 default_income=2500 compensation=false
```

### 20.5. Ручной режим без карт

Если routing API недоступен, бот должен позволять вручную ввести километры и минуты.

```text
/manual_route 24.5 45
```

---

## 21. Тестовые сценарии

### 21.1. Адрес в базовой зоне повышает доходность

Ожидаемый результат:

```text
Решение: ОДНОЗНАЧНО ДА
```

### 21.2. Адрес вне базовой зоны при количестве базовых адресов < 5

Ожидаемый результат:

```text
ТОЛЬКО СО СПЕЦТАРИФОМ
```

### 21.3. Адрес вне базовой зоны, но повышает доходность

Ожидаемый результат:

```text
ОДНОЗНАЧНО ДА по экономике, но адрес вне базовой зоны. Рекомендация: всё равно требовать спецтариф или подтверждение условий.
```

### 21.4. День завершён с фактическими данными

Ожидаемый результат:

- рассчитан итог дня;
- обновлена скользящая средняя скорости;
- обновлена скользящая средняя времени на адресе.

### 21.5. Ошибка фактических данных

Если пользователь ввёл:

```text
50 км, 10 км/ч, рабочий день 2 часа
```

Дорога занимает 5 часов, что невозможно. Бот должен попросить перепроверить данные.

---

## 22. Критерии готовности

Проект считается готовым, если:

1. Пользователь может начать день через Telegram.
2. Пользователь может добавить адрес и доход.
3. Бот геокодирует адрес.
4. Бот определяет, в базовой зоне адрес или нет.
5. Бот строит маршрут с обязательным возвращением домой/к финальной точке.
6. Бот оптимизирует порядок адресов после каждого принятия.
7. Бот выдаёт подробный расчёт влияния нового адреса.
8. Бот считает доходность за час до и после добавления адреса.
9. Бот считает минимальный спецтариф/доплату.
10. Бот генерирует готовую фразу для клиники.
11. Пользователь может завершать адреса по порядковому номеру.
12. Пользователь может завершить день и внести фактические данные.
13. Бот обновляет скользящую среднюю за 7 дней.
14. Бот не хранит персональные медицинские данные пациентов.
15. Все ключевые формулы покрыты unit-тестами.

---

## 23. Справочные технологии и официальные источники

Эти источники использовать как техническую основу при реализации:

- python-telegram-bot documentation: https://docs.python-telegram-bot.org/
- OSRM API documentation: https://project-osrm.org/docs/
- OSRM Table Service documentation: https://github.com/Project-OSRM/osrm-backend/blob/master/docs/http.md
- OR-Tools Vehicle Routing documentation: https://developers.google.com/optimization/routing
- OR-Tools Vehicle Routing Problem: https://developers.google.com/optimization/routing/vrp
- Nominatim: https://nominatim.org/
- Nominatim Usage Policy: https://operations.osmfoundation.org/policies/nominatim/

---

## 24. Главный принцип реализации

Бот должен быть не «картой» и не «калькулятором километров», а инструментом экономического решения.

Правильный вопрос, на который отвечает бот:

```text
Если я добавлю этот адрес в сегодняшний маршрут, сколько я реально заработаю за час и не ухудшит ли он день?
```

Если адрес снижает эффективность — бот должен спокойно и жёстко предложить спецтариф. Без эмоций, без споров, только математика.
