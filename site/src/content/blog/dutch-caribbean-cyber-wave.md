---
title: "The week the Dutch Caribbean woke up"
description: "Between 22 and 31 July 2025, a court, a tax administration and a parliament across the Dutch Caribbean were hit in quick succession. What the wave reveals about shared exposure — and what to fix first."
published: 2025-07-31
tags: ["incident analysis", "Dutch Caribbean", "ransomware", "phishing"]
summary_nl: "Tussen 22 en 31 juli 2025 werden een rechtbank, de belastingdienst van Curaçao en het parlement van Aruba binnen tien dagen getroffen. Deze briefing reconstrueert de publieke tijdlijn, scheidt wat bekend is van wat niet bekend is, en legt uit welke vijf maatregelen organisaties deze week moeten nemen."
summary_pap: "Entre 22 y 31 di juli 2025, un corte, e departamento di impuesto di Kòrsou y e parlamento di Aruba a ser gherá den dies dia. E análisis aki ta rekonstruí e timeline públiko, separá loke nos sa di loke nos no sa, y ta splika kua sinku medidanan organisacionnan mester tuma e siman aki."
sources:
  - label: "The Record — Dutch Caribbean islands respond to cyberattacks on courts, tax departments (Aug 2025)"
    url: "https://therecord.media/aruba-curacao-governments-cyberattacks"
  - label: "NL Times — Ransomware attacks cripple government services across Dutch Caribbean islands (2 Aug 2025)"
    url: "https://nltimes.nl/2025/08/02/ransomware-attacks-cripple-government-services-across-dutch-caribbean-islands"
  - label: "Aruba.nu — Arubaans parlement getroffen door cyberaanval (31 Jul 2025)"
    url: "https://www.aruba.nu/nieuws/algemeen/77709/arubaans-parlement-getroffen-door-cyberaanval"
  - label: "Government of Aruba — Nationale waarschuwing: gevaarlijke phishing e-mails in omloop (13 Aug 2025)"
    url: "https://www.gobierno.aw/nl/nationale-waarschuwing-gevaarlijke-phishing-e-mails-in-omloop-op-aruba"
  - label: "HackCuraçao — August 2025 cybersecurity roundup"
    url: "https://hackcuracao.com/cybersecurity/august-2025-cybersecurity-roundup-caribbean"
---

For a region of roughly 300,000 people, the last week of July 2025 was a compressed course in why cyber resilience is not an abstract policy theme. Within ten days, three institutions in three different countries of the Dutch Caribbean reported serious incidents. None of them was a bank or a technology company. They were the institutions that make a state function: a court, a tax administration and a parliament.

This briefing reconstructs the public timeline, separates what is known from what is not, and draws out the lessons that apply to every organisation on the islands — not just government.

## The timeline

| Date (2025) | Event | What was publicly reported |
|---|---|---|
| 22 July | Dutch Public Prosecution Service disconnects | The OM took itself off the internet for several weeks after an NCSC alert about a potential Citrix NetScaler vulnerability used for remote access. |
| 23 July | Joint Court of Justice hit | The court serving the six Dutch Caribbean islands suffered a cyberattack that disrupted email systems and court proceedings. |
| 24 July | Curaçao Tax and Customs Administration | Ransomware. Vehicle-tax processing, telephone support and in-person service went down. The public filing portal was deliberately kept online. |
| 31 July | Aruba Parliament | One official email account was compromised through phishing. Parliament warned the public not to open links or attachments in messages that appeared to come from it. |
| 5 August | Parliament follow-up | A second warning described a phishing email circulating locally, designed to steal sensitive information, and noted that local organisations were affected too. |
| 13 August | National warning | Aruba's police corps (KPA) and security service (VDA) issued a national phishing warning after a significant increase in compromised accounts. |

The sequencing matters. The Dutch OM's Citrix NetScaler alert on 22 July is the first public signal in the chain. It is not proof that the same vulnerability was used against the islands — no public report makes that claim — but it is a reminder that the kingdom's critical infrastructure is operationally linked. A warning in The Hague is relevant in Willemstad and Oranjestad within hours, not weeks.

## What we know, and what we do not

Three things are well supported by public reporting:

1. **The incidents were real and operational.** Court proceedings were disrupted, tax services were unavailable for days, and a parliamentary email account was used to send or spread phishing. These are not speculative "attempts".
2. **The Curaçao tax incident was ransomware.** The Minister of Finance confirmed ransomware; the public portal was kept online while back-office functions were restored. Recovery involved Dutch IT security specialists and took close to two weeks according to regional reporting.
3. **The Aruba incidents were credential-focused.** Parliament's account was compromised through phishing, and the national warning describes messages arriving from known contacts, using Adobe, DocuSign and SharePoint lures, explicitly designed to bypass Microsoft Authenticator.

