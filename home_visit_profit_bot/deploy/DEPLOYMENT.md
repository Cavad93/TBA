# Развёртывание backend: сайт вместо IP (домен + HTTPS)

Цель: приложение ходит не на `http://<ip>:8088`, а на `https://<имя>` — сначала на
бесплатное имя, позже на купленный домен. Смена домена не требует пересборки
приложения — меняется только URL в настройках.

## Почему именно так (а не просто «повесить IP»)

- **Android по умолчанию запрещает открытый HTTP.** Работать «правильно» — это HTTPS.
  Сейчас в приложении включён `usesCleartextTraffic="true"` как временный костыль для
  доступа по IP; после перехода на HTTPS его нужно выключить (см. §7).
- **Bearer-ключ по обычному HTTP летит в открытом виде.** HTTPS его шифрует.
- **IP может смениться, домен — нет.** Приложение, привязанное к имени, переживает
  переезд сервера и смену IP.

## Итоговая схема

```
Android-приложение
      │  HTTPS (443), Authorization: Bearer <ключ>
      ▼
   Caddy  ──── автоматический TLS-сертификат Let's Encrypt
      │  HTTP на localhost
      ▼
 Python backend (app.main)  слушает 127.0.0.1:8088, наружу НЕ смотрит
      │
      ▼
   SQLite (data.sqlite3)
```

Ключевая идея: **наружу смотрит только Caddy**, а Python-процесс слушает localhost.
Caddy занимается доменом, HTTPS и продлением сертификата.

---

## Вариант A (рекомендуется): нативно — Caddy + systemd

Подходит для обычного VPS (Ubuntu/Debian). Меньше «магии», проще диагностировать.

### 1. Сервер и код

```bash
sudo adduser --system --group homevisit
sudo mkdir -p /opt/tba && sudo chown homevisit:homevisit /opt/tba
sudo -u homevisit git clone <repo-url> /opt/tba
cd /opt/tba/home_visit_profit_bot

sudo -u homevisit python3.11 -m venv .venv
sudo -u homevisit .venv/bin/pip install -r requirements.txt
```

### 2. Конфигурация (backend слушает только localhost)

```bash
sudo -u homevisit cp deploy/env.production.example .env
# сгенерировать ключ:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# вписать его в .env → LOCATION_API_KEY. Проверить, что LOCATION_API_HOST=127.0.0.1
```

### 3. Backend как служба

```bash
sudo cp deploy/homevisit-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homevisit-api
curl -s http://127.0.0.1:8088/api/health      # {"ok": true, ...}
```

### 4. Бесплатное имя прямо сейчас (DuckDNS)

Пока домена нет, берём бесплатное имя, которое резолвится в ваш IP. На
<https://www.duckdns.org> заведите поддомен, например `tba.duckdns.org`, и укажите
текущий IP сервера. (Аналоги: `<ip>.sslip.io` вообще без регистрации, но DuckDNS
даёт постоянное имя, которое удобно оставить как запасное.)

Откройте порты:

```bash
sudo ufw allow 80,443/tcp
```

### 5. Caddy (автоматический HTTPS)

```bash
# установка Caddy (Debian/Ubuntu) — см. https://caddyserver.com/docs/install
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy

# положить наш конфиг (впишите в него своё имя вместо tba.duckdns.org)
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Проверка снаружи:

```bash
curl -s https://tba.duckdns.org/api/health      # {"ok": true, ...} по HTTPS
```

### 6. Переключить приложение на имя

В приложении → **Настройки** → «URL сервера»: `https://tba.duckdns.org`
(без `:8088` — теперь вход через 443). API-ключ — тот же, что в `.env`.

---

## Вариант B (альтернатива): Docker Compose

Один командный запуск, backend и Caddy в контейнерах.

```bash
cd /opt/tba/home_visit_profit_bot
cp deploy/env.production.example .env      # вписать LOCATION_API_KEY
nano deploy/Caddyfile.docker               # вписать своё имя
cd deploy
docker compose up -d --build
docker compose logs -f caddy               # видно выпуск сертификата
```

SQLite и сертификаты хранятся в именованных томах (`app_data`, `caddy_data`) —
при пересоздании контейнеров данные не теряются. **Не удаляйте `caddy_data`** —
там сертификаты (у Let's Encrypt есть лимиты на перевыпуск).

---

## 7. Когда купите домен

Домен подключается за пару минут и **без пересборки приложения**:

1. У регистратора/DNS создайте A-запись `api.example.com` → IP сервера
   (при наличии IPv6 — ещё и AAAA). Дождитесь распространения DNS
   (`dig api.example.com`).
2. Добавьте домен в конфиг Caddy. Можно оставить и старое имя — сертификат
   выпустится на оба:
   ```
   tba.duckdns.org, api.example.com {
       ...
   }
   ```
   Нативно: `sudo systemctl reload caddy`. Docker: `docker compose restart caddy`.
3. В приложении смените «URL сервера» на `https://api.example.com`.
   Ключ и все данные прежние.

> Совет: можно сразу заводить домен вида `api.example.com` (поддомен под API),
> оставив корень `example.com` под будущий лендинг/сайт.

---

## 8. Усиление безопасности (после перехода на HTTPS)

- **Выключить открытый HTTP в приложении.** В `AndroidManifest.xml` убрать
  `android:usesCleartextTraffic="true"` (или задать `false`) и пересобрать — тогда
  приложение принимает только HTTPS. Делать это стоит, когда все клиенты уже
  переехали на `https://<имя>` и IP-доступ больше не нужен.
- **Firewall:** наружу открыты только 80/443 и SSH. Порт `8088` закрыт (backend и
  так на localhost).
- **Ротация ключа:** при подозрении на утечку — новый `LOCATION_API_KEY` в `.env`,
  `systemctl restart homevisit-api`, и обновить ключ в приложении.
- **Бэкапы:** периодически копировать `data.sqlite3` (можно через существующий
  экспорт JSON из приложения либо `sqlite3 .backup`).

---

## Диагностика

| Симптом | Причина / проверка |
|---|---|
| Caddy не выдаёт сертификат | DNS имени не указывает на сервер, или закрыты 80/443. `dig <имя>`, `sudo ufw status`. |
| `502` от Caddy | backend не запущен/не на 127.0.0.1:8088. `systemctl status homevisit-api`, `curl 127.0.0.1:8088/api/health`. |
| Приложение: «нет связи» | неверный URL (должен быть `https://<имя>` без порта) или ключ; проверьте кнопкой «Проверить связь» в настройках. |
| `401` на запросах | `LOCATION_API_KEY` в `.env` ≠ ключу в приложении. |
| Сертификат «просрочен» после переезда | сохранён ли том `caddy_data` / каталог `/var/lib/caddy`. |
