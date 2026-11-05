#!/usr/bin/env bash
# Backup the Aruba Threat Radar: config, MISP database and OpenCTI volumes.
# Stops the OpenCTI stack briefly for a consistent Elasticsearch volume copy.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
. ./.env
set +a

BACKUP_DIR="${BACKUP_DIR:-/mnt/hdd/backups/aruba-ti}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP="$(date +%Y%m%d-%H%M)"
PROJECT="${COMPOSE_PROJECT_NAME:-opencti-aruba}"

mkdir -p "$BACKUP_DIR"
echo "[backup] $BACKUP_DIR/$STAMP"

echo "[backup] configuration"
tar czf "$BACKUP_DIR/config-$STAMP.tgz" \
  .env misp/.env misp/ssl caddy/Caddyfile \
  docker-compose.yml misp/docker-compose.yml \
  2>/dev/null

echo "[backup] MISP database"
docker compose -f misp/docker-compose.yml exec -T db \
  sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --events misp' \
  | gzip > "$BACKUP_DIR/misp-db-$STAMP.sql.gz"

echo "[backup] stopping OpenCTI stack for a consistent volume snapshot"
docker compose stop

echo "[backup] OpenCTI volumes"
for vol in "${PROJECT}_esdata" "${PROJECT}_s3data"; do
  name="${vol#${PROJECT}_}"
  docker run --rm \
    -v "$vol":/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine:3.20 tar czf "/backup/$name-$STAMP.tgz" -C /data .
done

echo "[backup] restarting"
docker compose up -d

echo "[backup] pruning older than $KEEP_DAYS days"
find "$BACKUP_DIR" -maxdepth 1 -type f -mtime "+$KEEP_DAYS" -delete

ls -lh "$BACKUP_DIR"/*"$STAMP"*
echo "[backup] done"
