# target-prioritization

Source repository: [Agents365-ai/365-skills](https://github.com/Agents365-ai/365-skills)

Canonical key: `agents365-ai/365-skills:plugins/target-prioritization/skills/target-prioritization`

Manifest: [https://github.com/Agents365-ai/365-skills/blob/main/plugins/target-prioritization/skills/target-prioritization/SKILL.md](https://github.com/Agents365-ai/365-skills/blob/main/plugins/target-prioritization/skills/target-prioritization/SKILL.md)

## Description

Prioritize drug targets from a ranked gene list (e.g., scRNA-seq DE output) by orchestrating parallel API queries against UniProt, OpenTargets (with integrated DepMap CRISPR essentiality + gnomAD constraint), PubMed, the Human Protein Atlas (HPA), and ChEMBL tool compounds, then re-ranking by a composite score combining protein localization, druggability, disease genetics, tissue specificity (safety), focus-cell-type expression, CRISPR essentiality, LoF safety constraint, and research maturity. Use whenever the user wants to filter, triage, prioritize, or "do due diligence" on a list of candidate genes for drug discovery, especially after a DE / DEG analysis when they say things like "which of these should I follow up on", "filter for druggable targets", "make a target dossier", "rank these for tractability", "annotate these genes for druggability", or "build a target report". Trigger even when the user says just "filter these candidate genes" or hands over a CSV from a DE pipeline.

## Classification

Categories: data, design, engineering, research
Client compatibility: not explicitly detected
License: not declared

## Resources

Scripts: 8
References: 1
Assets: 0
Other: 1

## Scores

Overall: 91
Quality: 93
Security: 100
Maintenance: 100
Adoption: 55

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-10T05:53:54.002733+00:00
Published: 2026-09-10T14:03:45.870733+00:00
Publication event: add
Source fingerprint: ``
Analysis fingerprint: ``
