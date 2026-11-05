# Runbook

Operational procedures for the Aruba Threat Radar. Everything here assumes the repository is at `~/aruba-ti` on the VM and Compose is used from that directory.

## Daily checks

```bash
cd ~/aruba-ti
docker compose ps
curl -s http://127.0.0.1/ -o /dev/null -w 'radar %{http_code}\n'
curl -sk https://127.0.0.1:8443/ -o /dev/null -w 'opencti %{http_code}\n'
jq -r '.generated_at, (.kpis|tostring)' site/public/data/latest.json
df -h /
```

A healthy deployment:

- every container `Up` (worker ×2);
- radar `200`;
- OpenCTI `200` (or `302` to login);
- `generated_at` less than 7 hours old;
- disk below 80%.

## Service control

```bash
docker compose up -d                     # converge, create missing
docker compose restart opencti           # app only
docker compose up -d --force-recreate connector-misp
docker compose logs -f --tail=100 opencti
docker compose logs -f --tail=100 connector-misp
docker compose down                      # stop, keep volumes
docker compose down -v                   # DESTROY data — never casually
```

MISP is a separate project:

```bash
cd ~/aruba-ti/misp
docker compose ps
docker compose logs -f --tail=100 misp-core
docker compose restart misp-core
```

## Common failures

### OpenCTI container restarts or is unhealthy

```bash
docker compose logs opencti --tail=200 | grep -iE 'error|fatal|elastic|memory'
free -g
df -h /
curl -s http://127.0.0.1:9200/_cluster/health?pretty   # from inside the ES container if not published
```

Usual causes, in order:

1. **Elasticsearch not ready.** OpenCTI waits for the healthcheck, but a slow disk can exceed the start period. Restart the stack; do not delete volumes.
2. **Heap pressure.** `ES_JAVA_OPTS` 6 GB + Node 6 GB on a 20 GB VM is tight during first ingestion. Reduce to 4 GB each if the kernel OOM-kills processes (`dmesg | grep -i oom`).
3. **Disk full.** Elasticsearch enters read-only mode at the flood stage. Free space, then:
   ```bash
   curl -X PUT "localhost:9200/_all/_settings" -H 'Content-Type: application/json' \
     -d '{"index.blocks.read_only_allow_delete": null}'
   ```
4. **Corrupt index after a hard stop.** Restore from backup; do not run `rm -rf` on `esdata` unless you accept losing the graph.

### Connector restart loop

```bash
docker compose logs connector-misp --tail=50
```

- `Connection refused` to `misp-core` → MISP is still booting or its DB is down. Wait, then restart the connector.
- `401` / `Invalid API key` → `MISP_API_KEY` in `.env` does not match `ADMIN_KEY` in `misp/.env`. Regenerate or copy the value, then `docker compose up -d --force-recreate connector-misp`.
- `certificate verify failed` → set `MISP_SSL_VERIFY=false` for the self-signed lab cert (already the default).
- Connector `Restarting (1)` with no useful log → check the image tag exists: `docker manifest inspect opencti/connector-misp:latest`.

### MISP first boot hangs

```bash
docker compose -f ~/aruba-ti/misp/docker-compose.yml logs --tail=100 misp-core
```

- Schema install can take 5–10 minutes on spinning disk. Look for `Starting MISP install`.
- `MySQL connection refused` → wait for the `db` healthcheck; MariaDB initialises the data directory first.
- `BASE_URL` missing → the Compose file requires it (`${BASE_URL:?...}`). Check `misp/.env`.

### Elasticsearch yellow/red

Single-node clusters are always yellow (replicas cannot be allocated). That is expected and OpenCTI is configured with `NUMBER_OF_REPLICAS=0` for its indices. Red means a primary shard is missing:

```bash
docker compose exec elasticsearch curl -s 'localhost:9200/_cluster/allocation/explain?pretty'
```

Check disk watermarks first. Do not delete indices to "fix" red unless you have a snapshot.

### Collector produces an empty snapshot

```bash
cd ~/aruba-ti
set -a; . ./.env; set +a
OPENCTI_TOKEN=$OPENCTI_ADMIN_TOKEN MISP_KEY=$MISP_API_KEY python3 scripts/collect_radar.py --pretty
```

- `401` → token mismatch. The token is `OPENCTI_ADMIN_TOKEN` (a UUID), not the password.
- `GraphQL error: Allowed number of calls ... exceeded` → the collector was edited to make more than two `stixCoreObjectsNumber` calls per request. Split the query.
- All zeros with a healthy platform → nothing has been ingested yet. Check connector logs and MISP event count.

