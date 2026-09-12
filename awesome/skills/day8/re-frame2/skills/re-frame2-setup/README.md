# re-frame2-setup

Source repository: [day8/re-frame2](https://github.com/day8/re-frame2)

Canonical key: `day8/re-frame2:skills/re-frame2-setup`

Manifest: [https://github.com/day8/re-frame2/blob/main/skills/re-frame2-setup/SKILL.md](https://github.com/day8/re-frame2/blob/main/skills/re-frame2-setup/SKILL.md)

## Description

Greenfield-only bootstrap for re-frame2 ClojureScript projects. Scope: brand-new apps from nothing, or empty CLJS projects (shadow-cljs / Clojure already present but zero re-frame2 wiring). Writes the canonical twelve-file counter SPA the generator template emits — core + the Reagent adapter, `shadow-cljs.edn`, the entry namespace with `rf/init!`, events / subs / views — then installs, compiles, serves it and reports the URL, exiting once the counter mounts. **Do not use** for writing app code on an already-bootstrapped project (use `re-frame2`), v1→v2 migration (`re-frame-migration`), live-app inspection (`re-frame2-pair`), or porting re-frame2 itself (`re-frame2-implementor`); the full disqualifier list is `skills/README.md` §Skill routing. Trigger on "start a re-frame2 project", "scaffold re-frame2", "hello-world re-frame2 app", or a build failure on a freshly-scaffolded project that traces to missing `re-frame.core` / `re-frame.adapter.reagent` wiring.


## Classification

Categories: browser-automation, commerce, content, documentation, engineering, marketing
Client compatibility: not explicitly detected
License: MIT

## Resources

Scripts: 0
References: 4
Assets: 0
Other: 3

## Scores

Overall: 100
Quality: 93
Security: 100
Maintenance: 100
Adoption: 47

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-12T23:16:55.549533+00:00
Published: 2026-09-12T23:18:21.000081+00:00
Publication event: add
Source fingerprint: `d0ae467c9611aef7ba9cf275fe4a795b84cbf07fdd329816a410e3cf6fc23ed3`
Analysis fingerprint: `cfaf278f953a5ad3255bfb4cb2168ef04445589d7da7e62ba71540def276f46c`
