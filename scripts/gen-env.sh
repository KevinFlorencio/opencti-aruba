#!/usr/bin/env bash
# Generate a .env with fresh secrets. Run once on the deployment host.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  echo "refusing to overwrite existing .env" >&2
  exit 1
fi

rand() { openssl rand -base64 64 | tr -dc 'A-Za-z0-9' | head -c "$1"; }
uuid() { python3 -c 'import uuid; print(uuid.uuid4())'; }
hexkey() { openssl rand -hex 32; }

ADMIN_PASS="$(rand 28)"
MINIO_PASS="$(rand 32)"
RABBIT_PASS="$(rand 32)"

cat > .env <<EOF
COMPOSE_PROJECT_NAME=opencti-aruba
OPENCTI_BASE_URL=https://192.168.0.180:8443
OPENCTI_ADMIN_EMAIL=admin@aruba-ti.local
OPENCTI_ADMIN_PASSWORD=${ADMIN_PASS}
OPENCTI_ADMIN_TOKEN=$(uuid)
OPENCTI_ENCRYPTION_KEY=$(hexkey)
OPENCTI_HEALTHCHECK_ACCESS_KEY=$(uuid)
ELASTIC_MEMORY_SIZE=6G
MINIO_ROOT_USER=opencti
MINIO_ROOT_PASSWORD=${MINIO_PASS}
RABBITMQ_DEFAULT_USER=opencti
RABBITMQ_DEFAULT_PASS=${RABBIT_PASS}
MISP_URL=https://192.168.0.180:9443
MISP_API_KEY=
ALIENVAULT_API_KEY=
ABUSECH_AUTH_KEY=
RANSOMWARELIVE_API_KEY=
SITE_ADDRESS=http://192.168.0.180
EOF

chmod 600 .env

# TLS certificate for the OpenCTI UI on :8443. A long-lived self-signed cert is
# used because Caddy's internal CA issues 12-hour certs and selects them by SNI;
# browsers do not send SNI for IP literals. Replace with a real domain cert when
# publishing.
mkdir -p caddy/certs
if [[ ! -f caddy/certs/opencti.crt ]]; then
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout caddy/certs/opencti.key -out caddy/certs/opencti.crt -days 825 \
    -subj "/CN=aruba-threat-radar" \
    -addext "subjectAltName=IP:192.168.0.180,DNS:opencti.aruba,DNS:localhost" >/dev/null 2>&1
  chmod 644 caddy/certs/opencti.crt caddy/certs/opencti.key
fi

echo "wrote .env"
echo "admin: admin@aruba-ti.local / ${ADMIN_PASS}"
