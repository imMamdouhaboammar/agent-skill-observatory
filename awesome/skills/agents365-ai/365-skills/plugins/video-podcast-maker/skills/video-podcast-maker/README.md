# video-podcast-maker

Source repository: [Agents365-ai/365-skills](https://github.com/Agents365-ai/365-skills)

Canonical key: `agents365-ai/365-skills:plugins/video-podcast-maker/skills/video-podcast-maker`

Manifest: [https://github.com/Agents365-ai/365-skills/blob/main/plugins/video-podcast-maker/skills/video-podcast-maker/SKILL.md](https://github.com/Agents365-ai/365-skills/blob/main/plugins/video-podcast-maker/skills/video-podcast-maker/SKILL.md)

## Description

Use when the user gives a topic and wants an automated topic-driven narrated explainer, podcast, or knowledge-summary video (Bilibili / YouTube / Xiaohongshu / Douyin / WeChat Channels), or asks to learn visual design patterns from a reference video/image. Trigger when the user mentions creating a knowledge video, narrated explainer, video podcast, or animated infographic-style video from a topic — even if they don't say "video podcast" explicitly. Also trigger when the user wants to regenerate, re-render, rebuild, update, or iterate on a narrated video this skill already produced — e.g. they edited the script/prompt, changed the visuals, or swapped the background music and want the final video remade (reuse the existing videos/{name}/ directory, never start a new project). Do NOT trigger for generic video editing, trimming, format conversion, color grading, or non-narrative video tasks. Produces 4K video via research → script → TTS → Remotion → MP4 + BGM.

## Classification

Categories: content, design, engineering, research
Client compatibility: not explicitly detected
License: not declared

## Resources

Scripts: 26
References: 12
Assets: 0
Other: 10

## Scores

Overall: 81
Quality: 93
Security: 66
Maintenance: 100
Adoption: 55

## Static security findings

- medium: sudo in references/troubleshooting.md: Requests elevated operating-system privileges.
- high: recursive-delete in references/troubleshooting.md: Uses recursive forced deletion.

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-10T05:53:54.002733+00:00
Published: 2026-09-10T14:03:45.870733+00:00
Publication event: add
Source fingerprint: ``
Analysis fingerprint: ``
