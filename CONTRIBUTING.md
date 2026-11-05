# Contributing

This project is useful only if it stays accurate and local. Contributions are welcome in four shapes.

## 1. Corrections

If a briefing, timeline entry or source description is wrong:

- open an issue with the exact sentence, the correction and a public source;
- corrections are published with a dated note, not silently edited.

## 2. Sources

Suggest a feed or connector if it meets all of these:

- public or licensable for redistribution at TLP:CLEAR;
- maintained (last update within 90 days);
- adds signal the current set does not have — especially Caribbean, Dutch or Papiamento-language sources;
- does not require an API key that nobody owns.

Include the URL, licence, update cadence and a sample record. A source that cannot be licensed for public output can still be useful inside OpenCTI; say so and it will be tagged as platform-only.

## 3. Incident reports

If you run an organisation on the island and want to contribute an incident:

- use the repository's private security advisory channel, not a public issue;
- describe the timeline, the technique and the impact — not the victim's identity;
- attach headers, URLs or hashes only if you have the right to share them;
- say whether you want to be credited, anonymised or not mentioned.

Victim identities and personal data are never published.

## 4. Code

- Keep the platform and the publication separated: nothing in `site/` may hold an OpenCTI token.
- Pin image versions in `docker-compose.yml`; connectors may track `latest`.
- Update the relevant document in `docs/` in the same pull request.
- Test with `npm run build` and one collector run before opening the PR.
- No new third-party JavaScript on the public site without a privacy note.

## Style

- English for code and docs; Dutch and Papiamento summaries are welcome in briefings.
- Claims need sources. Assessments need to be labelled as assessments.
- Prefer a clear sentence over a clever one. This is intelligence, not marketing.

## Security

Do not open a public issue for a vulnerability. Use the private advisory channel. Never paste live credentials, API keys or victim data into an issue.
