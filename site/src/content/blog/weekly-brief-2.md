---
title: "Weekly brief 2: the graph grew a memory"
description: "The week the platform stopped counting only indicators: 746 malware families, 185 intrusion sets, 58 campaigns, and 1,768 known-exploited vulnerabilities in the Aruba radar."
date: 2026-11-05
tags: [CTI, Aruba, Weekly Brief]
summary_nl: "Deze week kreeg het platform context: 746 malwarefamilies, 185 intrusiesets en 58 campagnes uit MITRE ATT&CK, naast 1.853 indicatoren en 1.768 kwetsbaarheden. De nadruk ligt nu op wat lokale organisaties deze week moeten patchen en waarom MFA alleen niet genoeg is."
summary_pap: "E siman aki e plataforma a haña konteksto: 746 famia di malware, 185 intrusionset y 58 campaña for di MITRE ATT&CK, huntu cu 1.853 indicador y 1.768 vulnerabilidad. E foco awor ta riba kiko organisacionnan lokal mester patch e siman aki y dicon MFA so no ta suficiente."
---

The first weekly brief counted what arrived. This one can finally describe **who** is in the graph, not only how many indicators passed through it.

## The week in numbers

| Metric | Total |
| --- | ---: |
| Reports | 5 |
| Indicators | 1,853 |
| Observables | 3,934 |
| Malware families | 746 |
| Intrusion sets | 185 |
| Campaigns | 58 |
| Known-exploited vulnerabilities | 1,768 |

The malware and actor counts are not new intelligence from Aruba. They are the MITRE ATT&CK baseline finally landing: the connector had been registering with an invalid scope, so OpenCTI accepted it and then dropped the bundle. The fix was one line in `docker-compose.yml` and a state reset. The lesson is uncomfortable: a connector can look healthy while importing nothing.

## What changed

- **The ATT&CK baseline is complete enough to use.** 746 malware families, 96 tools, 185 intrusion sets and 58 campaigns. That turns the graph from an indicator list into something an analyst can pivot through.
- **KEV coverage is now the vulnerability baseline.** 1,768 known-exploited vulnerabilities, all from CISA KEV. There is no "all vulnerabilities" delta yet because no NVD feed is connected; do not read the total as a full vulnerability inventory.
- **The feed mix is still URL-heavy.** Phishing URLs dominate because that is what the local threat looks like. Botnet IPs are context, not the main event.
- **Feed endpoints remain the weakest link.** URLhaus was retired upstream; Phishunt and RansomLook replaced it. Verify endpoints, not dashboards.

## What to do this week

- Patch the KEV entries that match your internet-facing estate first. The list is prioritisation, not a score.
- Treat an unsolicited MFA prompt as an incident, not an annoyance. The 2025 wave used adversary-in-the-middle kits that relayed the session after the code was entered.
- If you run a school, hotel or clinic, check inbox rules and forwarding for accounts that authenticate from a new country. That is where the persistence usually hides.
- Send a local phishing sample to the radar instead of forwarding it in a WhatsApp group. One sample with headers is worth more than fifty screenshots.

## The regional picture

The July–August 2025 incidents remain the reference case: the Joint Court of Justice, Curaçao's Tax and Customs Administration, Aruba's Parliament, and the national phishing warning from Korps Politie Aruba and Veiligheidsdienst Aruba. The radar's [timeline](https://kevinflorencio.github.io/opencti-aruba/#timeline) keeps the public record; the briefings explain the techniques.

## Sources

- [Aruba Threat Radar](https://kevinflorencio.github.io/opencti-aruba/)
- [Source catalogue](https://kevinflorencio.github.io/opencti-aruba/sources/)
- [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
- [MITRE ATT&CK](https://attack.mitre.org/)

*Next brief: Monday. The platform drafts it; a human still has to decide what matters.*
