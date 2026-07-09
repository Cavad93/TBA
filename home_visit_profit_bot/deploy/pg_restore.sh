#!/usr/bin/env bash
# Восстановление из зашифрованного бэкапа.
#
# Использование:
#   deploy/pg_restore.sh <файл.sql.gz.gpg> [target_db]
#
# По умолчанию восстанавливает в НОВУЮ базу vizitor_restore (безопасно, не трогает
# рабочую). Чтобы восстановить поверх рабочей БД при аварии — укажите её имя явно и
# предварительно очистите (см. DEPLOYMENT/BACKUPS.md).
set -euo pipefail

FILE="${1:?укажите путь к файлу бэкапа}"
TARGET="${2:-vizitor_restore}"
PASS_FILE="${PG_BACKUP_PASS_FILE:-/root/.pg_backup_pass}"

if [[ ! -f "$FILE" ]]; then
    echo "Файл не найден: $FILE" >&2
    exit 1
fi

runuser -u postgres -- createdb "$TARGET" 2>/dev/null || true

gpg --batch --quiet --decrypt --passphrase-file "$PASS_FILE" "$FILE" \
    | gunzip \
    | runuser -u postgres -- psql -v ON_ERROR_STOP=1 -q "$TARGET"

echo "восстановлено в БД: ${TARGET}"
