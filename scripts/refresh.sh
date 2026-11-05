#!/usr/bin/env bash
# Refresh the public radar: collect a snapshot from OpenCTI + MISP, then rebuild
# the static site. Intended for cron/systemd; safe to run by hand.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
. ./.env
set +a

export OPENCTI_URL="${OPENCTI_URL:-http://127.0.0.1:8080}"
export OPENCTI_TOKEN="${OPENCTI_ADMIN_TOKEN}"
export MISP_KEY="${MISP_API_KEY}"
export OPENCTI_PUBLIC_URL="${OPENCTI_BASE_URL}"

echo "[refresh] collecting $(date -Is)"
python3 scripts/collect_radar.py

if [ -x site/node_modules/.bin/astro ]; then
  echo "[refresh] building site"
  (cd site && npm run build --silent)
elif command -v npm >/dev/null 2>&1; then
  echo "[refresh] npm present but site dependencies are not installed — updating the served snapshot only" >&2
else
  echo "[refresh] npm not found — updating the served snapshot only" >&2
fi

# The snapshot is fetched at runtime, so it must exist in dist even when a full
# rebuild is skipped. Astro copies public/ into dist on build; this makes the
# no-build path work too.
mkdir -p site/dist/data
cp site/public/data/latest.json site/dist/data/latest.json

echo "[refresh] done $(date -Is)"