### Site is stale after a content edit

```bash
cd ~/aruba-ti/site && npm run build
```

Caddy serves `dist` directly. Hard-refresh the browser; the snapshot fetch uses a cache-buster, the HTML may be cached by the browser.

### MISP feed cache fills the disk

```bash
du -sh ~/aruba-ti/misp/files ~/aruba-ti/misp/configs 2>/dev/null
docker system df
```

Disable low-value feeds, prune old events (`Administration → Maintenance`), and keep `MISP_IMPORT_FROM_DATE` recent so OpenCTI does not pull history you do not need.

## Backup

### What matters

| Data | Location | Rebuild cost |
|---|---|---|
| OpenCTI graph | `opencti-aruba_esdata` volume | Irreplaceable |
| Files/exports | `opencti-aruba_s3data` | Mostly reproducible |
| MISP events | `mysql_data` + `misp/files` | Re-fetchable, but slow |
| Config/secrets | `.env`, `misp/.env`, `misp/ssl/`, Caddyfile | Must be backed up |
| Site | git | Rebuildable |

### Procedure (volume copy, requires a short stop)

`scripts/backup.sh` implements this and writes to `/mnt/hdd/backups/aruba-ti/` by default.

```bash
sudo ./scripts/backup.sh
```

It stops the stack, tars the OpenCTI volumes and dumps the MISP database, then restarts. Expect 2–10 minutes of downtime depending on volume size. Schedule it at 03:00 and keep 7 daily / 4 weekly copies.

### Restore

```bash
cd ~/aruba-ti
docker compose down
docker volume rm opencti-aruba_esdata opencti-aruba_s3data   # destructive
docker volume create opencti-aruba_esdata
docker volume create opencti-aruba_s3data
tar xzf /mnt/hdd/backups/aruba-ti/opencti-YYYYMMDD.tgz -C /
docker compose up -d
```

For MISP, restore the SQL dump into the `db` container before starting `misp-core`:

```bash
cat backup.sql | docker compose -f misp/docker-compose.yml exec -T db \
  mysql -umisp -p"$MYSQL_PASSWORD" misp
```

Test the restore path once, on a throwaway copy. An untested backup is a rumour.

## Upgrade

### OpenCTI

1. Read the release notes for the target version; major versions require a migration.
2. Back up.
3. Change the image tags for `opencti` and `worker` in `docker-compose.yml`.
4. `docker compose pull && docker compose up -d`.
5. Watch `docker compose logs -f opencti` until the migration finishes.
6. Re-run the collector and check the snapshot.

Connectors track `:latest`; pin them if you need reproducible rebuilds.

### MISP

```bash
cd ~/aruba-ti/misp
docker compose pull
docker compose up -d
docker compose logs -f misp-core
```

MISP runs schema updates on boot. Back up the database first.

### Host

`apt-get update && apt-get upgrade` monthly. Reboot during a maintenance window; the stack comes back via `restart: always`, but the collector timer needs the systemd unit enabled.

## Credential rotation

| Secret | Where | Rotation |
|---|---|---|
| OpenCTI admin password | `.env` → UI | Change in UI, then update `.env` |
| OpenCTI admin token | `.env` → connectors | Create a new token in UI/API, update `.env`, recreate connectors |
| MISP automation key | `misp/.env` + `.env` | Create new key in MISP, update both, recreate connector |
| MISP admin password | `misp/.env` | Change in UI, update `.env` |
| MinIO / RabbitMQ | `.env` | Change both sides together; restart dependent services |

The collector only needs read access. Create a dedicated OpenCTI user/token with a read-only role and use it for `OPENCTI_TOKEN`; keep the admin token for bootstrap only.

## Logs and telemetry

```bash
docker compose logs --since 1h opencti | jq -r 'select(.level=="error") | .message' 2>/dev/null | tail
journalctl -u aruba-radar-refresh --since '24 hours ago'
docker stats --no-stream
```

There is no external telemetry. `APP__TELEMETRY__ENABLED=false` is set deliberately.

## Escalation

This is a single-operator lab. If the host itself is unstable (USB disk errors, PCIe resets), stop the stack before troubleshooting the disk:

```bash
cd ~/aruba-ti && docker compose stop
```

A database that keeps running on a failing USB bridge is how you turn a recoverable outage into a corrupt index.
