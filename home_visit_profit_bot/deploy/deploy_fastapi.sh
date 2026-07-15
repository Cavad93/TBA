#!/usr/bin/env bash
# Безопасный перевод backend на FastAPI/uvicorn с параллельным прогоном и откатом.
#
# Философия: НЕ переключать боевой трафик вслепую. Сначала поднимаем uvicorn на
# ЗАПАСНОМ порту рядом с работающим старым сервером, гоняем смоук по живой базе, и
# только если всё зелёное — меняем systemd-юнит и перезапускаем службу. Откат — одна
# команда: старый entrypoint (app/main.py) никуда не делся.
#
# Запускать на сервере 1 из /opt/tba/home_visit_profit_bot.
set -euo pipefail

APP_DIR=/opt/tba/home_visit_profit_bot
VENV="$APP_DIR/.venv"
TEST_PORT=8089
HEALTH_URL_MAIN=http://127.0.0.1:8088/api/health
HEALTH_URL_TEST=http://127.0.0.1:${TEST_PORT}/api/health

cd "$APP_DIR"

echo "==> 1. Обновляю зависимости (fastapi, uvicorn, psycopg_pool)"
sudo -u homevisit "$VENV/bin/pip" install -q -r requirements.txt

echo "==> 2. Параллельный прогон: uvicorn на запасном порту ${TEST_PORT} (старый сервер не трогаю)"
sudo -u homevisit env $(grep -v '^#' "$APP_DIR/.env" | xargs) \
    "$VENV/bin/uvicorn" app.asgi:app --host 127.0.0.1 --port "$TEST_PORT" --workers 1 &
UVICORN_PID=$!
trap 'kill "$UVICORN_PID" 2>/dev/null || true' EXIT
sleep 4

echo "==> 3. Смоук по запасному порту"
if ! curl -fsS "$HEALTH_URL_TEST"; then
    echo "ОШИБКА: uvicorn не отвечает на ${HEALTH_URL_TEST}. Переключение отменено."
    exit 1
fi
echo
echo "    health OK на запасном порту."

echo "==> 4. Останавливаю тестовый uvicorn"
kill "$UVICORN_PID" 2>/dev/null || true
trap - EXIT
sleep 1

echo "==> 5. Ставлю новый systemd-юнит (uvicorn на 8088) и перезапускаю службу"
sudo cp "$APP_DIR/deploy/homevisit-api.service" /etc/systemd/system/homevisit-api.service
sudo systemctl daemon-reload
sudo systemctl restart homevisit-api
sleep 3

echo "==> 6. Смоук боевого порта"
if curl -fsS "$HEALTH_URL_MAIN"; then
    echo
    echo "ГОТОВО: backend на FastAPI/uvicorn, /api/health живой."
else
    echo
    echo "ОШИБКА боевого health. ОТКАТ: верните в юните ExecStart на 'python -m app.main',"
    echo "  sudo systemctl daemon-reload && sudo systemctl restart homevisit-api"
    exit 1
fi
