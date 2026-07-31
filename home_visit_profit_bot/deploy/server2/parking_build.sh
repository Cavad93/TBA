#!/bin/bash
# Достать зоны платной парковки из той же выгрузки OSM, что съел OSRM.
#
# Overpass для этого не годится: он общественный, рассчитан на точечные запросы и на
# выкачивание страны честно отвечает 504. А выгрузка тут всё равно лежит — ради OSRM.
# Один файл, два потребителя.
set -euo pipefail

PBF=/opt/osrm/data/russia.osm.pbf
OUT=/opt/parking/out
WORK=$(mktemp -d /tmp/parking-XXXX)
trap "rm -rf $WORK" EXIT

# tags-filter отбирает объекты, у которых есть ХОТЬ ОДИН из тегов. Само значение
# (fee=yes или fee=no) проверим при разборе: так бесплатную парковку с тегом fee=no
# мы не спутаем с платной.
osmium tags-filter --overwrite -o "$WORK/p.osm.pbf" "$PBF" \
  nwr/amenity=parking \
  w/parking:both:fee \
  w/parking:left:fee \
  w/parking:right:fee

# geojsonseq — по объекту на строку. Читается потоком, в память целиком не лезет.
# --add-unique-id=type_id ОБЯЗАТЕЛЕН: без него osmium export не пишет id вовсе,
# и каждая зона приезжает с osm_id=0. Уникальный ключ в базе — (тип, id), поэтому
# все зоны затирали бы друг друга, и в таблицу попадала бы ровно одна.
osmium export --overwrite --add-unique-id=type_id -f geojsonseq -o "$WORK/p.geojsonseq" "$WORK/p.osm.pbf"

gzip -c "$WORK/p.geojsonseq" > "$OUT/parking.geojsonseq.gz.tmp"
mv "$OUT/parking.geojsonseq.gz.tmp" "$OUT/parking.geojsonseq.gz"
sha256sum "$OUT/parking.geojsonseq.gz" | cut -d" " -f1 > "$OUT/parking.sha256"
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/parking.built_at"

echo "готово: $(du -h "$OUT/parking.geojsonseq.gz" | cut -f1), объектов: $(zcat "$OUT/parking.geojsonseq.gz" | wc -l)"

# --- Улицы для офлайн-геокодинга (Фаза 2) — из ТОЙ ЖЕ выгрузки ------------------
# Экстрактор привязывает улицы к ближайшему нас. пункту и пишет CSV.gz; сервер 1
# заберёт его с :5001 (scripts.update_osm_streets). Нефатально: сбой сборки улиц не
# должен ронять зоны парковки — они на горячем GPS-пути, а улицы лишь подсказка адреса.
if [ -f /opt/osrm/osm_streets_pbf_service.py ]; then
  echo "собираю улицы для геокодинга..."
  python3 /opt/osrm/osm_streets_pbf_service.py "$PBF" "$OUT/osm_streets.csv.tmp.gz" \
    && mv "$OUT/osm_streets.csv.tmp.gz" "$OUT/osm_streets.csv.gz" \
    && sha256sum "$OUT/osm_streets.csv.gz" | cut -d" " -f1 > "$OUT/osm_streets.sha256" \
    && date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/osm_streets.built_at" \
    && echo "улицы: $(du -h "$OUT/osm_streets.csv.gz" | cut -f1)" \
    || echo "warning: улицы не собрались, старый файл (если был) не тронут"
else
  echo "warning: /opt/osrm/osm_streets_pbf_service.py нет — улицы пропущены"
fi

# --- Административные районы РФ (границы, для базовых зон) — из ТОЙ ЖЕ выгрузки ------
# Определяем район адреса по географии, а не по Nominatim (он районы РФ знает плохо).
# Сервер 1 заберёт districts.geojsonseq.gz с :5001 (scripts.update_district_zones).
# Нефатально: сбой сборки районов не должен ронять зоны парковки и улицы.
if [ -f /opt/parking/district_pbf_service.py ]; then
  echo "собираю районы РФ..."
  python3 /opt/parking/district_pbf_service.py "$PBF" "$OUT/districts.geojsonseq.tmp.gz" \
    && mv "$OUT/districts.geojsonseq.tmp.gz" "$OUT/districts.geojsonseq.gz" \
    && sha256sum "$OUT/districts.geojsonseq.gz" | cut -d" " -f1 > "$OUT/districts.sha256" \
    && date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/districts.built_at" \
    && echo "районы: $(zcat "$OUT/districts.geojsonseq.gz" | wc -l)" \
    || echo "warning: районы не собрались, старый файл не тронут"
else
  echo "warning: /opt/parking/district_pbf_service.py нет — районы пропущены"
fi
