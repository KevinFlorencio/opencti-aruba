---
title: "MFA is not a wall"
description: "Aruba's national phishing warning said the attackers could bypass Microsoft Authenticator. That is not a bug in MFA — it is the signature of adversary-in-the-middle phishing. Here is how the machinery works, and what actually stops it."
published: 2025-08-13
tags: ["tradecraft", "phishing", "AiTM", "identity"]
sources:
  - label: "Government of Aruba — Nationale waarschuwing: gevaarlijke phishing e-mails in omloop op Aruba (13 Aug 2025)"
    url: "https://www.gobierno.aw/nl/nationale-waarschuwing-gevaarlijke-phishing-e-mails-in-omloop-op-aruba"
  - label: "Sekoia — Tycoon 2FA: an in-depth analysis of the latest version of the AiTM phishing kit"
    url: "https://blog.sekoia.io/tycoon-2fa-an-in-depth-analysis-of-the-latest-version-of-the-aitm-phishing-kit/"
  - label: "Barracuda — Email Threat Radar, September 2025"
    url: "https://blog.barracuda.com/2025/09/23/email-threat-radar-september-2025"
  - label: "Proofpoint via SecurityBrief — fake Microsoft OAuth apps used in AiTM campaigns (Aug 2025)"
    url: "https://securitybrief.asia/story/phishing-campaign-uses-fake-microsoft-apps-to-bypass-mfa"
  - label: "CIS / MS-ISAC — Member-reported phishing likely from Tycoon2FA PhaaS (29 Oct 2025)"
    url: "https://www.cisecurity.org/insights/blog/ms-isac-member-reported-phishing-likely-from-tycoon2fa-phaas"
---

On 13 August 2025, the Government of Aruba published a national warning that deserves to be read closely. It described a persistent wave of phishing emails, arriving from familiar contacts, using Adobe, DocuSign and SharePoint as lures, and — in the government's own words — capable of **bypassing extra security such as Microsoft Authenticator**.

That sentence is not an admission that MFA failed. It is a precise description of a technique that has become the default playbook for criminal account takeover: **adversary-in-the-middle (AiTM) phishing**. Understanding it is the difference between adding another prompt to the login flow and actually closing the door.

## The illusion: you are logging into the real thing

In a classic phishing page, the attacker copies the login form and hopes the victim does not notice the URL. MFA breaks that model, because the stolen password alone is not enough.

AiTM removes the copy. The attacker stands between the victim and the real service:

1. The victim clicks a link and lands on `login.microsoftonline.com.<attacker-domain>` — or, increasingly, a legitimate cloud service abused as a redirector.
2. The page is served by a **reverse proxy** controlled by the attacker. It looks like Microsoft because it is Microsoft: every request is forwarded to the real login endpoint, and the real page is returned.
3. The victim enters their password. The proxy relays it. Microsoft asks for the MFA challenge. The victim completes it on their phone. Microsoft issues the session.
4. The proxy relays the response back — and quietly copies the **session cookies** (`ESTSAUTH`, `ESTSAUTHPERSISTENT`, and friends) before they reach the victim's browser.
5. The attacker imports those cookies into their own browser. Microsoft sees a valid, MFA-satisfied session. No password prompt, no push notification, no code.

This is why the warning tells people to change their password **and log out of all devices**. Changing the password does not invalidate an already-issued session cookie. Ending the sessions does.

## Tycoon 2FA and the industrialisation of the attack

The kit class behind much of this activity is sold as phishing-as-a-service. **Tycoon 2FA** has been tracked since at least August 2023 and is designed to harvest Microsoft 365 and Google session cookies in real time. Sekoia's analysis documents the evolution: anti-bot checks, obfuscated JavaScript, encoded URLs, Telegram-based exfiltration and a management panel that lets a customer without deep technical skill run a campaign.

The scale is not marginal. Barracuda recorded roughly one million PhaaS attacks in January–February 2025, with Tycoon 2FA accounting for about 89% of them. Proofpoint observed more than 50 impersonated Microsoft OAuth applications and nearly 3,000 attempted compromises across more than 900 environments in 2025, with a confirmed success rate above 50%. In October 2025, CIS's MS-ISAC team reported an increase in member-submitted phishing in August and September that it assessed with moderate confidence as Tycoon2FA-linked.

