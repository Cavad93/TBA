#!/bin/bash
# Обновление карты: свежая выгрузка OSM -> графы «пешком»/«велосипед» -> зоны парковки,
# улицы геокодинга и районы РФ. Запускается раз в два месяца из GitHub Actions.
#
# ЧТО ИЗМЕНИЛОСЬ 31.07.2026 (переход на карту ВСЕЙ РОССИИ).
# Раньше здесь собирался и автомобильный граф — из пяти федеральных округов. Теперь
# car-граф покрывает всю страну, и собрать его НА ЭТОМ СЕРВЕРЕ нельзя: osrm-extract
# полной России берёт больше двадцати гигабайт памяти, а тут пятнадцать. Сборка ушла бы
# в своп на много часов или её убил бы OOM — причём уже ПОСЛЕ остановки маршрутизатора.
# Поэтому car-граф собирается отдельно на мощной машине и приезжает сюда готовым, а этот
# скрипт его НЕ ТРОГАЕТ. Честный пропуск с записью в лог лучше тихого падения: устаревшая
# карта лучше сломанной.
#
# Всё остальное обновляется как прежде: пеший и велосипедный графы (только Москва и
# Петербург — они маленькие и сервер их тянет), а также выгрузка, из которой строятся
# зоны платной парковки, улицы для офлайн-геокодинга и границы районов.
#
# Строим в отдельной папке и подменяем готовое одним движением: упавшая сборка не
# заметна работающим маршрутизаторам.
set -euo pipefail

DATA=/opt/osrm/data
NEW=/opt/osrm/new
BASE=russia
IMAGE=ghcr.io/project-osrm/osrm-backend:latest

rm -rf "$NEW"; mkdir -p "$NEW"
trap "rm -rf $NEW" EXIT

echo "[1/5] качаю свежую выгрузку всей России"
curl -sfL --retry 3 -o "$NEW/$BASE.osm.pbf" "https://download.geofabrik.de/russia-latest.osm.pbf"

echo "[2/5] вырезаю Москву и Петербург (пешком и на велосипеде дальше не ездят)"
# osmium ждёт порядок lon,lat — перепутать значит вырезать океан.
osmium extract --overwrite -b 36.95,55.40,37.97,56.05 -o "$NEW/msk.osm.pbf" "$NEW/$BASE.osm.pbf"
osmium extract --overwrite -b 29.55,59.70,30.60,60.10 -o "$NEW/spb.osm.pbf" "$NEW/$BASE.osm.pbf"
osmium merge --overwrite -o "$NEW/cities.osm.pbf" "$NEW/msk.osm.pbf" "$NEW/spb.osm.pbf"
rm -f "$NEW/msk.osm.pbf" "$NEW/spb.osm.pbf"

echo "[3/5] собираю графы: пешком и велосипед (2 города). Car-граф НЕ пересобираю —"
echo "      он на всю Россию и строится на отдельной большой машине (см. шапку скрипта)."
build() {
  local DIR=$1 PROFILE=$2 BASE_NAME=$3
  mkdir -p "$DIR"
  docker run --rm -v "$DIR":/data $IMAGE osrm-extract   -p /opt/$PROFILE.lua "/data/$BASE_NAME.osm.pbf" >/dev/null
  docker run --rm -v "$DIR":/data $IMAGE osrm-partition "/data/$BASE_NAME"                              >/dev/null
  docker run --rm -v "$DIR":/data $IMAGE osrm-customize "/data/$BASE_NAME"                              >/dev/null
  rm -f "$DIR/$BASE_NAME.osm.pbf"
}
mkdir -p "$NEW/foot" "$NEW/bicycle"
cp "$NEW/cities.osm.pbf" "$NEW/foot/cities.osm.pbf"
cp "$NEW/cities.osm.pbf" "$NEW/bicycle/cities.osm.pbf"
build "$NEW/foot"    foot    cities
build "$NEW/bicycle" bicycle cities

echo "[4/5] подменяю пеший и велосипедный графы и свежую выгрузку"
# Автомобильный маршрутизатор не останавливаем вовсе — его граф не меняется.
systemctl stop osrm-foot osrm-bike

rm -rf /opt/osrm/foot.old /opt/osrm/bicycle.old
mv /opt/osrm/foot /opt/osrm/foot.old
mv /opt/osrm/bicycle /opt/osrm/bicycle.old
mv "$NEW/foot" /opt/osrm/foot
mv "$NEW/bicycle" /opt/osrm/bicycle

# Выгрузка нужна фабрикам парковки/улиц/районов. Граф car остаётся от прежней сборки —
# это нормально: граф и выгрузка независимы, у графа свой цикл обновления.
rm -f "$DATA/$BASE.osm.pbf" "$DATA/cities.osm.pbf"
mv "$NEW/$BASE.osm.pbf" "$DATA/$BASE.osm.pbf"
mv "$NEW/cities.osm.pbf" "$DATA/cities.osm.pbf"

systemctl start osrm-foot osrm-bike
rm -rf /opt/osrm/foot.old /opt/osrm/bicycle.old

echo "[5/5] зоны парковки, улицы и районы — из ТОЙ ЖЕ свежей выгрузки"
/opt/parking/build.sh

echo "карта обновлена: $(date -u +%Y-%m-%d\ %H:%M) UTC"
echo "ВНИМАНИЕ: автомобильный граф (вся Россия) не пересобирался — обновляется отдельно"
echo "на мощной машине, см. шапку скрипта. Текущий car-граф: $(ls -1 $DATA/$BASE.osrm.fileIndex 2>/dev/null && stat -c %y $DATA/$BASE.osrm.fileIndex 2>/dev/null || echo 'не найден')"
