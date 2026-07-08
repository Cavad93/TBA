# TBA

Проект Telegram-бота для расчёта рентабельности выездов врача на дом.

Основной код находится в [`home_visit_profit_bot`](home_visit_profit_bot).

## Что внутри

- Python Telegram-бот с SQLite-базой.
- Android-клиент `android_location_client` для отправки GPS-точек.
- GitHub Actions workflow для сборки debug APK.

## Быстрый старт

```bash
cd home_visit_profit_bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

APK собирается во вкладке **Actions** через workflow **Build Android APK**.
