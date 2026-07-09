# Бэкапы PostgreSQL

Ежедневные зашифрованные бэкапы базы `vizitor` с ротацией и автозапуском.

## Что настроено

- **Скрипт** [pg_backup.sh](pg_backup.sh): `pg_dump | gzip | gpg (AES256)` →
  `/var/backups/vizitor/vizitor-YYYYMMDD-HHMMSS.sql.gz.gpg`.
- **Расписание**: systemd-таймер [pg-backup.timer](pg-backup.timer) — ежедневно 03:30 UTC.
- **Ротация**: файлы старше 14 дней удаляются (`PG_BACKUP_RETENTION_DAYS`).
- **Шифрование**: симметрично, парольная фраза в `/root/.pg_backup_pass` (0600).

## Первичная установка (на сервере, под root)

```bash
apt-get install -y gnupg                 # если ещё нет
# парольная фраза для шифрования бэкапов (сохраните её ОТДЕЛЬНО!)
openssl rand -base64 32 > /root/.pg_backup_pass && chmod 600 /root/.pg_backup_pass

cp /opt/tba/home_visit_profit_bot/deploy/pg-backup.service \
   /opt/tba/home_visit_profit_bot/deploy/pg-backup.timer /etc/systemd/system/
chmod +x /opt/tba/home_visit_profit_bot/deploy/pg_backup.sh \
         /opt/tba/home_visit_profit_bot/deploy/pg_restore.sh
systemctl daemon-reload
systemctl enable --now pg-backup.timer

# первый бэкап прямо сейчас:
systemctl start pg-backup.service
```

> ⚠️ Парольную фразу `/root/.pg_backup_pass` храните **и вне сервера** (в менеджере
> паролей). Без неё зашифрованные бэкапы восстановить нельзя.

## Проверка

```bash
systemctl list-timers pg-backup.timer      # когда следующий запуск
ls -lh /var/backups/vizitor/               # список бэкапов
journalctl -u pg-backup.service -n 20      # логи последнего бэкапа
```

## Восстановление

В отдельную базу (безопасно, рабочую не трогает):

```bash
/opt/tba/home_visit_profit_bot/deploy/pg_restore.sh \
    /var/backups/vizitor/vizitor-ГГГГММДД-ЧЧММСС.sql.gz.gpg vizitor_restore
```

Восстановление **поверх рабочей** базы при аварии:

```bash
systemctl stop homevisit-api
runuser -u postgres -- psql -c "DROP DATABASE vizitor;"
runuser -u postgres -- createdb -O vizitor vizitor
/opt/tba/home_visit_profit_bot/deploy/pg_restore.sh <файл> vizitor
systemctl start homevisit-api
```

## Что улучшить дальше

- **Копия вне сервера** (off-site): периодически копировать `.gpg`-файлы на другой
  хост / в объектное хранилище. Локальные бэкапы не спасут при потере всего сервера.
- Раз в месяц — контрольное восстановление в `vizitor_restore` и сверка.
