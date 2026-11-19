#!/usr/bin/env bash
# Run on the MISP host from the deployment directory: bash scripts/misp_add_correlation_feeds.sh
# Cache only; do not import as events or distribute indicator data.
set -euo pipefail
set -a
. ./.env
set +a
: "${MISP_API_KEY:?Missing MISP_API_KEY}"
base=${1:-https://127.0.0.1:9443}
cache_failed=0
# The existing local MISP listener uses an internal certificate.
case "$base" in https://127.0.0.1:9443|https://localhost:9443) tls=(-k);; *) tls=();; esac
api() {
  printf 'Authorization: %s\n' "$MISP_API_KEY" | curl -fsS "${tls[@]}" --max-time 30 -H @- -H 'Accept: application/json' "$@"
}
add() {
  local name=$1 provider=$2 url=$3 format=$4 settings=$5 id payload
  id=$(api "$base/feeds/index.json" | jq -er --arg url "$url" '[.[] | (.Feed // .) | select(.url == $url)] | if length > 1 then error("duplicate feed URLs") else .[0].id // "" end')
  if [[ -z $id ]]; then
    payload=$(jq -cn --arg name "$name" --arg provider "$provider" --arg url "$url" --arg format "$format" --argjson settings "$settings" '{Feed:{name:$name,provider:$provider,url:$url,source_format:$format,input_source:"network",enabled:false,caching_enabled:true,lookup_visible:true,distribution:0,sharing_group_id:0,tag_id:0,fixed_event:false,delta_merge:false,event_id:0,publish:false,override_ids:false,settings:$settings,rules:[]}}')
    id=$(api -H 'Content-Type: application/json' -X POST -d "$payload" "$base/feeds/add" | jq -er '.Feed.id // .id')
  fi
  [[ $id =~ ^[0-9]+$ ]]
  if api -X POST "$base/feeds/cacheFeeds/$id" | jq -e '.saved == true or .success == true' >/dev/null; then
    printf 'Queued cache: %s (feed %s)\n' "$name" "$id"
  else
    printf 'Configured but could not queue cache: %s (feed %s)\n' "$name" "$id" >&2
    cache_failed=1
  fi
}
add 'CERT Polska Warning List' 'CERT Polska / NASK' 'https://hole.cert.pl/domains/v2/domains.txt' freetext '{}'
add 'abuse.ch SSLBL' 'abuse.ch' 'https://sslbl.abuse.ch/blacklist/sslblacklist.csv' csv '{"csv":{"value":"2","delimiter":","}}'
exit "$cache_failed"
