# Sources

Every feed in the platform, why it is there, its licence and how often it updates. The site's [source page](../site/src/data/sources.json) is generated from the same list.

## Enabled by default

| Source | Type | Licence | Cadence | What it adds |
|---|---|---|---|---|
| MISP (local) | Platform | AGPL-3.0 | continuous | Normalisation, deduplication, warning lists, feed management |
| CIRCL OSINT | MISP feed | Public / TLP:CLEAR | hourly | Broad, well-curated OSINT events |
| abuse.ch URLhaus | MISP feed | CC0 | hourly | Malware distribution URLs |
| abuse.ch Feodo Tracker | MISP feed | CC0 | hourly | Botnet C2 IPs (Emotet, Dridex, QakBot) |
| Botvrij.eu | MISP feed | CC0 | daily | Dutch-curated OSINT |
| OpenPhish | MISP feed | Free community feed | hourly | Phishing URLs |
| MITRE ATT&CK | OpenCTI connector | Apache-2.0 / CC BY 4.0 | daily | TTP vocabulary and mappings |
| MITRE ATLAS | OpenCTI connector | Apache-2.0 | daily | AI-system adversary techniques |
| CISA KEV | OpenCTI connector | Public domain | 6 h | Exploited-in-the-wild vulnerability prioritisation |
| OpenCTI Datasets | OpenCTI connector | CC BY-SA 4.0 | daily | Canonical countries, sectors, identities |

## Wired but disabled (needs a key)

| Source | Type | Key | Why disabled |
|---|---|---|---|
| AlienVault OTX | OpenCTI connector | `ALIENVAULT_API_KEY` | Free key required; adds pulses but also volume |
| abuse.ch ThreatFox | OpenCTI connector | `ABUSECH_AUTH_KEY` | abuse.ch Auth-Key required |
| Ransomware.live | OpenCTI connector | `RANSOMWARELIVE_API_KEY` | Pro API key required for the connector |

To enable one, set the key in `.env`, add the service to `docker-compose.yml` (copy the MISP connector block, change image/env), and `docker compose up -d`.

## Adding a MISP feed

1. **Check the licence.** If redistribution is not permitted, it can live in MISP but must never reach the public snapshot.
2. In MISP: `Sync Actions → List Feeds → Add Feed`, or import the default feed catalogue and enable the row.
3. Fetch metadata, then cache:
   ```bash
   KEY=$(grep ^MISP_API_KEY ~/aruba-ti/.env | cut -d= -f2)
   curl -sk -X POST -H "Authorization: $KEY" https://127.0.0.1:9443/feeds/fetchFromAllFeeds
   curl -sk -X POST -H "Authorization: $KEY" https://127.0.0.1:9443/feeds/cacheAllFeeds
   ```
4. Watch the first run: `docker stats`, `df -h`, MISP `Administration → Jobs`.
5. The OpenCTI MISP connector picks up new events on its next 15-minute cycle.

Feed selection criteria:

- updated within the last 90 days;
- attributes have a source and a timestamp;
- the feed owner permits redistribution (CC0, public domain, explicit TLP:CLEAR);
- it adds a data class we do not already have (e.g. Caribbean-specific, Dutch-language, telecom).

## Adding an OpenCTI connector

1. Find the connector under `OpenCTI-Platform/connectors/external-import/<name>`.
2. Generate a UUID for `CONNECTOR_ID`.
3. Add a service to `docker-compose.yml` using the common anchor:
   ```yaml
   connector-example:
     image: opencti/connector-example:latest
     restart: always
     environment:
       <<: *opencti-common
       CONNECTOR_ID: <uuid>
       CONNECTOR_NAME: Example
       CONNECTOR_SCOPE: example
       EXAMPLE_API_KEY: ${EXAMPLE_API_KEY}
     depends_on:
       opencti:
         condition: service_healthy
   ```
4. Add the key to `.env` and `.env.example`.
5. `docker compose up -d connector-example`, then watch its logs for the first run.
6. Add it to `site/src/data/sources.json` and `docs/SOURCES.md`.

## Licensing notes

- **CC0 / public domain** — republish freely.
- **CC BY 4.0** — attribution required; the source page provides it.
- **TLP:CLEAR** — shareable, but respect the source's terms of use.
- **MISP feed terms** — some feeds aggregate third-party data with their own restrictions. When in doubt, keep it platform-only.
- **CISA KEV** — US Government work, public domain.
- **MITRE ATT&CK** — Apache-2.0 for the software, CC BY 4.0 for the knowledge base.

## Quality checks

Run monthly:

- Which feeds produced zero usable events?
- Which produced mostly false positives?
- Which have not updated in 30 days?
- Is the MISP warning list catching known-benign infrastructure?
- Does the indicator mix reflect what local organisations actually see (phishing URLs and domains) rather than only botnet IPs?

A feed that looks impressive in a source table but never produces a local action is cost without value. Cut it.
