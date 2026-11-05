#!/usr/bin/env python3
"""
Seed the OpenCTI graph with the curated Aruba / Dutch Caribbean baseline.

Creates a small STIX 2.1 bundle (campaign, tool, locations, reports) and pushes
it through OpenCTI's stixBundlePush mutation. Idempotent: deterministic STIX IDs
mean a second run updates the same objects instead of duplicating them.

Usage:
    OPENCTI_TOKEN=... python3 scripts/seed_aruba.py --dry-run
    OPENCTI_TOKEN=... python3 scripts/seed_aruba.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NS = uuid.UUID("7c1e2f5a-4b3d-4c8e-9f10-a1b2c3d4e5f6")
CREATED = "2026-11-05T00:00:00.000Z"


def sid(kind: str, name: str) -> str:
    return f"{kind}--{uuid.uuid5(NS, name)}"


def obj(kind: str, key: str, **fields) -> dict:
    base = {
        "type": kind,
        "spec_version": "2.1",
        "id": sid(kind, key),
        "created": CREATED,
        "modified": CREATED,
    }
    base.update(fields)
    return base


def build_bundle() -> dict:
    author = obj(
        "identity",
        "Aruba Threat Radar",
        name="Aruba Threat Radar",
        identity_class="organization",
        description=(
            "Independent, non-commercial threat intelligence initiative for Aruba, "
            "Curaçao, Bonaire and Sint Maarten. Publishes at TLP:CLEAR."
        ),
        external_references=[
            {"source_name": "github", "url": "https://github.com/KevinFlorencio/opencti-aruba"}
        ],
    )

    locations = [
        obj("location", "Aruba", name="Aruba", location_type="country", x_opencti_aliases=["AW"]),
        obj("location", "Curaçao", name="Curaçao", location_type="country", x_opencti_aliases=["CW"]),
        obj(
            "location",
            "Bonaire",
            name="Bonaire",
            location_type="region",
            description="Special municipality of the Netherlands in the Caribbean.",
        ),
        obj("location", "Sint Maarten", name="Sint Maarten", location_type="country", x_opencti_aliases=["SX"]),
    ]

    campaign = obj(
        "campaign",
        "Dutch Caribbean phishing and ransomware wave (Jul-Aug 2025)",
        name="Dutch Caribbean phishing and ransomware wave (Jul-Aug 2025)",
        description=(
            "A cluster of incidents across the Dutch Caribbean between 22 July and 13 August 2025: "
            "a cyberattack on the Joint Court of Justice serving six islands, ransomware at Curaçao's "
            "Tax and Customs Administration, and phishing compromise of an Aruban Parliament email "
            "account followed by a national phishing warning from KPA and VDA. Public reporting does "
            "not establish a single actor or a single intrusion vector across all three; treat this as "
            "an analytical cluster, not an attribution."
        ),
        first_seen="2025-07-22T00:00:00.000Z",
        last_seen="2025-08-13T00:00:00.000Z",
        objective=(
            "Credential and mailbox access for follow-on fraud, plus ransomware against government "
            "services with weak segmentation and recovery capability."
        ),
        confidence=60,
        aliases=["July 2025 Dutch Caribbean cyber wave"],
        labels=["aruba", "curaçao", "dutch caribbean", "phishing", "ransomware"],
        created_by_ref=author["id"],
    )

    tool = obj(
        "tool",
        "Tycoon 2FA",
        name="Tycoon 2FA",
        description=(
            "Adversary-in-the-middle phishing-as-a-service kit first observed in 2023. Proxies the "
            "real Microsoft 365 or Google login page, captures the post-MFA session cookie and lets "
            "the operator replay the session. Public reporting does not attribute the Aruba incidents "
            "to this kit specifically; it is included as the dominant tradecraft pattern in the "
            "regional warning period."
        ),
        tool_types=["credential-exploitation"],
        aliases=["Tycoon2FA", "Tycoon 2FA PhaaS"],
        labels=["phishing", "aitm", "phaas", "mfa-bypass"],
        created_by_ref=author["id"],
    )

    report_wave = obj(
        "report",
        "The July-August 2025 Dutch Caribbean cyber wave",
        name="The July-August 2025 Dutch Caribbean cyber wave",
        published="2025-08-13T00:00:00.000Z",
        report_types=["threat-report"],
        description=(
            "Regional incident report covering the Joint Court of Justice attack (23 July), the "
            "Curaçao Tax and Customs Administration ransomware incident (24 July), the Aruba "
            "Parliament email compromise (31 July) and the national phishing warning issued by "
            "KPA and VDA (13 August). Sources: The Record, NL Times, Aruba.nu, Gobierno di Aruba."
        ),
        confidence=75,
        labels=["aruba", "curaçao", "dutch caribbean", "phishing", "ransomware", "aitm"],
        object_refs=[campaign["id"], tool["id"], *[loc["id"] for loc in locations]],
        created_by_ref=author["id"],
    )

    report_aruba = obj(
        "report",
        "Aruba Parliament phishing compromise and national warning",
        name="Aruba Parliament phishing compromise and national warning",
        published="2025-08-13T00:00:00.000Z",
        report_types=["threat-report"],
        description=(
            "On 31 July 2025 the Aruban Parliament warned that one of its official email accounts "
            "had been compromised through phishing. On 13 August 2025 the Korps Politie Aruba (KPA) "
            "and Veiligheidsdienst Aruba (VDA) issued a national warning describing phishing from "
            "known contacts, Adobe/DocuSign/SharePoint lures, and attempts to bypass Microsoft "
            "Authenticator. The warning advises password resets, ending all sessions, avoiding "
            "Outlook web and reporting to KPA."
        ),
        confidence=80,
        labels=["aruba", "phishing", "mfa-bypass", "government"],
        object_refs=[campaign["id"], tool["id"], locations[0]["id"]],
        created_by_ref=author["id"],
    )

    return {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid5(NS, 'aruba-seed-bundle-v1')}",
        "spec_version": "2.1",
        "objects": [author, *locations, campaign, tool, report_wave, report_aruba],
    }


def gql(url: str, token: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        url.rstrip("/") + "/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    if body.get("errors"):
        raise RuntimeError(body["errors"][0].get("message"))
    return body["data"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="write the bundle locally, do not push")
    parser.add_argument("--connector-id", default="6c7566e3-9665-48cc-bde9-68b24d652c38")
    args = parser.parse_args()

    bundle = build_bundle()
    out = ROOT / "data" / "aruba-seed.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False))
    print(f"wrote {out} ({len(bundle['objects'])} objects)", file=sys.stderr)

    if args.dry_run:
        return 0

    token = os.environ.get("OPENCTI_TOKEN", "").strip()
    if not token:
        print("OPENCTI_TOKEN is not set", file=sys.stderr)
        return 2
    url = os.environ.get("OPENCTI_URL", "http://127.0.0.1:8080")

    data = gql(
        url,
        token,
        "mutation Push($bundle: String!, $connectorId: String!) { stixBundlePush(bundle: $bundle, connectorId: $connectorId) }",
        {"bundle": json.dumps(bundle, ensure_ascii=False), "connectorId": args.connector_id},
    )
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
