#!/bin/bash
# Замена OSRM-графа сервера 2: 5 округов (russia5) -> ВСЯ РОССИЯ (russia).
#
# Порядок намеренный: сначала полностью забираем новый граф рядом со старым, проверяем
# его, и только потом останавливаем маршрутизатор. Упавший перенос не должен оставить
# сервер без карт — старый граф живёт до последнего момента (тот же принцип, что в
# refresh.sh: устаревшая карта лучше сломанной).
#
# Имя базы меняется russia5 -> russia: файл больше не «5 округов», имя врать не должно.
# Поэтому обновляются и потребители: systemd unit OSRM и parking/build.sh (из PBF
# строятся зоны парковки, улицы геокодинга и районы РФ).
set -euo pipefail

DATA=/opt/osrm/data
NEW=/opt/osrm/incoming
BASE=russia
OLD=russia5
UNIT=/etc/systemd/system/osrm-car.service

echo "=== [1/6] проверяю принятый граф ==="
test -d "$NEW" || { echo "нет каталога $NEW"; exit 1; }
for f in "$NEW/$BASE.osrm.fileIndex" "$NEW/$BASE.osrm.ebg" "$NEW/$BASE.osrm.cell_metrics" "$NEW/$BASE.osm.pbf"; do
  test -s "$f" || { echo "ОТСУТСТВУЕТ или пуст: $f"; exit 1; }
done
NEW_SIZE=$(du -sm "$NEW" | cut -f1)
echo "принято: ${NEW_SIZE} МБ, файлов: $(ls -1 "$NEW" | wc -l)"
# Полная Россия обязана быть КРУПНЕЕ пяти округов — иначе перенос неполный.
OLD_SIZE=$(du -cm "$DATA/$OLD.osrm"* 2>/dev/null | tail -1 | cut -f1 || echo 0)
echo "старый граф: ${OLD_SIZE} МБ"
if [ "$NEW_SIZE" -lt "$OLD_SIZE" ]; then
  echo "ОШИБКА: новый граф меньше старого — перенос неполный, ничего не трогаю"; exit 1
fi

echo "=== [2/6] место на диске ==="
df -h / | tail -1

echo "=== [3/6] останавливаю osrm-car (простой начинается здесь) ==="
systemctl stop osrm-car

echo "=== [4/6] убираю старый граф 5 округов и ставлю новый ==="
mkdir -p /opt/osrm/old
mv "$DATA/$OLD.osrm"* /opt/osrm/old/ 2>/dev/null || true
mv "$DATA/$OLD.osm.pbf" /opt/osrm/old/ 2>/dev/null || true
mv "$NEW/$BASE.osrm"* "$DATA/"
mv "$NEW/$BASE.osm.pbf" "$DATA/"
rmdir "$NEW" 2>/dev/null || true
ls -lah "$DATA" | head -8

echo "=== [5/6] обновляю потребителей (unit + сборка парковки/улиц/районов) ==="
cp -a "$UNIT" "$UNIT.bak-$(date +%Y%m%d-%H%M%S)"
sed -i "s#/data/$OLD#/data/$BASE#g" "$UNIT"
sed -i "s#OSRM (car, MLD) — 5 федеральных округов#OSRM (car, MLD) — вся Россия#" "$UNIT"
grep -E "Description|osrm-routed" "$UNIT"

if [ -f /opt/parking/build.sh ]; then
  cp -a /opt/parking/build.sh "/opt/parking/build.sh.bak-$(date +%Y%m%d-%H%M%S)"
  sed -i "s#PBF=/opt/osrm/data/$OLD.osm.pbf#PBF=/opt/osrm/data/$BASE.osm.pbf#" /opt/parking/build.sh
  grep -m1 "^PBF=" /opt/parking/build.sh
fi

echo "=== [6/6] поднимаю osrm-car на полной России ==="
systemctl daemon-reload
systemctl start osrm-car
sleep 12
systemctl is-active osrm-car
docker ps --format "{{.Names}} {{.Status}}" | grep osrm-car || true
echo "SWAP_DONE"
