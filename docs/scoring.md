# Scoring Model

<!-- Copyright (c) 2026 Mamdouh Aboammar. Licensed under Apache-2.0. -->

The score is designed for comparison, not certification. Public admission is a separate strict qualification decision.

Every observed record exposes four component scores from 0 to 100. Adoption remains visible as telemetry, but it does not affect qualification, overall score, or directory tie-breaking.

## Qualification gate

A Skill is eligible for public publication only when the deterministic qualification policy passes all blocking checks. Current checks cover:

- Open Agent Skills specification validity
- Sufficient instruction depth and procedural structure
- Static security score of at least 90 with no high or critical finding
- Verification evidence for bundled executable scripts
- Portable paths without user-specific absolute paths or traversal
- Integrity of referenced scripts, references, assets, evals, and agent resources
- Behavioral safety checks for prompt-override or system-prompt extraction instructions
- Duplicate rejection
- Active, non-archived source repository
- Declared Skill or repository license

Stars, forks, install counts, watchers, and star velocity are not qualification inputs.

## Quality (45% of overall)

Signals include open-spec validity, useful description length, instruction depth, repository tests or evals, and README evidence.

| Evidence | Current implementation signal |
|---|---|
| Spec-valid manifest | strong positive |
| Useful description length | positive |
| Substantive instruction body | positive |
| Tests or evals present | positive |
| README present | positive |

## Security (35% of overall)

Starts at 100 and applies documented deductions for static findings. No third-party code is executed to produce this score.

| Pattern | Example risk |
|---|---|
| `curl … \| bash` | remote content piped to a shell |
| `rm -rf` | recursive deletion |
| Credential-path references | secret exposure |
| `eval` / `exec` | dynamic execution |
| `chmod 777` | world-writable permissions |
| `sudo` | privilege escalation |

A high security score means the static scanner did not detect the patterns it knows about. It is not a sandbox execution result and is not a guarantee of safety.

## Maintenance (20% of overall)

Recent pushes retain a higher score. Long inactivity reduces it. Archived repositories receive a strong penalty and are rejected by the qualification gate.

| Age since last push | Effect |
|---|---|
| recent | higher maintenance confidence |
| 90+ days | progressive reduction |
| 180+ days | larger reduction |
| 365+ days | strong reduction |
| archived | rejected from public qualification |

## Adoption telemetry (0% of overall)

Adoption is still calculated and exposed so consumers can inspect repository reach and momentum separately. It uses bounded star, fork, and historical star-velocity signals. It is deliberately excluded from public admission and ranking quality decisions.

This means a new repository with zero stars can qualify and rank above a popular repository when its Skill package is structurally better, safer, and better maintained.

## Overall

```text
overall = 0.45 × quality + 0.35 × security + 0.20 × maintenance
if archived: overall = min(overall, 49)
if license present: overall = min(overall + 3, 100)
```

Directory ordering uses overall score, then security score, then quality score, then canonical key for deterministic ties. Stars and forks are never tie-breakers.

The component scores, qualification evidence, and reasons remain part of the record so consumers can inspect why a Skill was admitted rather than relying on one opaque number.
