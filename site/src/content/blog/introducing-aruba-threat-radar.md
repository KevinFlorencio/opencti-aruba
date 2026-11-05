---
title: "Introducing the Aruba Threat Radar"
description: "Why the island needs its own intelligence desk, how the OpenCTI + MISP pipeline is built, and exactly what will be published every week."
published: 2026-11-05
tags: ["project", "OpenCTI", "MISP", "architecture"]
sources:
  - label: "OpenCTI — open-source threat intelligence platform"
    url: "https://github.com/OpenCTI-Platform/opencti"
  - label: "MISP — open-source threat intelligence sharing platform"
    url: "https://github.com/MISP/MISP"
  - label: "MITRE ATT&CK"
    url: "https://attack.mitre.org/"
  - label: "CISA Known Exploited Vulnerabilities catalog"
    url: "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
---

There is no shortage of global threat intelligence. There is a shortage of **local** threat intelligence: a consistent, structured, public record of what is happening to Aruba, Curaçao, Bonaire and Sint Maarten, written by someone who lives here and can tell the difference between a global feed and a local incident.

The Aruba Threat Radar is that record. It is an OpenCTI instance running on a Proxmox host in the lab, fed by MISP and public CTI sources, with a static public dashboard and this blog in front of it. This post explains the design, the boundaries and what to expect.

## The problem with "just follow the news"

News reporting gives us the what, usually after the fact, often in fragments. It rarely gives us:

- the **techniques** behind an incident, in a form defenders can map to controls;
- the **indicators** that were observed, in a form a SOC can ingest;
- the **pattern** across islands and sectors, because each outlet covers its own country;
- a **baseline** that lets you say "this is unusual" rather than "this is scary".

A threat intelligence platform fixes the structure. OpenCTI stores entities and relationships using STIX 2.1: reports, threat actors, campaigns, malware, attack patterns, vulnerabilities, indicators, observables, locations, sectors, and the links between them. That graph is what lets a phishing report from Curaçao be connected to an ATT&CK technique, a malware family and an Aruban sector without a human re-reading everything.

## Architecture

```
                         ┌────────────────────────────────────────────┐
                         │  Proxmox VE host (ophanim)                  │
                         │  VM 124 · opencti-aruba · 8 vCPU / 20 GB    │
                         │                                            │
  MISP public feeds ───► │  ┌──────────┐    ┌───────────────────────┐  │
  CIRCL, URLhaus,        │  │  MISP    │    │  OpenCTI 7            │  │
  Feodo, Botvrij,        │  │  MariaDB │───►│  GraphQL API :8080    │  │
  OpenPhish              │  │  Redis   │    │  Elasticsearch        │  │
                         │  └──────────┘    │  Redis / RabbitMQ     │  │
  MITRE ATT&CK ─────────►│                  │  S3-compatible store  │  │
  MITRE ATLAS  ─────────►│  connectors ────►│                       │  │
  CISA KEV     ─────────►│  (misp, mitre,   └───────────┬───────────┘  │
  OpenCTI data ─────────►│   kev, atlas,                │              │
                         │   datasets)                  │ GraphQL      │
                         │                              ▼              │
                         │                   ┌─────────────────────┐   │
                         │                   │ collector (Python)  │   │
                         │                   │ snapshot + brief    │   │
                         │                   └──────────┬──────────┘   │
                         │                              │ JSON         │
                         │                   ┌──────────▼──────────┐   │
                         │                   │ Astro static site   │   │
                         │                   │ radar + blog        │   │
                         │                   └──────────┬──────────┘   │
                         └──────────────────────────────┼──────────────┘
                                                        │ HTTP
                                              ┌─────────▼─────────┐
                                              │ Caddy :80 / :8443 │
                                              │ public / OpenCTI  │
                                              └───────────────────┘
```

Three principles drive the design:

**1. Separate the platform from the publication.** OpenCTI is not exposed to the public internet. A collector queries the GraphQL API on a schedule, writes a small JSON snapshot, and the static site is built from that snapshot. If the site is compromised, the platform is not. If the platform is down, the last snapshot still renders.

**2. Publish at TLP:CLEAR only.** Feeds are selected and filtered for data that can be shared publicly. Internal or sensitive sources can live in OpenCTI without ever reaching the snapshot. The collector uses an explicit allow-list of fields, not a database dump.

**3. Keep the regional layer human.** Global feeds know nothing about Aruba. The regional incident map, the ATT&CK coverage view and the briefing text are curated by hand from public reporting, with a source link on every entry. Automation handles volume; a human handles meaning.

## The stack

