# MISP

MISP is the ingestion and normalisation layer. OpenCTI is the knowledge graph. The official MISP connector moves published events between them.

## First boot

```bash
cd ~/aruba-ti
./scripts/gen-misp-env.sh
cd misp
docker compose up -d
docker compose logs -f misp-core
```

First boot installs the schema, creates the admin user and the automation key. On a spinning disk this takes 5–15 minutes. The stack is ready when `misp-core` is healthy and `https://<VM_IP>:9443` returns the login page.

The script prints:

- admin email (`admin@aruba-ti.local`)
- admin password
- automation key (also written to the OpenCTI `.env` as `MISP_API_KEY`)

The self-signed certificate in `misp/ssl/` has a SAN for the VM IP and `misp-nginx`.

## API key

The key is `ADMIN_KEY` in `misp/.env`. Verify it:

```bash
KEY=$(grep ^MISP_API_KEY ~/aruba-ti/.env | cut -d= -f2)
curl -sk -H "Authorization: $KEY" https://127.0.0.1:9443/servers/getVersion
```

If the connector reports `401`, the two values have diverged. Copy one to the other and recreate the connector:

```bash
cd ~/aruba-ti
docker compose up -d --force-recreate connector-misp
docker compose logs -f connector-misp
```

For production, create a dedicated sync user with the minimum role and use its key instead of the admin key.

## Enabling feeds

UI: `Sync Actions → List Feeds`. Enable the public OSINT set, then fetch and cache.

API:

```bash
KEY=$(grep ^MISP_API_KEY ~/aruba-ti/.env | cut -d= -f2)
BASE=https://127.0.0.1:9443

# list feeds with their ids and enabled flag
curl -sk -H "Authorization: $KEY" $BASE/feeds/index | jq -r '.[] | [.id,.enabled,.name] | @tsv' | head -40

# enable by id (repeat)
curl -sk -X POST -H "Authorization: $KEY" -H 'Content-Type: application/json' \
  -d '{"enabled":true}' $BASE/feeds/edit/<id>

# fetch metadata for all feeds, then download events
curl -sk -X POST -H "Authorization: $KEY" $BASE/feeds/fetchFromAllFeeds
curl -sk -X POST -H "Authorization: $KEY" $BASE/feeds/cacheAllFeeds
```

The first cache is heavy. Watch disk and MISP jobs (`Administration → Jobs`). Do not enable every feed in the catalogue; each one adds parsing load and false positives.

Recommended set:

- CIRCL OSINT
- abuse.ch Feodo Tracker
- Botvrij.eu
- OpenPhish

## OpenCTI connector settings

In `docker-compose.yml`:

```yaml
connector-misp:
  environment:
    MISP_URL: ${MISP_URL}              # https://<VM_IP>:9443
    MISP_KEY: ${MISP_API_KEY}
    MISP_SSL_VERIFY: "false"           # self-signed lab cert
    MISP_CREATE_REPORTS: "true"
    MISP_CREATE_INDICATORS: "true"
    MISP_CREATE_OBSERVABLES: "true"
    MISP_CREATE_OBJECT_OBSERVABLES: "true"
    MISP_REPORT_TYPE: misp-event
    MISP_IMPORT_FROM_DATE: "2025-06-01"
    MISP_IMPORT_DISTRIBUTION_LEVELS: "0,1,2,3"
    MISP_IMPORT_THREAT_LEVELS: "1,2,3,4"
    MISP_IMPORT_ONLY_PUBLISHED: "true"
    MISP_ENFORCE_WARNING_LIST: "true"
```

Notes:

- `MISP_IMPORT_FROM_DATE` is the main volume control. Importing a decade of history will flood a small VM.
- `MISP_ENFORCE_WARNING_LIST=true` drops attributes matching known false-positive infrastructure.
- `MISP_IMPORT_TAGS` / `MISP_IMPORT_TAGS_NOT` let you include or exclude by tag (e.g. only `tlp:white`).
- The connector runs every 15 minutes (`CONNECTOR_DURATION_PERIOD: PT15M`).

## What the connector creates

| MISP | OpenCTI |
|---|---|
| Event | Report (`misp-event`) |
| Attribute / object | Indicator + Observable |
| Tag | Label |
| Galaxy cluster | Malware, Threat Actor, Attack Pattern, Tool (when mapped) |
| Org / sharing group | Identity (creator) |
| TLP tag | Marking definition |

The report's confidence is derived from the MISP threat level via `MISP_THREAT_LEVEL_SCORE_MAPPING`.

## Sharing back

The connector is import-only. To push OpenCTI intelligence back to MISP:

