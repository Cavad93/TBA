#!/bin/bash
# Сборка OSRM-графа (профиль car, схема MLD) для ВСЕЙ РОССИИ на временном сервере.
#
# Зачем временный сервер: на сервере 2 (15 ГБ RAM) osrm-extract полной России не влезает
# — там строились только 5 округов. Здесь 31 ГБ RAM + 16 ядер, extract проходит.
#
# Образ ЗАКРЕПЛЁН ПО DIGEST — ровно тот, что запущен на сервере 2. Разные версии OSRM
# пишут несовместимые графы: собранный чужой версией просто не поднимется в бою.
#
# Имя базы — `russia` (а не `russia5`): файл больше не «5 округов», и имя не должно врать.
# Пути на сервере 2 (systemd unit, parking/build.sh, osm_streets) обновляются отдельно.
set -euo pipefail

DATA=/opt/build/data
BASE=russia
IMAGE=ghcr.io/project-osrm/osrm-backend@sha256:a7091038e39a73659767f34ef2d389909b42ea80b09bd2bdca482dce2991cbad
LOG=/opt/build/build.log

exec > >(tee -a "$LOG") 2>&1
echo "=== старт $(date -u +%H:%M:%S) UTC ==="

if [ ! -f "$DATA/$BASE.osm.pbf" ]; then
  mv "$DATA/russia-latest.osm.pbf" "$DATA/$BASE.osm.pbf"
fi
ls -lah "$DATA/$BASE.osm.pbf"

echo "=== [1/3] osrm-extract (самый тяжёлый шаг) $(date -u +%H:%M:%S) ==="
docker run --rm -v "$DATA":/data "$IMAGE" \
  osrm-extract -p /opt/car.lua "/data/$BASE.osm.pbf"

echo "=== [2/3] osrm-partition $(date -u +%H:%M:%S) ==="
docker run --rm -v "$DATA":/data "$IMAGE" osrm-partition "/data/$BASE"

echo "=== [3/3] osrm-customize $(date -u +%H:%M:%S) ==="
docker run --rm -v "$DATA":/data "$IMAGE" osrm-customize "/data/$BASE"

echo "=== готово $(date -u +%H:%M:%S) UTC ==="
du -ch "$DATA/$BASE.osrm"* | tail -1
echo "BUILD_OK"
