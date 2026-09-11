# reachability

Source repository: [alpha-omega-security/scrutineer](https://github.com/alpha-omega-security/scrutineer)

Canonical key: `alpha-omega-security/scrutineer:skills/reachability`

Manifest: [https://github.com/alpha-omega-security/scrutineer/blob/main/skills/reachability/SKILL.md](https://github.com/alpha-omega-security/scrutineer/blob/main/skills/reachability/SKILL.md)

## Description

Check whether known sinks in this application's dependencies are reachable from its own trust boundaries. Scrutineer already holds findings against the libraries this app uses; this skill traces each one from the app's entry points to the library call and reports the ones an attacker can reach. Use on applications (Gemfile.lock / package-lock.json present), not on libraries.

## Classification

Categories: commerce, content, data, documentation, documents, engineering
Client compatibility: not explicitly detected
License: MIT

## Resources

Scripts: 0
References: 0
Assets: 0
Other: 1

## Scores

Overall: 100
Quality: 100
Security: 100
Maintenance: 100
Adoption: 74

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-11T23:36:10.775186+00:00
Published: 2026-09-11T23:41:04.105755+00:00
Publication event: add
Source fingerprint: `acc889ccf7fd2d190b656ed49ec74d84fe0afb0681b1d5086732d2a3510171d4`
Analysis fingerprint: `111c6b9a590d96bf0675de6a9ed1a35aa36edb4329980f01e63afa582a4bfd65`
