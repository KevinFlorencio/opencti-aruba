# Deployment

Tested on Proxmox VE 9.x with a Debian 13 cloud-init template. The whole stack runs in one VM; MISP is a second Compose project on the same host.

## 1. Proxmox guest

Assumes a Debian 13 cloud-init template with `qemu-guest-agent` installed (see the `proxmox` skill's template section). Sizing:

| Resource | Value | Why |
|---|---|---|
| vCPU | 8 | Elasticsearch + OpenCTI + MISP burst |
| RAM | 20 GB | 6 GB ES heap, 6 GB Node heap, MISP/MariaDB |
| Disk | 100 GB | Images ≈ 7 GB, feeds and indexes grow |
| Bridge | `vmbr0` | Same L2 as the LAN |

```bash
qm clone 9000 124 --name opencti-aruba --full --storage hdd
qm set 124 --cores 8 --memory 20480 --balloon 0 \
  --ipconfig0 ip=192.168.0.180/24,gw=192.168.0.1 --nameserver 1.1.1.1 --ciuser styx
qm resize 124 scsi0 100G
qm start 124
```

> **Raw disk resize quirk.** `qm resize` exits 0 but may leave `size=3G` in the config when the underlying raw file is already the target size. Confirm with `qm config 124 | grep scsi0` and, if needed, rewrite it:
> `qm set 124 --scsi0 hdd:124/vm-124-disk-0.raw,discard=on,ssd=1,size=100G`

> **Storage warning.** The lab VM disk lives on a USB-attached HDD. That is acceptable for a demo but not for production: USB bridges drop under sustained database I/O. Move the VM to NVMe before enabling large feeds. See `docs/RUNBOOK.md` for the recovery procedure.

Get the address from the guest agent:

```bash
qm guest cmd 124 network-get-interfaces | jq -r \
  '.[] | .["ip-addresses"][]? | select(."ip-address-type"=="ipv4") | ."ip-address"' | grep -v 127
```

## 2. Base packages and Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git jq python3-venv unzip htop tmux
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
# log out and back in, or use `newgrp docker`
docker --version && docker compose version
```

Docker's install script configures the official repository, so upgrades come through `apt`.

## 3. OpenCTI stack

```bash
git clone https://github.com/KevinFlorencio/opencti-aruba.git ~/aruba-ti
cd ~/aruba-ti
./scripts/gen-env.sh          # writes .env with fresh secrets, prints the admin password
```

Edit `.env` if the VM IP is not `192.168.0.180`:

```dotenv
OPENCTI_BASE_URL=https://<VM_IP>:8443
```

Start:

```bash
docker compose up -d
docker compose ps
```

First start pulls ~6 GB of images and takes 3–8 minutes on a spinning disk. OpenCTI is healthy when:

```bash
curl -sk "https://<VM_IP>:8443/health?health_access_key=$(grep ^OPENCTI_HEALTHCHECK_ACCESS_KEY .env | cut -d= -f2)"
```

### What starts

- `redis`, `elasticsearch`, `minio`, `rabbitmq` — dependencies
- `opencti` + 2 `worker` replicas
- connectors: `mitre`, `mitre-atlas`, `cisa-kev`, `opencti` datasets, `misp`, `import-document`, `export-stix`
- `caddy` — serves `site/dist` on :80 and proxies OpenCTI on :8443

The MISP connector will restart until MISP exists and `MISP_API_KEY` is set. That is expected.

## 4. MISP

```bash
cd ~/aruba-ti
./scripts/gen-misp-env.sh
cd misp
docker compose up -d
docker compose logs -f misp-core    # first boot: schema install, several minutes
```

The script:

- generates `misp/.env` with database, Redis, encryption, salt and admin secrets;
- creates a self-signed certificate for `<VM_IP>` in `misp/ssl/`;
- writes the same automation key into `misp/.env` (`ADMIN_KEY`) and the OpenCTI `.env` (`MISP_API_KEY`).

Then restart the connector so it picks up the key:

```bash
cd ~/aruba-ti
docker compose up -d --force-recreate connector-misp
docker compose logs -f connector-misp
```

Verify the API:

```bash
KEY=$(grep ^MISP_API_KEY .env | cut -d= -f2)
curl -sk -H "Authorization: $KEY" https://127.0.0.1:9443/servers/getVersion
```

MISP UI: `https://<VM_IP>:9443` — `admin@aruba-ti.local` and the password printed by `gen-misp-env.sh`.

### Enable public feeds

MISP ships two feeds, both disabled, and neither is URLhaus/Feodo/OpenPhish. Run the helper:

```bash
cd ~/aruba-ti
./scripts/misp_add_feeds.sh
```

It enables CIRCL and Botvrij, adds URLhaus, Feodo Tracker, OpenPhish and ET Compromised IPs, then queues a fetch and cache for every scope. The first cache is the heaviest operation in the whole stack. Run it off-hours and watch disk:

```bash
watch -n5 'df -h /; docker stats --no-stream'
```

OpenCTI's MISP connector imports events from `2025-06-01` onward (`MISP_IMPORT_FROM_DATE`) and, in this deployment, **unpublished** feed events too (`MISP_IMPORT_ONLY_PUBLISHED=false`). Adjust both in `docker-compose.yml` if you want a different window or only published events. Importing every historical event will flood a small VM.

## 5. Site build

The site is static. Build it on the VM (recommended, so the refresh timer can rebuild unattended) or on a workstation and copy `site/dist`.

```bash
sudo apt-get install -y nodejs npm
node -v    # Astro 5 needs >= 18.20.8, 20.3+ or 22+
cd ~/aruba-ti/site
npm install
npm run build
```

Caddy serves `site/dist` read-only. Rebuild after content changes:

```bash
cd ~/aruba-ti/site && npm run build
```

No Caddy reload is needed; it reads from disk.

## 6. Collector and refresh timer

```bash
sudo cp ~/aruba-ti/deploy/systemd/aruba-radar-refresh.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aruba-radar-refresh.timer
systemctl list-timers aruba-radar-refresh.timer
```

The service runs `scripts/refresh.sh`, which:

1. loads `.env`;
2. runs `collect_radar.py` against OpenCTI and MISP;
3. rebuilds the Astro site;
4. leaves the new `dist` in place for Caddy.

Run it once by hand to verify:

```bash
sudo systemctl start aruba-radar-refresh.service
journalctl -u aruba-radar-refresh -n 50 --no-pager
```

## 7. DNS and TLS

### LAN only

Nothing to do. Caddy uses its internal CA for `https://<VM_IP>:8443`. Browsers warn until you trust the root certificate:

```bash
docker compose exec caddy cat /data/caddy/pki/authorities/local/root.crt > aruba-radar-ca.crt
```

Import that file into your OS/browser trust store. It is a local CA; do not distribute it as a public trust anchor.

### Public domain

1. Point an `A`/`AAAA` record at the public address (or a tunnel).
2. Change the Caddyfile site addresses from the IP to the domain.
3. Set `OPENCTI_BASE_URL=https://opencti.example.org` and restart OpenCTI.
4. Open ports 80/443 only. **Never** expose 8443, 9443 or 8080.
5. Prefer a tunnel (Cloudflare Tunnel, Tailscale Funnel) over a port-forward for the OpenCTI host.

Caddy obtains a Let's Encrypt certificate automatically once the domain resolves.

## 8. Verification checklist

```bash
# platform
curl -sk https://<VM_IP>:8443/health?health_access_key=... | jq
# graph
TOKEN=$(grep ^OPENCTI_ADMIN_TOKEN .env | cut -d= -f2)
curl -s -X POST http://127.0.0.1:8080/graphql \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"query":"{ about { version } reportsNumber { total } indicatorsNumber { total } }"}'
# misp
curl -sk -H "Authorization: $MISP_KEY" https://127.0.0.1:9443/servers/getVersion
# site
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/
# snapshot freshness
jq -r '.generated_at, .kpis' site/public/data/latest.json
```

All five should return data or `200`. If the connector list is empty, check `docker compose ps` and the connector logs before touching OpenCTI.