None of those reports attribute the Aruba wave to a specific kit, and neither do we. What they establish is that the capability is cheap, widespread and effective — exactly the conditions under which a small-island campaign becomes likely.

## Why "we have MFA" is the wrong sentence

MFA answers the question *"is this the right person?"* at the moment of login. AiTM attacks do not break that answer. They steal the **result** of a successful answer.

The practical consequences:

- **Push-based MFA is not phishing-resistant.** A real push approved on a real phone during a real login is still a valid authentication event. The attacker simply reuses the session.
- **Number matching helps against MFA fatigue, not against proxying.** It reduces accidental approvals; it does not stop a proxy that relays the correct number.
- **Password managers help, but are not enough.** They refuse to autofill on lookalike domains, which blocks many campaigns — but a user who types the password manually, or a campaign hosted on a trusted cloud domain, can still get through.
- **Email security filters are necessary but leaky.** The lures arrive from compromised legitimate accounts, which is precisely the traffic a filter is most inclined to trust.

## What actually raises the cost

**1. Phishing-resistant authentication.** FIDO2 security keys and passkeys are bound to the origin. A proxy on `login-microsoft.com.evil.tld` cannot produce a valid assertion for `login.microsoftonline.com`, so there is nothing to relay. This is the single highest-leverage control. Prioritise it for anyone who can send email as the organisation, approve payments, or administer tenancies.

**2. Token protection.** Microsoft Entra ID's token protection (where licensed) binds session tokens to the device. A stolen cookie replayed from another machine fails. Pair it with Continuous Access Evaluation so revocation takes effect in near real time rather than waiting for token expiry.

**3. Session revocation as a reflex.** The moment a user reports a suspicious login or a phishing click, the response should be: revoke refresh tokens and sessions, reset the password, then investigate. Not "wait and see". Every minute a stolen cookie is valid is a minute of mailbox access.

**4. Hunt for the quiet persistence.** After a mailbox takeover, attackers rarely announce themselves. They add inbox rules to hide replies, delegate access, register a new MFA method, or consent an OAuth application. Alert on:

- new inbox rules that move or delete messages matching finance, invoice, payment or "phishing";
- new OAuth application consents, especially with mail or offline-access scopes;
- MFA method changes and new device registrations;
- mailbox delegation and forwarding changes;
- sign-ins with valid tokens from unfamiliar ASNs, countries or user agents.

**5. Make reporting fast and blameless.** The Aruba warning's first instruction is to change the password immediately and end all sessions. That only works if people report quickly. A one-click report button, a phone number that a receptionist can call, and a promise that nobody gets fired for clicking are controls, not soft skills.

**6. Assume the mailbox is a supply-chain weapon.** Once inside, the attacker reads the thread, waits for the right moment, and replies from the real account. Finance teams should verify payment changes **out of band**, on a number they already have — never on a number supplied in the email.

## A 60-minute checklist for this week

- [ ] List every account with mailbox delegation or "send as" rights. Confirm MFA method and last sign-in.
- [ ] Enable alerts for new inbox rules, new OAuth consents and MFA method changes.
- [ ] Test the "revoke sessions" runbook on a test account. Time it.
- [ ] Check Conditional Access: block legacy auth, require compliant devices for email, enforce sign-in risk.
- [ ] Brief finance and front-desk staff on the callback rule, in the language they actually use at work.
- [ ] Report one real phishing sample to KPA and to your provider. Reporting is how the next warning gets written.

## The uncomfortable conclusion

The Aruba warning is a good piece of public communication: it names the lures, explains the mechanism in plain language, and gives concrete steps. But it also marks a threshold. The attackers are no longer trying to break encryption or find a zero-day. They are renting a proxy for a few hundred dollars and waiting for someone to click.

The defence is not more awareness posters. It is a shift from **"prove who you are once"** to **"prove that this session, on this device, is still yours"**. Organisations that make that shift — starting with the accounts that matter most — will watch the same campaigns arrive and fail.

---

*Published 13 August 2025. Updated 5 November 2026 with MS-ISAC reporting and current mitigation guidance.*
