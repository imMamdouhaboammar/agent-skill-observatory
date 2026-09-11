# cherry-skill-marketplace

Source repository: [CherryHQ/cherry-studio](https://github.com/CherryHQ/cherry-studio)

Canonical key: `cherryhq/cherry-studio:resources/builtin-agents/cherry-assistant/.claude/skills/cherry-skill-marketplace`

Manifest: [https://github.com/CherryHQ/cherry-studio/blob/main/resources/builtin-agents/cherry-assistant/.claude/skills/cherry-skill-marketplace/SKILL.md](https://github.com/CherryHQ/cherry-studio/blob/main/resources/builtin-agents/cherry-assistant/.claude/skills/cherry-skill-marketplace/SKILL.md)

## Description

当用户明确要求搜索、安装、查看、卸载或创建 Skill，或内置 Skill / 工具出现能力缺口、无法完成当前任务时触发。通过 `mcp__skills__search_skills` 搜索并用 `mcp__skills__install_skill` 安装；已安装 Skill 的查看和删除通过产品清单导航到 Skills UI；没有合适结果时调用内置 `skill-creator` 创建并验证自定义 Skill，再继续原任务。普通任务仍先尝试内置能力。

## Classification

Categories: design
Client compatibility: not explicitly detected
License: AGPL-3.0

## Resources

Scripts: 0
References: 0
Assets: 0
Other: 0

## Scores

Overall: 100
Quality: 100
Security: 100
Maintenance: 100
Adoption: 80

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-11T08:05:17.684097+00:00
Published: 2026-09-11T08:07:15.832049+00:00
Publication event: add
Source fingerprint: `67a99eafefc932fa8b02a3807f7ae6cc59f580ce5799b7f5c9c251273ef8dec0`
Analysis fingerprint: `0bf14e643756cbf407fe3335b6d7a8b43270d3c1dd9b5c911f8b6a3cd3fc9043`
