# Architecture

## Goals

1. Give Aruba and the Dutch Caribbean a **structured, public** threat picture.
2. Keep the intelligence platform **off the public internet**.
3. Make the deployment **reproducible** on a single Proxmox guest.
4. Publish **only** TLP:CLEAR material, with a documented field allow-list.
5. Stay useful when a feed breaks: the last snapshot keeps rendering.

## Component view

| Component | Image / version | Role | Persistence |
|---|---|---|---|
| OpenCTI | `opencti/platform:7.261103.0` | STIX 2.1 knowledge graph, API, UI | Elasticsearch + S3 |
| Worker | `opencti/worker:7.261103.0` (×2) | Background jobs, connector orchestration | — |
| Elasticsearch | `8.19.21` | Primary datastore and search index | `esdata` volume |
| Redis | `8.10.1` | Cache and stream | `redisdata` |
| RabbitMQ | `4.3-management` | Connector work queue | `amqpdata` |
| S3 store | `pgsty/silo` | Files, exports, attachments | `s3data` |
| MISP core | `ghcr.io/misp/misp-docker/misp-core` | Feed ingestion, event sharing | `mysql_data`, files |
| MISP nginx | `misp-nginx` | TLS termination, FastCGI | `ssl/` |
| MariaDB | `10.11` | MISP relational store | `mysql_data` |
| Valkey | `7.2` | MISP cache | `cache_data` |
| Connectors | `opencti/connector-*` | Import ATT&CK, ATLAS, KEV, MISP, datasets | — |
| Collector | Python 3 stdlib | GraphQL + MISP → `latest.json` | `site/public/data` |
| Site | Astro 5, ECharts 6, Leaflet 1.9 | Static radar + blog | `site/dist` |
| Edge | Caddy 2.10 | Static files :80, OpenCTI proxy :8443 | `caddydata` |

## Data flow

```
Public feeds                  MISP                      OpenCTI
────────────                  ────                      ───────
CIRCL OSINT ──┐
Phishunt ─────┤   fetch/cache   ┌─────────┐   connector  ┌──────────┐
Feodo ────────┼───────────────► │  events │ ───────────► │ reports  │
Botvrij ──────┤                 │attributes│             │indicators│
OpenPhish ────┘                 └─────────┘              │ malware  │
                                                         │ actors   │
MITRE ATT&CK ───────────────────────────────────────────►│ vulns    │
MITRE ATLAS ────────────────────────────────────────────►│ sectors  │
CISA KEV ───────────────────────────────────────────────►│ locations│
OpenCTI datasets ───────────────────────────────────────►└────┬─────┘
                                                               │ GraphQL
                                                               ▼
                                                     ┌──────────────────┐
                                                     │ collect_radar.py │
                                                     │ field allow-list │
                                                     └────────┬─────────┘
                                                              │ latest.json
                                                              ▼
                                                     ┌──────────────────┐
                                                     │ Astro build      │
                                                     │ radar + blog     │
                                                     └────────┬─────────┘
                                                              │ static files
                                                              ▼
                                                     ┌──────────────────┐
                                                     │ Caddy :80        │
                                                     └──────────────────┘
```

## Why one VM

The initial corpus is deliberately small: five public feeds plus reference data, not a commercial firehose. A single 20 GB / 8 vCPU guest handles it with headroom. The constraint is disk I/O, not CPU: the VM disk lives on the lab's USB HDD, so bulk ingestion is scheduled and backups are throttled.

When the corpus grows:

- move the VM disk to NVMe (first priority — Elasticsearch hates USB bridges);
- add a second Elasticsearch node and set `ELASTICSEARCH__NUMBER_OF_REPLICAS=1`;
- split MISP onto its own guest;
- put the collector on a schedule against a read-only token.

## Why Elasticsearch is the source of truth

OpenCTI 7's compose no longer ships a relational database for the platform; Elasticsearch holds the graph, with S3 for files. That makes backup a two-part problem:

1. **Elasticsearch snapshot** (preferred, online) or a volume copy (simple, requires a short stop).
2. **S3 volume** for files and exports.

The runbook documents the volume-copy path because it is the one that works without a snapshot repository. A production deployment should add an S3 snapshot repository and use the Elasticsearch snapshot API.

## Network and exposure

| Port | Bound to | Purpose | Exposure |
|---|---|---|---|
| 80 | `0.0.0.0` | Radar + blog | LAN (publishable) |
| 8443 | `0.0.0.0` | OpenCTI via Caddy, internal TLS | LAN only |
| 8080 | `127.0.0.1` | OpenCTI API for the collector | localhost |
| 9080 | `0.0.0.0` | MISP HTTP → HTTPS redirect | LAN |
| 9443 | `0.0.0.0` | MISP HTTPS | LAN only |

OpenCTI's application port is bound to loopback on purpose. Caddy holds the only externally reachable path to it. Elasticsearch, Redis, RabbitMQ and the S3 store have no published ports at all.

## Trust boundaries

- **Feed → MISP.** Untrusted input. MISP enforces warning lists and correlation; the connector filters on published/TLP.
- **MISP → OpenCTI.** Semi-trusted. The MISP connector creates STIX objects; no code execution.
- **OpenCTI → collector.** Trusted, read-only in practice. The collector uses the admin token today; a read-only service account is a hardening item.
- **Collector → site.** The only place data leaves the platform. The collector explicitly selects fields; it does not serialise arbitrary objects.
- **Site → browser.** Static HTML/JS. No token, no API call, no write path.

## Failure modes

| Failure | Effect | Mitigation |
|---|---|---|
| Elasticsearch down | OpenCTI UI/API unavailable; site still serves last snapshot | restart ES, check disk/heap |
| MISP down | Connector retries; other feeds continue | connector restarts automatically |
| Collector fails | Snapshot goes stale | systemd timer retries; `generated_at` visible on the radar |
| Caddy down | Site and UI unreachable | `docker compose restart caddy` |
| USB disk drops | Everything on the VM stalls | documented recovery; move to NVMe |
| Feed poisoned | Bad indicators in graph | MISP warning lists, TLP filter, manual review |

## Design decisions

**Static site instead of a live API.** Publishing a read-only JSON snapshot removes an entire attack surface: no database credentials in a web process, no GraphQL proxy, no session handling. It also makes the radar deployable to GitHub Pages or Cloudflare with zero backend.

**MISP as the ingestion layer.** OpenCTI's own connectors are excellent for structured sources, but MISP is better at normalising messy OSINT feeds, deduplicating attributes and applying warning lists. Using both plays to each tool's strength.

**Curated regional layer.** No public feed will tell you that Aruba's Parliament lost an email account. That requires reading local news, verifying with a second source and writing it down. The site separates this layer visually and labels it as curated.

**No public OpenCTI dashboards.** OpenCTI's dashboard sharing is not designed for anonymous public access. The radar re-implements the useful views against the snapshot instead of exposing the platform.