1. Create a MISP **sync user** and a dedicated organisation.
2. Add a MISP server entry in OpenCTI (`Data sharing → Sharing`) or use the `misp` export connector if your version ships one.
3. Start with a single report and verify the STIX-to-MISP mapping before enabling automatic push.

Most teams do not need bidirectional sync on day one. Import is where the value is.

## Deployment notes and known issues

These bit us on the first build (MISP 2.5.51, single `misp-core` container). They are documented so the next deployment does not lose an evening to them.

**Only two feeds ship with the image.** CIRCL OSINT and Botvrij are present but disabled; Feodo, OpenPhish and ET must be added through `POST /feeds/add`. URLhaus bulk CSV is retired upstream (HTTP 410) and must not be added. The working payload is in the deployment notes of `docs/DEPLOYMENT.md` and in the `add_feed` helper used to build this instance.

**nginx never starts if the healthcheck probes IPv4.** The image's healthcheck runs `echo > /dev/tcp/127.0.0.1/9002`, but php-fpm listens on `[::]:9002`. The check fails forever and `misp-nginx` waits on `service_healthy`. The compose file in this repository replaces the probe with a php-fpm process check. If you use the upstream compose unchanged, start nginx manually once (`docker start misp-misp-nginx-1`) or patch the healthcheck.

**Redis session handler returns HTTP 500.** The image writes `session.save_handler = redis` and `session.save_path = 'tcp://redis:6379?auth=...'` into `php.ini`. On this phpredis build the session handler rejects that query-string auth form, so every request that touches a session dies with `session_start(): Redis connection not available`. `misp/php-session.ini` overrides the handler to `files`; it is mounted into `conf.d` by the compose file. One `misp-core` container does not need shared sessions.

**Do not `sed -i` `app/Config/config.php` as root.** It leaves the file owned by root with mode 600 and php-fpm then fails with `include(config.php): Permission denied`, which surfaces as a generic HTTP 500. If you must edit it, finish with `chown www-data:www-data` and `chmod 640`. Prefer `cake Admin setSetting`.

**Auth keys: advanced vs legacy.** With `Security.advanced_authkeys=true`, keys live in the `auth_keys` table, hashed, with an optional `allowed_ips` allowlist. `cake User change_authkey` writes an allowlist entry for the caller's IP, which is why a key that works from one host returns 403 from another. Either clear `allowed_ips` (`UPDATE auth_keys SET allowed_ips=NULL WHERE id=...`) or create the key from the UI with no IP restriction. This deployment uses legacy keys (`advanced_authkeys=false`) so the key in `users.authkey` works from the connector container; switch to advanced keys with explicit allowlists for production.

**Feed events are unpublished by default.** With `MISP_IMPORT_ONLY_PUBLISHED=true` the OpenCTI connector skips every feed event. Either publish the events in MISP or set the connector to `false` (this deployment does the latter, because the feeds are public OSINT).

**Feed caching is the long pole.** `POST /feeds/cacheFeeds/<scope>` queues a background job per scope (`misp`, `csv`, `freetext`). On a spinning disk the first cache of five feeds takes 10–20 minutes and produces thousands of attributes. Watch it in `Administration → Jobs` and via:

```bash
PASS=$(grep ^MYSQL_PASSWORD ~/aruba-ti/misp/.env | cut -d= -f2)
docker exec misp-db-1 mysql -umisp -p"$PASS" -N -B misp \
  -e "select concat('events=',count(*)) from events; select concat('attributes=',count(*)) from attributes;"
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `misp-core` restarts, logs show DB connection refused | MariaDB still initialising | wait; check `docker compose logs db` |
| `502` from nginx | `misp-core` not healthy | check core logs; wait for schema install |
| `SSL_ERROR_RX_RECORD_TOO_LONG` | hitting HTTPS port with HTTP | use `https://` and the right port |
| Connector 401 | key mismatch | sync `ADMIN_KEY` and `MISP_API_KEY` |
| Connector imports nothing | events not published, or date filter | check `MISP_IMPORT_ONLY_PUBLISHED`, `MISP_IMPORT_FROM_DATE` |
| Disk full | feed cache + attachments | disable feeds, prune events, check `misp/files` |
| Feed cache job never finishes | too many feeds at once | enable in batches, run `cacheAllFeeds` off-hours |

## Backup

The database dump is in `scripts/backup.sh`. A manual dump:

```bash
cd ~/aruba-ti/misp
docker compose exec -T db sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction misp' | gzip > misp-$(date +%F).sql.gz
```

Also back up `misp/files` (attachments) and `misp/ssl` (certificates) if you have custom ones.
