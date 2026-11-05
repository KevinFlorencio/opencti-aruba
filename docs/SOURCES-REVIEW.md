# Aruba / Caribbean CTI — connector review

Reviewed `OpenCTI-Platform/connectors` at commit `8e8eccf` (2026-11-05), 324 connectors
(187 external-import, 84 enrichment, 40 stream). 233 of them need a third-party
credential; only 7 need none.

Scope of the question: which of these actually improve threat intelligence for
Aruba and the wider Caribbean (Curaçao, Bonaire, Trinidad, Guyana, Suriname,
Barbados, Jamaica, DR…).

## TL;DR

- **There is no Aruba- or Caribbean-specific connector in the repository.** Nothing
  mentions Aruba, CARICOM or the Caribbean. Regional relevance has to be built:
  global feeds + a country filter where the source supports one + enrichment that
  geo-tags observables + MISP feeds you curate yourself.
- **Only one connector in the repo can be scoped to Aruba at the source:**
  `abuseipdb-ipblacklist`, via `ABUSEIPDB_ONLY_COUNTRY=AW,CW,BQ,TT,GY,SR,...`.
- **Only one free signup is genuinely required** for the good baseline: AlienVault OTX.
  The rest of the useful stack is keyless or self-hosted.
- **Two of the sources currently listed as enabled in `docs/SOURCES.md` are dead.**
  abuse.ch retired its public bulk downloads: URLhaus CSV and MISP feed, ThreatFox
  CSV, and MalwareBazaar CSV all return **HTTP 410 Gone** today. Feodo Tracker still
  works (200). The ThreatFox connector has no Auth-Key support, so as shipped it
  cannot ingest anything any more.
- **Ransomware.live needs a paid Pro key.** The repo also has `ransomlook`, which is
  free, keyless, and covers the same class of data.
- **Best paid single source for this project, if ever funded:** Lab539 AiTM Feed —
  it is the only paid feed directly aimed at the AiTM/Typhoon-style phishing kits
  that hit Aruban government and business targets.

## Verified live on 2026-11-05

| Endpoint | Result |
|---|---|
| `https://urlhaus.abuse.ch/downloads/csv/` | 410 Gone |
| `https://urlhaus.abuse.ch/downloads/misp/` | 410 Gone |
| `https://threatfox.abuse.ch/export/csv/recent/` | 410 Gone |
| `https://bazaar.abuse.ch/export/csv/recent/` | 410 Gone |
| `https://feodotracker.abuse.ch/downloads/ipblocklist.csv` | 200 |
| `https://www.circl.lu/doc/misp/feed-osint/manifest.json` | 200 |
| `https://www.botvrij.eu/data/feed-osint/manifest.json` | 200 |
| `https://www.ransomlook.io/api/recent` | 200 |
| Criminal IP C2 Daily Feed (GitHub raw) | 200 |
| abuse.ch login (`auth.abuse.ch`) | now OAuth / e-mail link, rate limits announced |

## Ranked for Aruba / Caribbean

### Tier 1 — add now, no account, no key

| Connector | Path | What it gives Aruba | Notes |
|---|---|---|---|
| RansomLook | `external-import/ransomlook` | Ransomware claims (victim name, group, description); local relevance by matching Aruban/Caribbean organisation names | Public API, no key. No victim-country field in the recent feed, so filter by name/domain. Set a dedicated `RansomLook` OpenCTI user. |
| Phishunt | `external-import/phishunt` | Active phishing URLs — the dominant local threat class | Keyless, `PHISHUNT_DEFAULT_X_OPENCTI_SCORE=40` |
| Criminal IP C2 Daily Feed | `external-import/criminalip-c2-daily-feed` | 50 C2 IPs/day, with country field | Free but tiny sample; low volume, low cost |
| XposedOrNot | `internal-enrichment/xposedornot` | Breach exposure for `.aw` e-mail addresses | Keyless community API, 25 req/hour |
| Feodo Tracker (MISP feed) | MISP | Botnet C2 IPs | CSV still live; keep |

### Tier 2 — one free account each

| Connector | Path | Env | What it gives Aruba | Caveat |
|---|---|---|---|---|
| AlienVault OTX | `external-import/alienvault` | `ALIENVAULT_API_KEY` | Pulses with `targeted_countries`, including Aruba; largest free OSINT corpus | Free signup at otx.alienvault.com. Set `ALIENVAULT_PULSE_START_TIMESTAMP` to recent or the first run pulls from 2020. |
| AbuseIPDB IP blacklist | `external-import/abuseipdb-ipblacklist` | `ABUSEIPDB_API_KEY`, `ABUSEIPDB_ONLY_COUNTRY=AW,CW,BQ,TT,GY,SR` | **The only country-scoped feed in the repo** | Free tier is rate-limited and caps the pull size; use `ABUSEIPDB_SCORE=75`+ |
| VirusTotal | `internal-enrichment/virustotal` | `VIRUSTOTAL_TOKEN` | Enrich any local IOC | Free: 4 lookups/min, 500/day |
| urlscan.io | `external-import/urlscan` | `URLSCAN_API_KEY` | Scan/observe local phishing landing pages | Free tier |
| MalwareBazaar | `external-import/malwarebazaar` | Auth-Key | Malware samples seen in regional campaigns | Needs `ABUSECH_AUTH_KEY`; abuse.ch retired the old CSV, connector uses API |
| IPinfo | `internal-enrichment/ipinfo` | `IPINFO_TOKEN` | ASN/country tagging — turns "an IP" into "an Aruba ISP IP" | Free token |

