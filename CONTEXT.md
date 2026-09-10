# Domain glossary

## Candidate repository
A GitHub repository discovered by a broad search signal. A candidate is not assumed to contain an Agent Skill

## Skill manifest
A file named `SKILL.md` or case-equivalent candidate that contains Agent Skills frontmatter and instructions

## Indexed skill
A candidate skill with an actual manifest that has been fetched, parsed, attributed to a repository path, and stored with evidence

## Spec validity
Whether the manifest satisfies the required structural rules of the open Agent Skills specification. Validity does not imply usefulness or safety

## Security finding
A static-analysis observation about instructions or bundled text files that may cause high-impact behavior if followed or executed. A finding is not proof of malicious intent

## Quality score
Evidence about manifest clarity, specification compliance, documentation depth, and available test or evaluation signals

## Security score
A static-analysis score derived from detected command and instruction patterns. It is not a sandbox result and is never a guarantee of safety

## Maintenance score
Evidence about recency, archival status, and available repository maintenance signals

## Adoption score
A bounded popularity and momentum signal based on repository metrics and historical snapshots when available

## Overall score
A documented weighted summary of quality, security, maintenance, and adoption. The component scores remain visible and are the primary evidence

## Discovery source
The exact search query or curated seed that caused a repository to enter the candidate set

## Provenance
The repository, branch, path, manifest URL, discovery source, and indexing time that allow a catalog record to be traced back to source evidence

## Snapshot
A timestamped observation of repository metrics used to estimate change over time without treating current stars as momentum

## Observation
The latest successfully indexed semantic state of a Skill in the observation database

## Published Skill
The canonical Skill state already committed to the GitHub-native publication surface

## Skill event
One semantic transition of one Published Skill. Valid event types are add, update, reindex, and remove

## Telemetry update
A repository-level metric change, such as stars or forks, that does not by itself represent a semantic Skill change

## Materialized view
A reproducible aggregate output derived from canonical published records and not used as publication truth

## Source fingerprint
A deterministic fingerprint of the bounded Skill source inputs that were inspected

## Analysis fingerprint
A deterministic fingerprint of semantic Observatory analysis that excludes telemetry-only changes

## Publication truth
The canonical per-Skill records committed under `catalog/skills/**/record.json` on `main`
