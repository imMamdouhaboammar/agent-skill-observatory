# reagent-migration

Source repository: [day8/re-frame2](https://github.com/day8/re-frame2)

Canonical key: `day8/re-frame2:skills/reagent-migration`

Manifest: [https://github.com/day8/re-frame2/blob/main/skills/reagent-migration/SKILL.md](https://github.com/day8/re-frame2/blob/main/skills/reagent-migration/SKILL.md)

## Description

Rewrites Reagent VIEW code into **Fresco** (`re-frame.fresco`, alias `h`) — re-frame2's re-frame-native view layer: a view becomes an `h/defview` mounted in brackets, `@(subscribe …)` becomes `(h/sub …)`, handlers become event vectors, Form-2/Form-3 state moves out of the component. **First establish whether the user needs Fresco**: re-frame2's Reagent adapter is first-class and supported, so a v1 app keeps its view code and needs NO rewrite to land on re-frame2 — that is `re-frame-migration`, and it finishes the job. This is an OPTIONAL second step, and Fresco is pre-publication with no released Maven coordinate. **Do not use** for: the v1→v2 events/subs/db migration (`re-frame-migration`), writing new re-frame2 code (`re-frame2`), greenfield setup (`re-frame2-setup`), or live-runtime inspection (`re-frame2-pair`). Trigger on "migrate my Reagent views to Fresco", "port this component to h/defview", or a Reagent view surface (`r/atom`, `@(subscribe …)` in a view) named in a Fresco context.


## Classification

Categories: ai-ml, commerce, content, design, documentation, engineering
Client compatibility: not explicitly detected
License: MIT

## Resources

Scripts: 0
References: 7
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
Source fingerprint: `f8f8852effe1f45f2b680003b26511ab43dcd6ced0625484d7be11712e1f21ce`
Analysis fingerprint: `205192f6114673e762e00b7f140311967074aa71223caae9467dcd2a7238a3e2`