| Layer | Component | Why |
|---|---|---|
| Hypervisor | Proxmox VE 9.x | Existing lab; snapshots, backups, clean isolation |
| Runtime | Debian 13 + Docker Compose | Reproducible; every service pinned in git |
| Knowledge base | OpenCTI 7.261103.0 | STIX 2.1 graph, ATT&CK, connectors, dashboards |
| Sharing | MISP (Docker) | Public OSINT feeds + local event sharing |
| Search | Elasticsearch 8.19 | OpenCTI's index |
| Bus / cache | RabbitMQ 4.3, Redis 8 | Connector and worker queues |
| Object store | S3-compatible (silo) | Report attachments, exports |
| Collector | Python 3 + requests | GraphQL → snapshot.json |
| Site | Astro 5 + ECharts + Leaflet | Static, fast, no runtime server |
| Edge | Caddy 2 | TLS, static files, reverse proxy |

The whole thing fits in one VM because the data volume is deliberately modest: a curated set of feeds, not a firehose. A full-feed deployment would need a second Elasticsearch node and more disk, and that is a documented upgrade path rather than a day-one requirement.

## The feeds, and why these

**MISP** is the ingestion workhorse. It consumes public OSINT feeds — CIRCL, URLhaus, Feodo Tracker, Botvrij, OpenPhish — and normalises them into events with attributes, tags and galaxies. The official OpenCTI MISP connector then pulls published events into the graph as reports, indicators and observables.

**MITRE ATT&CK** gives every technique a stable ID and a tactic. Without it, "phishing" is a word; with it, `T1566.002` is a node that can be counted, mapped and compared across incidents.

**MITRE ATLAS** is forward-looking. AI adoption on the islands is rising faster than AI security literacy; ATLAS gives us the vocabulary for those threats before they appear in local incident reports.

**CISA KEV** is a prioritisation signal, not a local feed. It answers "which vulnerabilities are actually being exploited?" so patch meetings can stop arguing about CVSS scores.

**OpenCTI datasets** provide canonical locations, sectors and identities, so "Aruba" is one entity and not four spellings.

Optional connectors for AlienVault OTX, abuse.ch ThreatFox and Ransomware.live are wired but disabled by default. They need API keys, and a key without an owner is a broken feed waiting to happen.

## What gets published

Every collector run produces a snapshot with:

- **counts** — reports, indicators, malware families, actors, KEV vulnerabilities, watchlist hits;
- **latest reports** — title, date, confidence, link into the platform;
- **fresh indicators** — type, defanged value, score (never the raw URL in the public HTML);
- **indicator mix and ingestion series** — for the charts;
- **source health** — which feeds are online, optional or stale;
- **a weekly brief stub** — the numbers and headlines a human then writes around.

The site renders that snapshot client-side. There is no server-side database connection, no API key in the browser, and no way to pivot from the public site into the platform.

## What does not get published

- Victim identities, personal data, or details that could re-victimise an organisation.
- Unverified attribution. If a report says "a ransomware group", we do not upgrade it to a named actor because it fits a pattern.
- Raw malware samples, credentials, or live phishing URLs in clickable form.
- Anything above TLP:CLEAR. The collector filters on marking, and the source catalogue documents the licence of each feed.

## The weekly rhythm

- **Continuous:** MISP feeds and OpenCTI connectors ingest.
- **Every 15 minutes:** the MISP connector reconciles new events.
- **Every 6 hours:** the collector refreshes the snapshot; Caddy serves it immediately.
- **Weekly:** a written brief — what changed, what it means for the islands, what to do. Published here and cross-posted to the social channels where people actually are.
- **Monthly:** a review of source coverage and false positives. Feeds that produce noise without value get cut.

## Roadmap

1. **OpenCTI dashboards** for the analyst view: regional watchlist, KEV exposure, MISP feed health.
2. **STIX/TAXII export** of the public bundle, so local SOCs can subscribe instead of scraping the site.
3. **Sector views** for government, finance, hospitality, utilities and healthcare.
4. **Papiamento and Dutch summaries** of every brief. English-only intelligence is a filter on who can use it.
5. **Community reporting form** with anonymous submission and source protection.

## Contribute

The repository is public: infrastructure as code, collector, site and docs. If you run an organisation on the island and want to share an incident, a phishing sample or a correction, the contact route is on the [about page](/about/#contact). If you spot an error in a briefing, open an issue — corrections are published, not quietly edited.

The goal is not to look like a large national CERT. It is to make sure that when the next wave arrives, the islands are not starting from zero.

---

*Published 5 November 2026.*
