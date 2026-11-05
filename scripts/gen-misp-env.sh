#!/usr/bin/env bash
# Generate misp/.env, a self-signed TLS certificate, and wire the API key into
# the OpenCTI stack. Run once, from the repository root.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f misp/.env ]]; then
  echo "refusing to overwrite existing misp/.env" >&2
  exit 1
fi

rand() { openssl rand -base64 64 | tr -dc 'A-Za-z0-9' | head -c "$1"; }
uuid() { python3 -c 'import uuid; print(uuid.uuid4())'; }
hexkey() { openssl rand -hex 32; }

HOST="${MISP_HOST:-192.168.0.180}"
API_KEY="$(uuid)"
ADMIN_PASS="$(rand 24)"
DB_PASS="$(rand 24)"
DB_ROOT="$(rand 24)"
REDIS_PASS="$(rand 24)"

sed -i "s|^MISP_API_KEY=.*|MISP_API_KEY=${API_KEY}|" .env
sed -i "s|^MISP_URL=.*|MISP_URL=https://${HOST}:9443|" .env

cat > misp/.env <<EOF
COMPOSE_PROJECT_NAME=misp
TZ=America/Aruba
BASE_URL=https://${HOST}:9443
NGINX_HTTP_PORT=9080
NGINX_HTTPS_PORT=9443
CORE_TAG=v2.5.51
MODULES_TAG=v3.1.3
GUARD_TAG=v1.4.1
CORE_RUNNING_TAG=latest
MODULES_RUNNING_TAG=latest
ADMIN_EMAIL=admin@aruba-ti.local
ADMIN_ORG=Aruba Threat Intel
ADMIN_ORG_UUID=$(uuid)
ADMIN_PASSWORD=${ADMIN_PASS}
ADMIN_KEY=${API_KEY}
GPG_PASSPHRASE=${ADMIN_PASS}
ENCRYPTION_KEY=$(hexkey | head -c 32)
SALT=$(hexkey | head -c 32)
UUID=$(uuid)
MYSQL_HOST=db
MYSQL_USER=misp
MYSQL_PASSWORD=${DB_PASS}
MYSQL_ROOT_PASSWORD=${DB_ROOT}
MYSQL_DATABASE=misp
REDIS_HOST=redis
REDIS_PASSWORD=${REDIS_PASS}
ENABLE_REDIS_EMPTY_PASSWORD=false
ENABLE_BACKGROUND_UPDATES=true
INNODB_BUFFER_POOL_SIZE=1024M
NUM_WORKERS_DEFAULT=3
NUM_WORKERS_PRIO=3
NUM_WORKERS_EMAIL=2
NUM_WORKERS_UPDATE=1
NUM_WORKERS_CACHE=3
COMPOSE_PROFILES=
EOF
chmod 600 misp/.env

mkdir -p misp/ssl
if [[ ! -f misp/ssl/cert.pem ]]; then
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout misp/ssl/key.pem -out misp/ssl/cert.pem -days 825 \
    -subj "/CN=misp-aruba" \
    -addext "subjectAltName=IP:${HOST},DNS:misp-nginx,DNS:localhost" >/dev/null 2>&1
  chmod 644 misp/ssl/cert.pem misp/ssl/key.pem
fi

echo "wrote misp/.env and misp/ssl"
echo "MISP admin: admin@aruba-ti.local / ${ADMIN_PASS}"
echo "MISP API key (also set in .env): ${API_KEY}"
