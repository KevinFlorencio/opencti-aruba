---
title: "Weekly Brief #1 — the radar goes live"
description: "What the platform ingested in its first cycle, why the indicator mix is URL-heavy, and the three things an Aruban organisation should do this week."
published: 2026-11-05
tags: ["weekly brief", "Aruba", "CTI"]
sources:
  - label: "Aruba Threat Radar — live snapshot"
    url: "https://github.com/KevinFlorencio/opencti-aruba"
  - label: "CISA Known Exploited Vulnerabilities catalog"
    url: "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
  - label: "Government of Aruba — national phishing warning (13 Aug 2025)"
    url: "https://www.gobierno.aw/nl/nationale-waarschuwing-gevaarlijke-phishing-e-mails-in-omloop-op-aruba"
  - label: "CIS / MS-ISAC — Tycoon2FA PhaaS activity (29 Oct 2025)"
    url: "https://www.cisecurity.org/insights/blog/ms-isac-member-reported-phishing-likely-from-tycoon2fa-phaas"
---

**Window:** 30 October – 5 November 2026 · **Classification:** TLP:CLEAR · **Platform:** OpenCTI 7 + MISP, first full ingestion cycle

This is the first weekly brief. It is short on narrative because the platform is one day old; the useful content is the baseline. Next week we can talk about change.

## What the platform ingested

At the time of writing, after the first feed cycle:

| Metric | Value |
|---|---|
| MISP events | 160 |
| MISP attributes | 12,639 |
| OpenCTI reports | 4 |
| OpenCTI indicators | 438 |
| Observables | 804 |
| Known-exploited vulnerabilities (CISA KEV) | 950 |
| Campaigns | 1 (the Jul–Aug 2025 Dutch Caribbean wave) |
| Enabled feeds | 6 |

The indicator mix is **over 400 URLs and a handful of IPv4 addresses**. That is not a coincidence: the feed set enabled on day one — URLhaus, OpenPhish, Feodo, CIRCL, Botvrij, ET — is URL- and IP-centric. It reflects what those feeds collect, not what is targeting Aruba.

**Read this as a starting line, not a threat level.** A radar that only sees URLs will miss malware hashes, TLS certificates, e-mail sender infrastructure and the identity-layer signals that mattered in the 2025 incidents. Adding MISP galaxies, malware feeds and a certificate-transparency source is the next coverage job.

## The regional picture

No new publicly reported Aruban incident entered the source set this week. That is a **reporting gap, not a clean bill of health**: most local incidents are not published, and the ones that are often appear weeks later in Dutch or Papiamento outlets.

What remains on the board is the July–August 2025 wave:

- the Joint Court of Justice attack across six islands;
- ransomware at Curaçao's Tax and Customs Administration;
- the Aruba Parliament mailbox compromise and the KPA/VDA national warning that followed.

The pattern from that period — phishing from known contacts, AiTM session theft, MFA bypass, then mailbox-driven follow-on fraud — is still the most likely local playbook. Nothing in this week's feed data contradicts it.

## Three things to do this week

1. **Patch what is actually exploited.** Filter the CISA KEV list against your internet-facing inventory. If a KEV entry matches an appliance you cannot patch this week, document the compensating control and the date you will patch it. "We will get to it" is not a control.
2. **Move the accounts that matter to phishing-resistant MFA.** Executives, finance, press, anyone who can send as the organisation. Passkeys or FIDO2. Password-plus-push is the exact configuration the 2025 Aruba warning described as bypassable.
3. **Rehearse session revocation.** Pick a test account, simulate a reported phishing click, and time how long it takes to revoke sessions, reset the password, check inbox rules and confirm no OAuth consent was granted. If it takes more than 15 minutes, fix the runbook now, not during an incident.

## What changes next week

- Enable MISP galaxies and object templates so malware and actor context survives the import.
- Add a certificate-transparency source for lookalike domains of `.aw` properties.
- Publish the first OpenCTI analyst dashboard (regional watchlist, KEV exposure, feed health).
- Review false positives from the URL feeds before the indicator count becomes noise.

## A note on numbers

The KPI values on the radar move as feeds cache and the connector imports. The snapshot records `generated_at`; treat any number without that timestamp as decoration. The platform is designed to show its own freshness, and it will show when it is stale.

---

*Corrections and source suggestions: open an issue on the repository. Sensitive reports: use the private security advisory channel.*
