# Discovery policy

Discovery is intentionally broad. Verification is intentionally strict

The default candidate queries cover repositories tagged with `agent-skills` and repositories whose name, description, or README mention Agent Skills, Claude skills, Codex skills, or `SKILL.md`

Official seed repositories are also inspected so important standards repositories are not dependent on search ranking

A candidate repository is not listed as a skill until its tree contains a real manifest file

## Why not `skills in:name`

Repository names are weak evidence. They include GitHub learning exercises, unrelated human skill projects, forks, demos, and repositories that do not contain an agent-readable skill manifest

The Observatory therefore uses repository search only to produce candidates and uses repository contents to establish the indexing fact

## Bounded fetching

Remote inspection has hard limits:

- maximum 120 files considered per skill directory
- maximum 512 KB per fetched text file
- only the skill root and known supporting directories are fetched
- repository paths are checked against traversal before writing to a temporary directory
- third-party scripts are never executed

These bounds are security controls as well as rate-limit controls
