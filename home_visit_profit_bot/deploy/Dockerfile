# Образ backend REST API. Собирается из корня home_visit_profit_bot/.
FROM python:3.11-slim

WORKDIR /app

# Сначала зависимости — лучше кэшируется.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# В контейнере слушаем все интерфейсы: наружу порт не публикуется,
# доступ к нему есть только у Caddy внутри compose-сети.
ENV LOCATION_API_ENABLED=true \
    LOCATION_API_HOST=0.0.0.0 \
    LOCATION_API_PORT=8088 \
    DATABASE_PATH=/data/data.sqlite3

EXPOSE 8088
CMD ["python", "-m", "app.main"]
