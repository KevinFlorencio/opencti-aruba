# Dashboard and snapshot contract

The public radar is a static Astro site. It fetches one JSON file and renders it client-side. There is no API, no session and no token in the browser.

## Files

| Path | Role |
|---|---|
| `scripts/collect_radar.py` | Queries OpenCTI GraphQL + MISP, writes the snapshot |
| `site/public/data/latest.json` | The snapshot the site fetches |
| `site/src/pages/index.astro` | Radar markup + client renderer |
| `site/src/data/incidents.json` | Curated regional incidents (hand-maintained) |
| `site/src/data/attack.json` | Curated ATT&CK coverage (hand-maintained) |
| `site/src/data/sources.json` | Source catalogue (hand-maintained) |
| `site/src/content/blog/*.md` | Briefings |

## Snapshot schema

```jsonc
{
  "generated_at": "2026-11-05T20:08:58Z",
  "platform": {
    "status": "online",              // online | degraded
    "version": "7.261103.0",
    "url": "https://192.168.0.180:8443",
    "misp_status": "online"          // online | offline
  },
  "kpis": {
    "reports": 2,
    "indicators": 1204,
    "malware": 87,
    "actors": 31,
    "campaigns": 4,
    "vulnerabilities": 1240,
    "observables": 5400,
    "watchlist_hits": 14
  },
  "counts_by_type": [{ "name": "Observables", "count": 5400 }],
  "reports": [
    {
      "id": "uuid",
      "name": "Report title",
      "published": "2025-08-13T00:00:00.000Z",
      "confidence": 75,
      "types": ["threat-report"],
      "labels": ["aruba"]
    }
  ],
  "indicators": [
    {
      "id": "uuid",
      "name": "domain-name:value = 'example.com'",
      "value": "example.com",
      "pattern_type": "stix",
      "type": "DOMAIN",
      "score": 60,
      "valid_from": "2026-11-01T00:00:00.000Z",
      "created_at": "2026-11-01T00:00:00.000Z",
      "labels": ["osint"]
    }
  ],
  "series": [{ "date": "2026-11-01", "count": 42 }],
  "indicator_mix": [{ "label": "domain-name", "count": 730 }],
  "sources": [
    { "name": "MISP", "type": "Platform", "status": "online", "detail": "2.5.51" }
  ],
  "brief": { "number": 1, "window": "...", "headline": "...", "summary": "..." }
}
```

### Publication rules

The collector is the only code allowed to widen this contract. When editing it:

- never add a field that identifies a victim, a person or an internal host;
- never add raw file contents, credentials or un-defanged URLs;
- keep the field list explicit — do not serialise arbitrary STIX objects;
- keep `generated_at` accurate; the UI treats the snapshot as stale after 12 hours.

The site defangs values in `defang()` and escapes all feed text with `escapeHtml()`.

## How the radar renders

1. `renderEmptyCharts()` paints empty axes immediately, so the layout does not jump.
2. `load()` fetches `/data/latest.json` with a cache-buster.
3. KPIs animate with `requestAnimationFrame`.
4. Reports and indicators are rendered with template strings; every dynamic value is escaped.
5. ECharts renders the ingestion line, indicator donut and graph-composition bars.
6. Leaflet renders the curated incident map; markers are coloured by severity.
7. The ATT&CK matrix is generated from `attack.json`; heat = number of curated incidents where the technique was reported.

If the fetch fails, the page keeps the empty charts and shows `SNAPSHOT MISSING` in the signal card instead of breaking.

## Adding a widget

1. Add the data to `collect_radar.py` **and** to the schema above (if it is public-safe).
2. Add a `.card` with a titled container in `index.astro`.
3. Initialise the chart in `renderEmptyCharts()` and fill it in `renderCharts()`.
4. Add a fallback for zero rows — a chart with no data should say so, not render a blank box.
5. Test at 1440 px, 1024 px and 390 px widths. The grid collapses at 1080 px and 720 px.

## Adding a briefing

Create `site/src/content/blog/<slug>.md`:

```yaml
---
title: "..."
description: "..."
published: 2026-11-05
tags: ["incident analysis"]
sources:
  - label: "Publisher — Title (date)"
    url: "https://..."
---
```

The blog index, article page and RSS update automatically. Rules:

- every factual claim links to a public source;
- attribution stays absent unless public evidence exists;
- victim identities are excluded;
- write for a smart reader who is not a security specialist.

## Building

```bash
cd site
npm install
npm run build      # → site/dist
npm run dev        # local preview on :4321
```

Caddy serves `site/dist`. The build is deterministic and can run in CI; the only runtime input is `latest.json`, which is fetched from the same origin.

## Performance

- ECharts + Leaflet dominate the bundle (~425 KB gzip). Acceptable for a dashboard; if it matters, replace ECharts with a small chart library and lazy-load the map.
- Fonts come from Google Fonts. Self-host them for a zero-third-party build.
- Tiles come from CARTO. The map degrades to a dark panel if the CDN is unreachable.
- No analytics, no cookies, no tracking pixels.

## Accessibility

- Colour is not the only signal: severity is also text in the timeline and popups.
- The map has a text timeline equivalent directly beside it.
- Charts have titles and the underlying numbers appear in KPI cards and tables.
- Focus styles use the browser default; do not remove outlines.
- `prefers-reduced-motion` disables ticker, pulse and reveal animations.

## Analyst dashboards inside OpenCTI

The public radar is the publishable view. The analyst view lives in OpenCTI
itself, under **Dashboards → Custom dashboards**:

| Dashboard | Question it answers |
| --- | --- |
| Aruba Watchlist | Reports, indicators, observables, ATT&CK techniques, malware and intrusion sets in one screen |
| KEV Exposure | Known-exploited vulnerabilities vs the full vulnerability baseline |
| Ingestion Pulse (24h) | Whether the collectors delivered anything in the last day |

They are dashboards, not reports: every widget is a live count over the graph,
with the dashboard date range applied. They are LAN-only because OpenCTI is
LAN-only. The public page never queries them.

The manifests are generated from a small Python snippet and imported with the
`workspaceConfigurationImport` GraphQL mutation. To back one up, use the UI's
export (it writes `[YYYYMMDD]_octi_dashboard_[name].json`) and keep the JSON in
`site/src/data/` only if it contains no sensitive filters.
