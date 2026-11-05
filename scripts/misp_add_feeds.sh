#!/usr/bin/env bash
# Enable the default MISP feeds, add the public OSINT set, and queue a fetch +
# cache. Idempotent: existing feeds are left alone, missing ones are added.
#
# Usage: ./scripts/misp_add_feeds.sh
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
. ./.env
set +a

KEY="${MISP_API_KEY:?MISP_API_KEY is not set in .env}"
BASE="${MISP_URL:-https://127.0.0.1:9443}"
AUTH=(-H "Authorization: $KEY" -H "Accept: application/json" -H "Content-Type: application/json")

api() { curl -sk "${AUTH[@]}" "$@"; }

echo "[misp] enabling default feeds"
for id in 1 2; do
  api -X POST -d '{"Feed":{"enabled":true}}' "$BASE/feeds/edit/$id" >/dev/null || true
done

add_feed() {
  local name="$1" provider="$2" url="$3" fmt="$4"
  if api "$BASE/feeds/index.json" | jq -e --arg n "$name" '.[] | select(.Feed.name == $n)' >/dev/null; then
    echo "[misp] exists: $name"
    return
  fi
  echo "[misp] adding: $name"
  api -X POST -d "{\"Feed\":{\"name\":\"$name\",\"provider\":\"$provider\",\"url\":\"$url\",\"source_format\":\"$fmt\",\"input_source\":\"network\",\"enabled\":true,\"distribution\":\"3\",\"sharing_group_id\":\"0\",\"tag_id\":\"0\",\"default\":false,\"fixed_event\":false,\"delta_merge\":false,\"event_id\":\"0\",\"publish\":false,\"override_ids\":false,\"settings\":\"\",\"rules\":\"\"}}" \
    "$BASE/feeds/add" >/dev/null
}

add_feed "abuse.ch URLhaus" "abuse.ch" "https://urlhaus.abuse.ch/downloads/csv_recent/" "csv"
add_feed "abuse.ch Feodo Tracker" "abuse.ch" "https://feodotracker.abuse.ch/downloads/ipblocklist.csv" "csv"
add_feed "OpenPhish" "OpenPhish" "https://openphish.com/feed.txt" "freetext"
add_feed "ET Compromised IPs" "Emerging Threats" "https://rules.emergingthreats.net/blockrules/compromised-ips.txt" "freetext"

echo "[misp] queueing fetch"
api -X POST "$BASE/feeds/fetchFromAllFeeds" >/dev/null
for scope in misp csv freetext; do
  echo "[misp] queueing cache: $scope"
  api -X POST "$BASE/feeds/cacheFeeds/$scope" >/dev/null
done

echo "[misp] done — watch Administration → Jobs in the UI"