What we do **not** know publicly: who was behind each incident, whether they are linked, what the initial access vector was for the court or the tax office, and whether data was exfiltrated beyond what has been disclosed. Anyone who fills those gaps without evidence is selling a narrative, not intelligence.

## Why one week produced three incidents

Small islands have a structural intelligence problem: each institution sees only its own logs. A phishing campaign that hits the court on Wednesday and the tax office on Thursday looks like two unrelated events to the victims, and like a campaign to nobody, because there is no shared picture.

The shared exposure is real:

- **Common service providers.** Courts, tax offices and ministries across the kingdom often depend on the same vendors, the same Microsoft tenancies and the same remote-access appliances.
- **Shared language and lures.** Phishing in Papiamento, Dutch and English can be reused across Aruba, Curaçao and Sint Maarten with minimal effort. The same email works on all three islands.
- **Thin defensive depth.** A handful of IT staff cannot cover identity, endpoint, network and incident response at once. Detection engineering and threat hunting are usually the first capabilities to go when headcount is limited.
- **Tourism-shaped economies.** Hospitality, retail and government interact constantly. A compromised hotel mailbox is a supply-chain foothold into tour operators, airlines and public services.

That combination is exactly what opportunistic criminal groups look for: high-value institutions, low inspection, and a time zone that lets them work while the rest of the kingdom sleeps.

## The part that should worry you more than ransomware

Ransomware is loud. It encrypts files, takes down services and generates headlines. The Aruba incidents were quiet. An email account compromised through phishing can sit undetected for weeks, forwarding invoices, reading board mail and sending convincing follow-ups to contacts.

The 13 August national warning is unusually direct about the mechanism: the messages come **from someone you know**, use **urgent language**, and are designed to **bypass Microsoft Authenticator**. That last phrase is the important one. It describes adversary-in-the-middle phishing, where the attacker proxies the real Microsoft login page, captures the session cookie after MFA succeeds, and replays it from their own machine. The password and the MFA code are both correct. The attacker is simply already inside the session.

We cover the mechanics in [MFA is not a wall](/blog/mfa-is-not-a-wall/). For this briefing, the operational consequence is simple: if your incident response plan assumes "MFA stopped it", it did not.

## What to fix first

**This week, not this quarter:**

1. **Find every account that can send as the organisation.** Executives, press, finance, shared mailboxes. Enrol them in phishing-resistant MFA (passkeys or FIDO2). Password-plus-push is no longer a control against AiTM.
2. **Turn on session protection.** Conditional Access with token protection where licensed, strict device compliance, and a tested "revoke all sessions" procedure. When a user reports a phishing click, revoke first and investigate second.
3. **Alert on the quiet persistence.** New inbox rules, new OAuth application consents, MFA method changes, mailbox delegation changes. These are the artefacts attackers leave when they want to stay.
4. **Verify your backups by restoring one.** Not by reading a dashboard. Pick a domain controller or a finance file share and restore it in an isolated network. The Curaçao recovery took outside specialists; you do not want to discover your backup is unusable during that call.
5. **Write the first hour.** Who declares an incident, who isolates a host, who talks to the minister, who talks to the press. A one-page decision tree beats a 60-page plan nobody has read.

**This quarter:**

- Inventory internet-facing appliances — Citrix, VPN, RMM, mail gateways — and confirm their patch level against CISA KEV.
- Run a tabletop with a phishing scenario that starts from a compromised mailbox, not from malware.
- Join or form an information-sharing group with other local organisations. The fastest warning you will ever get is a peer who saw the same email an hour earlier.

## Why we are publishing this

This is the gap the Aruba Threat Radar exists to close. There is no dedicated, consistent, public source of threat intelligence for Aruba and the wider Dutch Caribbean. Incidents are reported in fragments, in different languages, on different platforms, and often without follow-up. Clients and citizens are left to guess.

We are not going to invent attribution or inflate numbers to look busy. We will publish what is sourced, label what is assessed, and keep a public timeline of incidents that affect the islands. The radar is the structured layer; these briefings are the context.

If your organisation was affected by the July–August wave and wants to contribute details anonymously, the contact route is on the [about page](/about/#contact). Victim identities are not published.

---

*Published 31 July 2025. Updated 5 November 2026 with the national warning of 13 August 2025 and platform context.*
