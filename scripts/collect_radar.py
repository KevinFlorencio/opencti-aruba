#!/usr/bin/env python3
"""
Aruba Threat Radar collector.

Queries the OpenCTI GraphQL API and the local MISP instance, then writes a
small, public-safe JSON snapshot that the static site renders. No database
credentials, no raw malware traffic, no unfiltered platform dump.

Usage:
    OPENCTI_TOKEN=... python3 scripts/collect_radar.py
    python3 scripts/collect_radar.py --out site/public/data/latest.json

Environment:
    OPENCTI_URL    default http://127.0.0.1:8080
    OPENCTI_TOKEN  required (admin or read-only API token)
    MISP_URL       optional, e.g. https://192.168.0.180:9443
    MISP_KEY       optional, MISP automation key
    MISP_SSL_VERIFY default false (self-signed lab certificate)
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "site" / "public" / "data" / "latest.json"

# The public focus is a data file, not a hardcoded list: change region.json to
# widen or narrow the watchlist without touching the collector.
try:
    REGION = json.loads((ROOT / "site" / "src" / "data" / "region.json").read_text())
    WATCHLIST_TERMS = [str(t).lower() for t in REGION["watchlist_terms"]]
except (OSError, KeyError, ValueError):
    WATCHLIST_TERMS = ["aruba", "curacao", "curaçao", "bonaire", "oranjestad"]


def log(msg: str) -> None:
    print(f"[collector] {msg}", file=sys.stderr)


class GraphQL:
    def __init__(self, url: str, token: str, timeout: int = 60):
        self.url = url.rstrip("/") + "/graphql"
        self.token = token
        self.timeout = timeout

    def query(self, query: str, variables: dict | None = None, attempts: int = 3) -> dict:
        payload = json.dumps({"query": query, "variables": variables or {}}).encode()
        last: Exception | None = None
        for attempt in range(1, attempts + 1):
            req = urllib.request.Request(
                self.url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read().decode())
                if body.get("errors"):
                    raise RuntimeError(f"GraphQL error: {body['errors'][0].get('message')}")
                return body["data"]
            except Exception as exc:  # network, JSON, GraphQL
                last = exc
                if attempt < attempts:
                    time.sleep(2 * attempt)
        raise RuntimeError(f"OpenCTI query failed after {attempts} attempts: {last}")


def misp_get(base: str, key: str, path: str, verify: bool = False, timeout: int = 20):
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        base.rstrip("/") + path,
        headers={"Authorization": key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode())


def collect_counts(gql: GraphQL) -> dict:
    """OpenCTI caps stixCoreObjectsNumber at two per request; batch accordingly."""
    counts: dict[str, int] = {}

    data = gql.query("{ reportsNumber { total } indicatorsNumber { total } }")
    counts["reports"] = data["reportsNumber"]["total"]
    counts["indicators"] = data["indicatorsNumber"]["total"]

    data = gql.query(
        """
        {
          malware: stixCoreObjectsNumber(types: ["Malware"]) { total }
          actors: stixCoreObjectsNumber(types: ["Threat-Actor", "Intrusion-Set"]) { total }
        }
        """
    )
    counts["malware"] = data["malware"]["total"]
    counts["actors"] = data["actors"]["total"]

    data = gql.query(
        """
        {
          campaigns: stixCoreObjectsNumber(types: ["Campaign"]) { total }
          vulns: stixCoreObjectsNumber(types: ["Vulnerability"]) { total }
        }
        """
    )
    counts["campaigns"] = data["campaigns"]["total"]
    counts["vulnerabilities"] = data["vulns"]["total"]

    data = gql.query("{ stixCyberObservablesNumber { total } }")
    counts["observables"] = data["stixCyberObservablesNumber"]["total"]

    return counts


def collect_watchlist(gql: GraphQL) -> int:
    total = 0
    terms = WATCHLIST_TERMS
    for i in range(0, len(terms), 2):
        pair = terms[i : i + 2]
        aliases = " ".join(
            f'a{n}: stixCoreObjectsNumber(search: "{t}") {{ total }}' for n, t in enumerate(pair)
        )
        data = gql.query("{ " + aliases + " }")
        for value in data.values():
            total += value["total"]
    return total


def collect_reports(gql: GraphQL, limit: int = 12) -> list[dict]:
    data = gql.query(
        """
        query Reports($n: Int) {
          reports(first: $n, orderBy: published, orderMode: desc) {
            edges { node { id name published confidence report_types objectLabel { value } } }
          }
        }
        """,
        {"n": limit},
    )
    out = []
    for edge in data["reports"]["edges"]:
        node = edge["node"]
        out.append(
            {
                "id": node["id"],
                "name": node["name"],
                "published": node.get("published"),
                "confidence": node.get("confidence"),
                "types": node.get("report_types") or [],
                "labels": [label["value"] for label in (node.get("objectLabel") or [])],
            }
        )
    return out


def collect_indicators(gql: GraphQL, limit: int = 40) -> list[dict]:
    data = gql.query(
        """
        query Indicators($n: Int) {
          indicators(first: $n, orderBy: created_at, orderMode: desc) {
            edges {
              node {
                id name pattern pattern_type x_opencti_score valid_from created_at
                objectLabel { value }
              }
            }
          }
        }
        """,
        {"n": limit},
    )
    out = []
    for edge in data["indicators"]["edges"]:
        node = edge["node"]
        pattern_type = (node.get("pattern_type") or "").lower()
        if "ipv4" in pattern_type or "ipv6" in pattern_type:
            label = "IP"
        elif "domain" in pattern_type:
            label = "DOMAIN"
        elif "url" in pattern_type:
            label = "URL"
        elif "sha" in pattern_type or "md5" in pattern_type:
            label = "HASH"
        else:
            label = "OTHER"
        # Render a clean value from the STIX pattern: [domain-name:value = 'x']
        value = node.get("name") or node.get("pattern") or ""
        if "=" in value:
            value = value.split("=", 1)[1].strip().strip("'\" ]")
        out.append(
            {
                "id": node["id"],
                "name": node.get("name"),
                "value": value,
                "pattern_type": node.get("pattern_type"),
                "type": label,
                "score": node.get("x_opencti_score"),
                "valid_from": node.get("valid_from"),
                "created_at": node.get("created_at"),
                "labels": [label["value"] for label in (node.get("objectLabel") or [])],
            }
        )
    return out


def collect_series(gql: GraphQL, days: int = 14) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    data = gql.query(
        """
        query Series($start: DateTime!, $end: DateTime!) {
          stixCoreObjectsTimeSeries(
            field: "created_at", operation: count,
            startDate: $start, endDate: $end, interval: "day",
            types: ["Report", "Indicator"]
          ) { date value }
        }
        """,
        {"start": start.isoformat().replace("+00:00", "Z"), "end": end.isoformat().replace("+00:00", "Z")},
    )
    return [{"date": row["date"][:10], "count": row["value"]} for row in data["stixCoreObjectsTimeSeries"]]


def collect_mix(gql: GraphQL) -> list[dict]:
    data = gql.query(
        '{ indicatorsDistribution(field: "x_opencti_main_observable_type", operation: count) { label value } }'
    )
    rows = data.get("indicatorsDistribution") or []
    return [{"label": row["label"], "count": row["value"]} for row in rows if row.get("value")]


def collect_connectors(gql: GraphQL) -> list[dict]:
    data = gql.query("{ connectors { name connector_type active auto } }")
    out = []
    for c in data.get("connectors") or []:
        name = c.get("name") or ""
        if name.startswith("[") or name.startswith("OpenCTI "):
            continue
        out.append(
            {
                "name": name,
                "type": (c.get("connector_type") or "").lower(),
                "status": "online" if c.get("active") else "offline",
                "detail": c.get("connector_type") or "",
            }
        )
    return out


def collect_misp() -> tuple[str, list[dict], int]:
    url = os.environ.get("MISP_URL", "").strip()
    key = os.environ.get("MISP_KEY", "").strip()
    if not url or not key:
        return "unconfigured", [], 0
    verify = os.environ.get("MISP_SSL_VERIFY", "false").lower() == "true"
    try:
        version = misp_get(url, key, "/servers/getVersion", verify=verify)
        ver = version.get("version") or version.get("pymisp_recommended_version") or "MISP"
    except Exception as exc:
        log(f"MISP unreachable: {exc}")
        return "offline", [], 0

    feeds: list[dict] = []
    try:
        raw = misp_get(url, key, "/feeds/index", verify=verify, timeout=40)
        for item in raw if isinstance(raw, list) else []:
            feed = item.get("Feed", item) if isinstance(item, dict) else {}
            if not feed.get("enabled"):
                continue
            feeds.append(
                {
                    "name": feed.get("name") or feed.get("id"),
                    "type": "MISP feed",
                    "status": "online",
                    "detail": feed.get("source_format") or "misp",
                }
            )
    except Exception as exc:
        log(f"MISP feed listing failed: {exc}")
    return f"online ({ver})", feeds, len(feeds)


def build_snapshot(gql: GraphQL) -> dict:
    generated = datetime.now(timezone.utc)
    counts = collect_counts(gql)
    counts["watchlist_hits"] = collect_watchlist(gql)

    reports = collect_reports(gql)
    indicators = collect_indicators(gql)
    series = collect_series(gql)
    mix = collect_mix(gql)
    connectors = collect_connectors(gql)
    misp_status, misp_feeds, misp_feed_count = collect_misp()

    sources = [
        {"name": "OpenCTI", "type": "Platform", "status": "online", "detail": "GraphQL API"},
        {"name": "MISP", "type": "Platform", "status": "online" if misp_status.startswith("online") else "offline",
         "detail": misp_status},
        *connectors,
        *misp_feeds,
    ]

    headline = reports[0]["name"] if reports else "Dutch Caribbean radar online"
    summary = (
        f"{counts['reports']} reports, {counts['indicators']} indicators and "
        f"{counts['malware']} malware families in the graph. "
        f"{misp_feed_count} public MISP feeds enabled."
    )

    return {
        "generated_at": generated.isoformat().replace("+00:00", "Z"),
        "platform": {
            "status": "online",
            "version": "7.261103.0",
            "url": os.environ.get("OPENCTI_PUBLIC_URL", "https://192.168.0.180:8443"),
            "misp_status": "online" if misp_status.startswith("online") else "offline",
        },
        "kpis": counts,
        "counts_by_type": [
            {"name": "Observables", "count": counts["observables"]},
            {"name": "Indicators", "count": counts["indicators"]},
            {"name": "Vulnerabilities", "count": counts["vulnerabilities"]},
            {"name": "Malware", "count": counts["malware"]},
            {"name": "Reports", "count": counts["reports"]},
            {"name": "Actors", "count": counts["actors"]},
        ],
        "reports": reports,
        "indicators": indicators,
        "series": series,
        "indicator_mix": mix,
        "sources": sources,
        "brief": {
            "number": 1,
            "window": (generated - timedelta(days=7)).strftime("%d %b") + " – " + generated.strftime("%d %b %Y"),
            "headline": headline,
            "summary": summary,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the public Aruba Threat Radar snapshot")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output JSON path")
    parser.add_argument("--pretty", action="store_true", help="indent the JSON")
    args = parser.parse_args()

    token = os.environ.get("OPENCTI_TOKEN", "").strip()
    if not token:
        log("OPENCTI_TOKEN is not set")
        return 2
    url = os.environ.get("OPENCTI_URL", "http://127.0.0.1:8080")

    gql = GraphQL(url, token)
    snapshot = build_snapshot(gql)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2 if args.pretty else None, ensure_ascii=False))
    tmp.replace(out)

    log(f"wrote {out} ({out.stat().st_size} bytes)")
    log(
        "counts: "
        + ", ".join(f"{k}={v}" for k, v in snapshot["kpis"].items())
        if isinstance(snapshot["kpis"], dict)
        else ""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
