#!/usr/bin/env bash
# Ежедневный зашифрованный бэкап PostgreSQL-базы.
#
# pg_dump (peer-auth как postgres) -> gzip -> gpg (AES256, симметрично).
# Файлы кладутся в каталог только для root (0700), сами бэкапы 0600.
# Старые (старше RETENTION_DAYS) удаляются.
#
# Запускается systemd-таймером pg-backup.timer (см. одноимённые unit-файлы).
set -euo pipefail

DB="${PG_BACKUP_DB:-vizitor}"
BACKUP_DIR="${PG_BACKUP_DIR:-/var/backups/vizitor}"
RETENTION_DAYS="${PG_BACKUP_RETENTION_DAYS:-14}"
PASS_FILE="${PG_BACKUP_PASS_FILE:-/root/.pg_backup_pass}"

if [[ ! -f "$PASS_FILE" ]]; then
    echo "Нет файла с парольной фразой: $PASS_FILE" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

ts="$(date -u +%Y%m%d-%H%M%S)"
out="${BACKUP_DIR}/${DB}-${ts}.sql.gz.gpg"
tmp="${out}.part"

runuser -u postgres -- pg_dump --no-owner --no-privileges "$DB" \
    | gzip -9 \
    | gpg --batch --yes --symmetric --cipher-algo AES256 --passphrase-file "$PASS_FILE" -o "$tmp"

mv "$tmp" "$out"
chmod 600 "$out"

# Ротация по возрасту.
find "$BACKUP_DIR" -maxdepth 1 -name "${DB}-*.sql.gz.gpg" -mtime "+${RETENTION_DAYS}" -delete

echo "backup OK: ${out} ($(du -h "$out" | cut -f1))"