### Tier 3 — paid, only if the project gets funding

| Connector | Why it matters here |
|---|---|
| Lab539 AiTM Feed (`external-import/lab539-aitm-feed`) | Directly targets adversary-in-the-middle phishing infrastructure — the Tycoon 2FA problem described in the project notes |
| Group-IB TI (`external-import/group-ib-ti`) | Region/victimology tagging; expensive |
| Flashpoint (`external-import/flashpoint`) | Regional targeting metadata; expensive |
| GreyNoise Feed (`external-import/greynoise-feed`) | Subscription required |
| Shodan (`internal-enrichment/shodan`), Spur, Censys | Enrichment depth; free tiers only give samples |

### Not worth it for this project

Recorded Future, Intel471, ZeroFox, CTM360, Cybersixgill, Silobreaker, Flashpoint
and the other commercial feeds are all enterprise contracts. For a one-island
publishing project they cost more than they return.

## What the repo cannot give you

Regional context lives outside these connectors. To make the platform actually
Aruban, add:

1. **Local MISP feeds** (the MISP connector already ingests them):
   CARICOM IMPACS advisories, CIRT-CW (Curaçao), Aruba government/CERT notices,
   `.aw` registry abuse reports.
2. **A local watchlist**: `.aw` domains, Aruban bank/government/utility brand
   names, and Aruba ISP ASNs/IP ranges (pull the ranges from IPinfo or the RIR,
   load them as a CSV feed). This is what turns global indicators into local hits.
3. **Outbound publishing** — the project's actual differentiator — stays on the
   site, not in a connector.

## Corrections for `docs/SOURCES.md`

- URLhaus MISP feed: **dead (410)**. Either move to the authenticated abuse.ch API
  with an Auth-Key, or drop it and rely on Phishunt/OTX for phishing URLs.
- ThreatFox: marked "Auth-Key required" but the connector only reads the retired
  public CSV and supports no key. **Disable until the connector is patched.**
- Ransomware.live: Pro key is paid. Use `ransomlook` (free) instead.
- Feodo Tracker: still valid.

## Suggested order of work

1. Fix the abuse.ch breakage (drop dead feeds, or obtain one Auth-Key and use the
   API-capable connectors only).
2. Add RansomLook + Phishunt (keyless) and confirm ingestion.
3. Add OTX with a recent start timestamp.
4. Add AbuseIPDB with the Caribbean country list.
5. Add IPinfo/VirusTotal enrichment.
6. Defer every paid connector.

## Drop-in compose blocks (keyless sources)

Generate one UUID per connector. These are ready apart from the IDs.

```yaml
  connector-ransomlook:
    image: opencti/connector-ransomlook:latest
    restart: always
    environment:
      <<: *opencti-common
      CONNECTOR_ID: 79a72ccf-56f1-443e-a17c-2719913d8187
      CONNECTOR_NAME: RansomLook
      CONNECTOR_SCOPE: ransomlook
      CONNECTOR_DURATION_PERIOD: PT6H
    depends_on:
      opencti:
        condition: service_healthy

  connector-phishunt:
    image: opencti/connector-phishunt:latest
    restart: always
    environment:
      <<: *opencti-common
      CONNECTOR_ID: f2c36bc6-17f9-4a5a-a06b-c5987e1622fa
      CONNECTOR_NAME: Phishunt
      CONNECTOR_SCOPE: phishunt
      CONNECTOR_DURATION_PERIOD: PT6H
      PHISHUNT_CREATE_INDICATORS: "true"
      PHISHUNT_DEFAULT_X_OPENCTI_SCORE: "40"
    depends_on:
      opencti:
        condition: service_healthy

  connector-criminalip:
    image: opencti/connector-criminalip-c2-daily-feed:latest
    restart: always
    environment:
      <<: *opencti-common
      CONNECTOR_ID: bc24854a-56a3-47bd-b09f-d4421b0c0b5a
      CONNECTOR_NAME: Criminal IP C2 Daily
      CONNECTOR_SCOPE: ipv4-addr
      CRIMINALIP_INTERVAL: "1"
      CRIMINALIP_CONFIDENCE_SCORE: "100"
    depends_on:
      opencti:
        condition: service_healthy
```

For AbuseIPDB, the only line that matters for Aruba:

```yaml
      ABUSEIPDB_ONLY_COUNTRY: "AW,CW,BQ,TT,GY,SR,BB,GD,LC,DM,AG,KN,VC,JM,BS,HT,DO,PR"
```

ISO 3166-1 alpha-2: Aruba `AW`, Curaçao `CW`, Bonaire/Sint Eustatius/Saba `BQ`,
Trinidad & Tobago `TT`, Guyana `GY`, Suriname `SR`, Barbados `BB`, Grenada `GD`,
Saint Lucia `LC`, Dominica `DM`, Antigua `AG`, St Kitts & Nevis `KN`,
St Vincent `VC`, Jamaica `JM`, Bahamas `BS`, Haiti `HT`, Dominican Republic `DO`,
Puerto Rico `PR`.
