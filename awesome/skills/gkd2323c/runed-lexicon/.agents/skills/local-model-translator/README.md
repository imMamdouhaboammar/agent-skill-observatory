# local-model-translator

Source repository: [gkd2323c/runed-lexicon](https://github.com/gkd2323c/runed-lexicon)

Canonical key: `gkd2323c/runed-lexicon:.agents/skills/local-model-translator`

Manifest: [https://github.com/gkd2323c/runed-lexicon/blob/main/.agents/skills/local-model-translator/SKILL.md](https://github.com/gkd2323c/runed-lexicon/blob/main/.agents/skills/local-model-translator/SKILL.md)

## Description

Use a local Ollama translation model such as Hy-MT2 as a constrained base-translation worker inside the Skyrim MOD localization pipeline. Use this skill whenever an Agent has already understood the quest/dialogue/book context and wants the local model to translate prepared English strings into Chinese, especially for batch translation with fixed terminology, protected placeholders, deterministic IDs, or a 32K local context window. The high-level Agent remains responsible for semantics, spoiler boundaries, terminology decisions, and review; this skill only delegates the basic translation pass and validates the worker output before it can enter translation-executor results.

## Classification

Categories: commerce, data, localization, productivity, research, testing
Client compatibility: GitHub Copilot, OpenAI Codex
License: Apache-2.0

## Resources

Scripts: 3
References: 1
Assets: 1
Other: 1

## Scores

Overall: 100
Quality: 100
Security: 100
Maintenance: 100
Adoption: 10

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-11T12:39:00.478677+00:00
Published: 2026-09-11T19:23:00.429355+00:00
Publication event: add
Source fingerprint: `635e4bd0c343636eb8453353dc931a4d85bfc48b0967f14394c318605cb5bae1`
Analysis fingerprint: `1699f8dc9494e2d38026856a6b453954f5cd92eea9320b72577302bf5577a834`
