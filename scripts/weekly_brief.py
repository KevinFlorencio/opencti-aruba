#!/usr/bin/env python3
"""Generate a weekly brief draft from the public radar snapshot.

The draft is written to drafts/ for review. Pass --publish to place it in the
Astro content collection instead. This is deliberately not fully automatic:
numbers can be generated, judgement cannot.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "site" / "public" / "data" / "latest.json"
HISTORY = ROOT / "data" / "history"
DRAFTS = ROOT / "drafts"
CONTENT = ROOT / "site" / "src" / "content" / "blog"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def previous_snapshot() -> dict | None:
    files = sorted(HISTORY.glob("*.json"))
    if len(files) < 2:
        return None
    return load(files[-2])


def fmt_delta(current: int, previous: int | None) -> str:
    if previous is None:
        return "—"
    delta = current - previous
    return f"{delta:+,}"


def table(rows: list[tuple[str, str, str]]) -> str:
    body = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows)
    return "| Metric | This week | Change |\n| --- | ---: | ---: |\n" + body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="write into the blog content collection")
    parser.add_argument("--number", type=int, help="optional label (default: ISO week)")
    args = parser.parse_args()

    if not SNAPSHOT.exists():
        raise SystemExit(f"missing snapshot: {SNAPSHOT}")

    data = load(SNAPSHOT)
    kpis = data["kpis"]
    now = datetime.now(timezone.utc).astimezone()
    HISTORY.mkdir(parents=True, exist_ok=True)
    history_file = HISTORY / f"{now:%Y-%m-%d}.json"
    if not history_file.exists():
        shutil.copy(SNAPSHOT, history_file)

    prev = previous_snapshot()
    pk = prev["kpis"] if prev else {}

    iso = now.isocalendar()
    number = args.number or iso.week
    slug = f"{iso.year}-W{iso.week:02d}"

    rows = []
    for key, label in [
        ("reports", "Reports"),
        ("indicators", "Indicators"),
        ("observables", "Observables"),
        ("vulnerabilities", "Known exploited vulnerabilities"),
        ("malware", "Malware families"),
        ("actors", "Threat actors"),
        ("campaigns", "Campaigns"),
    ]:
        current = int(kpis.get(key, 0))
        rows.append((label, f"{current:,}", fmt_delta(current, pk.get(key))))

    mix = data.get("indicator_mix") or []
    mix_rows = "\n".join(f"| {m['label']} | {m['count']:,} |" for m in mix) or "| — | — |"

    title = f"Weekly brief — week {number}, {iso.year}"
    description = (
        f"What the Aruba Threat Radar ingested in the week to {now:%d %B %Y}: "
        f"{kpis.get('indicators', 0):,} indicators, {kpis.get('vulnerabilities', 0):,} "
        "known-exploited vulnerabilities, and the regional incidents worth acting on."
    )

    body = f"""---
title: "{title}"
description: "{description}"
date: {now:%Y-%m-%d}
tags: [CTI, Aruba, Weekly Brief]
---

The numbers below come from the platform snapshot generated at {data.get('generated_at', 'unknown')}. They describe what the feeds delivered, not what an adversary did. Read them as a coverage check, then read the incidents.

## The week in numbers

{table(rows)}

## Indicator mix

| Observable type | Count |
| --- | ---: |
{mix_rows}

## What changed

<!-- Analyst: replace this with the two or three changes that matter. -->
- The automated delta is in the table above. Check the radar's [incident timeline](https://kevinflorencio.github.io/opencti-aruba/#timeline) for the regional picture.
- Verify the feed-health panel before drawing conclusions: a quiet week and a broken connector look identical in a count.

## What to do this week

- Patch the CISA KEV entries that match your estate; the count is a backlog, not a badge.
- Treat unsolicited MFA prompts and "Microsoft" landing pages as hostile until proven otherwise.
- Report a local phishing sample to the radar instead of forwarding it in WhatsApp groups.

## Sources

- [Aruba Threat Radar](https://kevinflorencio.github.io/opencti-aruba/)
- [Source catalogue](https://kevinflorencio.github.io/opencti-aruba/sources/)
- [OpenCTI graph](https://github.com/KevinFlorencio/opencti-aruba) (LAN-only)
"""

    DRAFTS.mkdir(parents=True, exist_ok=True)
    out = DRAFTS / f"weekly-brief-{slug}.md"
    out.write_text(body)
    print(f"[weekly] draft written: {out}")

    if args.publish:
        target = CONTENT / f"weekly-brief-{slug}.md"
        target.write_text(body)
        print(f"[weekly] published: {target}")
        print("[weekly] rebuild the site locally, then sync site/dist to the radar VM")


if __name__ == "__main__":
    main()
