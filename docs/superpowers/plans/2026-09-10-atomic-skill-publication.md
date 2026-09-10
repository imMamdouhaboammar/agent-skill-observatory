# Atomic Skill Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Replace snapshot-style catalog commits with a race-safe publication loop where every semantic Skill add, update, reindex, or confirmed removal is published as one atomic commit directly to `main`, while GitHub-native Markdown directories remain consistent and aggregate files are materialized separately.

**Architecture:** Keep discovery and indexing as the observation side of the product. Add a publication side that compares observed Skills with canonical published Skill records on `main`, emits deterministic Skill events, renders only the files affected by one event, and commits that event through the GitHub Git Database API with a fast-forward-only ref update. Store each Skill in a sharded canonical path so one Skill event does not require rewriting the full catalog. Keep `AWESOME.md` and `data/*` as reproducible materialized views rather than publication truth.

**Tech Stack:** Python 3.11+, Pydantic 2, SQLAlchemy 2, Alembic, HTTPX, Typer, pytest, Ruff, mypy, GitHub Actions, GitHub REST Git Database API

**Spec:** `CONTEXT.md`, `docs/adr/0001-evidence-gated-indexing.md`, `docs/adr/0002-never-execute-third-party-skills.md`, `docs/adr/0003-dual-runtime.md`, and the approved Atomic Skill Publication v1 contract captured in this plan

## Global constraints

- Never execute third-party Skill scripts during discovery, indexing, diffing, rendering, or publication.
- One semantic Skill event maps to exactly one Git commit.
- Never combine two Skill events into one Skill event commit.
- Publish Skill event commits directly to `main`; do not create a per-Skill branch or pull request.
- Never use force push and never update `refs/heads/main` with `force=true`.
- A commit must remain internally consistent if the workflow stops immediately after that commit.
- A no-op observation must not create a Skill commit.
- Repository telemetry changes such as stars or forks must not create one commit per Skill.
- Publication must be idempotent across retries, cancelled runs, cache loss, and partial prior publication.
- A failed repository scan must never be interpreted as Skill removal.
- Confirm a missing Skill in two successful scans of the same repository before publishing a removal.
- Generated Skill paths, repository pages, category pages, and canonical catalog records are bot-owned.
- The root `README.md` remains partly human-owned; publication may only replace the generated Awesome marker section.
- Keep the 15-minute scheduled refresh cadence at `7,22,37,52 * * * *`.
- Keep aggregate `AWESOME.md`, JSON, CSV, statistics, and repository rollups reproducible from canonical records.
- Preserve SQLite and PostgreSQL support for observation persistence.
- Preserve the current API, local scanner, static safety model, and service mode unless a task below explicitly changes their publication-facing behavior.

## Current-state evidence

The current code has four relevant seams:

1. `src/skill_observatory/pipeline.py` discovers repositories, materializes bounded Skill files, parses and scores them, and writes `IndexedSkill` records to the database.
2. `src/skill_observatory/db.py` stores Skill records and repository snapshots. `SkillRecord.content_fingerprint` currently represents the parsed manifest fingerprint, and no publication lifecycle fields exist yet.
3. `src/skill_observatory/publishing.py` currently regenerates `README.md`, `AWESOME.md`, `awesome/README.md`, `data/catalog.json`, `data/catalog.csv`, `data/repositories.json`, `data/stats.json`, and `data/refresh.json` as one snapshot.
4. `.github/workflows/refresh.yml` currently scans, regenerates all outputs, creates one large Git commit, and runs `git push`. A real production run already demonstrated the race: the scan and generation succeeded, another change advanced `main`, and the final push was rejected as non-fast-forward.

The new design fixes the publication boundary instead of adding retry shell commands around the old giant commit.

## Domain contract

Use these terms consistently in code, tests, docs, and commit metadata.

- **Observation:** The latest successfully indexed state of a Skill in the observation database.
- **Published Skill:** The canonical Skill state already present on `main` under `catalog/skills/**/record.json`.
- **Skill event:** One semantic transition of one canonical Skill. Event types are `add`, `update`, `reindex`, and `remove`.
- **Telemetry update:** Repository-level metrics such as stars, forks, and activity that do not represent a semantic Skill source change.
- **Materialized view:** A reproducible aggregate output such as `AWESOME.md`, `data/catalog.json`, or `data/stats.json`. Materialized views are not publication truth.
- **Source fingerprint:** A SHA-256 fingerprint of the bounded Skill source inputs that the indexer actually inspected.
- **Analysis fingerprint:** A SHA-256 fingerprint of semantic analysis output that is intentionally independent from telemetry-only fields.
- **Publication truth:** Canonical per-Skill records committed under `catalog/skills/**/record.json` on `main`.

## Canonical GitHub directory layout

```text
catalog/
└── skills/
    └── <owner>/
        └── <repo>/
            └── <skill-path>/
                └── record.json

awesome/
├── README.md
├── categories/
│   └── <category>.md
├── repos/
│   └── <owner>/
│       └── <repo>.md
└── skills/
    └── <owner>/
        └── <repo>/
            └── <skill-path>/
                └── README.md

AWESOME.md
data/
├── catalog.json
├── catalog.csv
├── repositories.json
├── stats.json
└── refresh.json
```

For a root-level Skill whose logical path is `.`, use `_root` as the filesystem segment. Reject `..`, absolute paths, null bytes, and any segment that escapes its generated root.

## Runtime commit contract

A new Skill commit uses this subject:

```text
skill(add): <skill-name> · <owner/repo>
```

An updated source uses:

```text
skill(update): <skill-name> · <owner/repo>
```

A changed Observatory analysis with unchanged source uses:

```text
skill(reindex): <skill-name> · <owner/repo>
```

A confirmed removal uses:

```text
skill(remove): <skill-name> · <owner/repo>
```

Each Skill commit body contains deterministic metadata:

```text
Skill-Key: <canonical-key>
Event: <add|update|reindex|remove>
Source-Fingerprint: <sha256-or-none>
Analysis-Fingerprint: <sha256-or-none>
Overall-Score: <0-100-or-none>
Security-Score: <0-100-or-none>
Categories: <comma-separated-list-or-none>
Observed-At: <ISO-8601 UTC timestamp>
```

A Skill event commit may change only the canonical Skill record and the generated views affected by that Skill:

- `catalog/skills/<owner>/<repo>/<skill-path>/record.json`
- `awesome/skills/<owner>/<repo>/<skill-path>/README.md`
- `awesome/repos/<owner>/<repo>.md`
- each old or new `awesome/categories/<category>.md`
- the generated marker block in root `README.md`
- `awesome/README.md`

Do not rewrite the full `AWESOME.md` or full `data/catalog.json` in every Skill commit.

After a batch, create at most one aggregate commit when materialized views changed:

```text
catalog: refresh materialized views
```

That aggregate commit may update only `AWESOME.md` and `data/*` aggregate files. Repository telemetry-only changes also belong in this aggregate commit.

## Event ordering

Publish deterministic event order in this priority:

1. Security downgrade on an existing Skill.
2. Confirmed removal.
3. Existing Skill source update.
4. Reindex.
5. New Skill.

Within one priority class, order by `canonical_key` ascending.

## Publication limits

Scheduled mode:

- Scan at most the configured candidate repository limit, currently 50 by default.
- Publish at most 100 Skill events per run.
- Stop Skill publication when the publication time budget reaches 420 seconds.
- Leave unprocessed events unpublished; the next run recomputes them from observation versus publication truth.

Bootstrap mode:

- Trigger manually.
- Use the same event model and publisher.
- Default to 500 events per run.
- Use a 2,400-second publication time budget.
- Never collapse bootstrap Skills into a giant commit.

The delta between observation state and canonical published records is the retry queue. Do not introduce a queue file that becomes a third source of truth.

## Dependency graph

```text
Task 1  Domain contract and publication types
   ↓
Task 2  Observation fingerprints and missing lifecycle
   ↓
Task 3  Canonical published-record store and path rules
   ↓
Task 4  Deterministic delta engine
   ↓
Task 5  Sharded GitHub directory renderer
   ↓
Task 6  Fast-forward-only GitHub atomic publisher
   ↓
Task 7  Publication orchestrator and CLI
   ↓
Task 8  Aggregate materializer migration
   ↓
Task 9  Scheduled and bootstrap Actions migration
   ↓
Task 10 End-to-end race, recovery, and idempotency verification
   ↓
Task 11 Documentation, rollout, and production proof
```

---

### Task 1: Define the publication domain and irreversible architecture decision

**Depends on:** None

**Files:**
- Modify: `CONTEXT.md`
- Create: `docs/adr/0004-atomic-skill-publication.md`
- Create: `src/skill_observatory/events.py`
- Modify: `src/skill_observatory/domain.py`
- Test: `tests/test_events.py`

**Interfaces:**
- Produces `SkillEventType`, `PublishedSkillRecord`, `SkillEvent`, `PublicationResult`, and canonical publication metadata used by every later task.
- Does not perform GitHub I/O or filesystem rendering.

**Required types:**

```python
SkillEventType = Literal["add", "update", "reindex", "remove"]

class PublishedSkillRecord(BaseModel):
    schema_version: int = 1
    canonical_key: str
    source_fingerprint: str
    analysis_fingerprint: str
    published_at: datetime
    publication_event: SkillEventType
    skill: IndexedSkill

class SkillEvent(BaseModel):
    type: SkillEventType
    canonical_key: str
    before: PublishedSkillRecord | None = None
    after: PublishedSkillRecord | None = None
    priority: int
    observed_at: datetime

class PublicationResult(BaseModel):
    canonical_key: str
    event_type: SkillEventType
    status: Literal["published", "noop", "deferred"]
    commit_sha: str | None = None
    parent_sha: str | None = None
    attempts: int = 0
    files_changed: list[str] = Field(default_factory=list)
```

- [ ] **Step 1: Write the failing event-model tests**

Add tests that reject an `add` event without `after`, reject a `remove` event without `before`, and accept a valid `update` with both states.

Run:

```bash
pytest tests/test_events.py -v
```

Expected: FAIL because the publication event types do not exist.

- [ ] **Step 2: Add the minimal publication types and validators**

Keep validation in Pydantic model validators so illegal event states cannot cross later interfaces.

- [ ] **Step 3: Update the domain glossary**

Add the terms Observation, Published Skill, Skill event, Telemetry update, Materialized view, Source fingerprint, Analysis fingerprint, and Publication truth to `CONTEXT.md`. Keep framework and storage implementation details out of glossary definitions.

- [ ] **Step 4: Record ADR 0004**

The ADR must record these decisions and consequences:

- publication truth moves from aggregate snapshot files to sharded canonical Skill records;
- one semantic Skill event becomes one direct `main` commit;
- aggregate files become materialized views;
- publication uses GitHub Git Database objects plus fast-forward-only ref updates;
- generated paths are bot-owned, while root `README.md` is only partly bot-owned;
- no force update is allowed;
- retries recompute from published truth instead of relying on an external queue.

- [ ] **Step 5: Run the focused tests**

```bash
pytest tests/test_events.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the slice**

```bash
git add CONTEXT.md docs/adr/0004-atomic-skill-publication.md src/skill_observatory/events.py src/skill_observatory/domain.py tests/test_events.py
git commit -m "feat: define atomic skill publication domain"
```

---

### Task 2: Separate semantic fingerprints from telemetry and add safe missing-state tracking

**Depends on:** Task 1

**Files:**
- Modify: `src/skill_observatory/db.py`
- Modify: `src/skill_observatory/repository.py`
- Modify: `src/skill_observatory/pipeline.py`
- Create: `src/skill_observatory/alembic/versions/9f2a7c1d4b10_atomic_publication_state.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_migrations.py`
- Test: `tests/test_repository.py`

**Interfaces:**
- Produces `source_fingerprint`, `analysis_fingerprint`, `consecutive_misses`, and `last_successful_repo_scan_at` on observed Skill records.
- Preserves existing `content_fingerprint` for duplicate detection.

**Schema additions:**

```text
skills.source_fingerprint            VARCHAR(64) NOT NULL DEFAULT ''
skills.analysis_fingerprint          VARCHAR(64) NOT NULL DEFAULT ''
skills.consecutive_misses            INTEGER NOT NULL DEFAULT 0
skills.last_successful_repo_scan_at  DATETIME NULL
```

**Fingerprint rules:**

- `content_fingerprint` remains the manifest-level duplicate signal.
- `source_fingerprint` hashes the normalized relative path plus bytes of every bounded text/source file that `_paths_for_skill()` actually inspected. Sort paths before hashing.
- `analysis_fingerprint` hashes only semantic analysis output: spec validation, static security findings and score, categories, client compatibility evidence, duplicate target, resource counts, and quality score. Exclude stars, forks, adoption score, maintenance score, `indexed_at`, and other telemetry-only values.

- [ ] **Step 1: Write a failing source-fingerprint regression test**

Create a fixture where `SKILL.md` stays unchanged but `scripts/check.py` changes. Assert that `content_fingerprint` stays the same while `source_fingerprint` changes.

- [ ] **Step 2: Write a failing telemetry isolation test**

Index the same Skill with different stars and forks. Assert that `source_fingerprint` and `analysis_fingerprint` remain unchanged.

- [ ] **Step 3: Write missing-state tests**

Cover all cases:

```text
successful scan + Skill present       -> consecutive_misses = 0
successful scan + Skill absent once   -> consecutive_misses = 1
successful scan + Skill absent twice  -> eligible for removal
repository scan failure               -> miss count unchanged
Skill returns after one miss          -> consecutive_misses = 0
```

- [ ] **Step 4: Add the Alembic migration**

Use revision id `9f2a7c1d4b10` and down revision `8278fbd6b06e`. The migration must preserve existing data and give existing rows safe defaults.

- [ ] **Step 5: Implement deterministic fingerprint helpers**

Keep hashing pure and deterministic. Do not include absolute temporary paths, filesystem mtimes, iteration order, or timestamps.

- [ ] **Step 6: Implement repository-success reconciliation**

After a repository tree is fetched successfully, reconcile the set of observed canonical keys for that repository. Increment missing counters only for previously active Skills that were absent from that successful tree. Do not mutate missing counters if the tree fetch failed.

- [ ] **Step 7: Run focused tests and migration checks**

```bash
pytest tests/test_pipeline.py tests/test_repository.py tests/test_migrations.py -v
SKILLOBS_DATABASE_URL=sqlite+pysqlite:///./migration-check.db skillobs migrate
alembic check
rm -f migration-check.db
```

Expected: PASS and no new upgrade operations detected.

- [ ] **Step 8: Commit the slice**

```bash
git add src/skill_observatory/db.py src/skill_observatory/repository.py src/skill_observatory/pipeline.py src/skill_observatory/alembic/versions/9f2a7c1d4b10_atomic_publication_state.py tests/test_pipeline.py tests/test_repository.py tests/test_migrations.py
git commit -m "feat: track semantic skill observations"
```

---

### Task 3: Add canonical published-record paths and a local publication snapshot loader

**Depends on:** Task 2

**Files:**
- Create: `src/skill_observatory/publication_store.py`
- Test: `tests/test_publication_store.py`

**Interfaces:**

```python
def skill_record_path(canonical_key: str) -> PurePosixPath: ...
def skill_markdown_path(canonical_key: str) -> PurePosixPath: ...
def repository_markdown_path(repo_full_name: str) -> PurePosixPath: ...
def category_markdown_path(category: str) -> PurePosixPath: ...

def load_published_catalog(root: Path) -> dict[str, PublishedSkillRecord]: ...
```

**Path behavior:**

For `owner/repo:skills/frontend`, produce:

```text
catalog/skills/owner/repo/skills/frontend/record.json
awesome/skills/owner/repo/skills/frontend/README.md
awesome/repos/owner/repo.md
```

For `owner/repo:.`, use:

```text
catalog/skills/owner/repo/_root/record.json
awesome/skills/owner/repo/_root/README.md
```

- [ ] **Step 1: Write failing path tests**

Cover nested Skill paths, root Skills, mixed case owner/repository names, category slug normalization, and rejection of traversal input.

- [ ] **Step 2: Write a failing published-catalog loader test**

Build a temporary `catalog/skills/**/record.json` tree with two valid records and assert that the loader returns a dictionary keyed by canonical key.

- [ ] **Step 3: Implement path generation and validation**

Do not use string replacement that can collapse distinct source paths into the same generated path. Preserve repository path segments after validating them.

- [ ] **Step 4: Implement the loader**

Reject malformed JSON and duplicate canonical keys with an explicit publication-state error. Do not silently skip corrupt publication truth.

- [ ] **Step 5: Run focused tests**

```bash
pytest tests/test_publication_store.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the slice**

```bash
git add src/skill_observatory/publication_store.py tests/test_publication_store.py
git commit -m "feat: add canonical published skill store"
```

---

### Task 4: Build the deterministic observation-to-publication delta engine

**Depends on:** Task 3

**Files:**
- Modify: `src/skill_observatory/events.py`
- Modify: `src/skill_observatory/repository.py`
- Test: `tests/test_events.py`

**Interfaces:**

```python
def build_published_record(skill: IndexedSkill, *, published_at: datetime, event: SkillEventType) -> PublishedSkillRecord: ...

def compute_skill_events(
    observed: list[IndexedSkill],
    published: dict[str, PublishedSkillRecord],
    *,
    observed_at: datetime,
) -> list[SkillEvent]: ...
```

**Decision table:**

```text
not published + active observation                     -> add
published + source fingerprint changed                 -> update
published + source same + analysis fingerprint changed -> reindex
published + telemetry-only change                      -> no Skill event
published + first confirmed miss only                  -> no event
published + consecutive_misses >= 2                    -> remove
identical published and observed semantic state        -> no event
```

Security downgrade receives the highest event priority when an existing Skill's security score decreases.

- [ ] **Step 1: Write the add test and observe RED**

Assert exactly one `add` event for one observed Skill absent from publication truth.

- [ ] **Step 2: Implement only the add path and reach GREEN**

- [ ] **Step 3: Add one test at a time for update, reindex, telemetry no-op, confirmed remove, and unchanged no-op**

Follow red, green, refactor for each decision-table row.

- [ ] **Step 4: Add deterministic ordering tests**

Create mixed event types and assert security downgrade, remove, update, reindex, then add. Assert canonical-key ascending order inside each class.

- [ ] **Step 5: Add idempotency test**

Apply the `after` state of a generated event to the published dictionary, compute the delta again, and assert that the same event is not emitted again.

- [ ] **Step 6: Run focused tests**

```bash
pytest tests/test_events.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit the slice**

```bash
git add src/skill_observatory/events.py src/skill_observatory/repository.py tests/test_events.py
git commit -m "feat: compute deterministic skill publication events"
```

---

### Task 5: Render one Skill event into a sharded GitHub-native directory patch

**Depends on:** Task 4

**Files:**
- Create: `src/skill_observatory/directory.py`
- Modify: `src/skill_observatory/publishing.py`
- Test: `tests/test_directory.py`
- Modify: `tests/test_publishing.py`

**Interfaces:**

```python
class DirectoryPatch(BaseModel):
    writes: dict[str, str]
    deletes: list[str]


def render_skill_event(
    event: SkillEvent,
    catalog_after_event: dict[str, PublishedSkillRecord],
    *,
    current_root_readme: str,
) -> DirectoryPatch: ...
```

`render_skill_event()` is pure. It receives the latest root README text and returns content to write or paths to delete. It does not call GitHub and does not mutate the filesystem.

**Skill page content:**

- Skill name and source repository
- canonical key and manifest URL
- description
- category list
- client compatibility evidence
- license and resource counts
- overall, quality, security, maintenance, and adoption scores
- static security findings summary
- first-seen and indexed timestamps when available
- source and analysis fingerprints
- explicit statement that static analysis is not malware certification

**Repository page content:**

- repository URL
- count of published Skills
- categories
- best score
- security distribution
- deterministic table of contained Skills

**Category page content:**

- category name
- deterministic table sorted by overall score descending, stars descending, then Skill name ascending

**Root README behavior:**

Only replace content between `<!-- AWESOME_INDEX_START -->` and `<!-- AWESOME_INDEX_END -->`. Include current published Skill count, repository count, latest Skill event, and links to `awesome/README.md` and `AWESOME.md`. Preserve every byte outside the marker block.

- [ ] **Step 1: Write a failing add-render test**

Assert that one add event writes exactly the canonical record, Skill page, repository page, category pages, `awesome/README.md`, and a root README with its non-generated prefix and suffix preserved.

- [ ] **Step 2: Implement the minimal add renderer**

- [ ] **Step 3: Write and implement update rendering**

If a Skill moves from category `research` to `engineering`, update both old and new category pages in the same commit patch.

- [ ] **Step 4: Write and implement removal rendering**

Delete the Skill record and Skill Markdown page. Regenerate the repository page and every affected category page. Delete a generated category or repository page only when it becomes empty.

- [ ] **Step 5: Write deterministic rendering tests**

Run the same event and catalog twice with the same explicit clock and assert byte-identical output.

- [ ] **Step 6: Ensure aggregate publishing remains separate**

Refactor helper reuse in `publishing.py` only where it reduces duplication. Do not make per-Skill rendering rewrite full aggregate files.

- [ ] **Step 7: Run focused tests**

```bash
pytest tests/test_directory.py tests/test_publishing.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit the slice**

```bash
git add src/skill_observatory/directory.py src/skill_observatory/publishing.py tests/test_directory.py tests/test_publishing.py
git commit -m "feat: render sharded GitHub skill directory"
```

---

### Task 6: Add a fast-forward-only GitHub atomic publisher

**Depends on:** Task 5

**Files:**
- Create: `src/skill_observatory/github_publisher.py`
- Modify: `src/skill_observatory/config.py`
- Test: `tests/test_github_publisher.py`

**Interfaces:**

```python
class GitHubAtomicPublisher:
    def publish_event(
        self,
        event: SkillEvent,
        catalog_after_event: dict[str, PublishedSkillRecord],
        *,
        repository: str,
        branch: str = "main",
        max_attempts: int = 5,
    ) -> PublicationResult: ...
```

The module owns all GitHub write mechanics. Callers must not construct blobs, trees, commits, or ref updates themselves.

**GitHub write sequence per attempt:**

```text
GET   /repos/{repository}/git/ref/heads/{branch}
GET   /repos/{repository}/git/commits/{current_sha}
GET   current README.md from the same branch head
render event against current README marker block
POST  /repos/{repository}/git/blobs for changed text files
POST  /repos/{repository}/git/trees with base_tree = current tree
POST  /repos/{repository}/git/commits with parent = current_sha
PATCH /repos/{repository}/git/refs/heads/{branch} with force = false
```

For deleted generated paths, create tree entries with `sha: null`.

**Conflict behavior:**

Treat non-fast-forward responses from the ref update as a retryable publication conflict. On retry, read the new branch head and current root README again. Rebuild the tree on the new base. Do not call `git rebase`, do not call `git push --force`, and do not set `force=true`.

Before creating a new commit, read the canonical Skill record at the current branch head when it exists. If that record already matches the target event's resulting source and analysis fingerprints, return `PublicationResult(status="noop")`.

- [ ] **Step 1: Write the happy-path HTTP contract test**

Use `httpx.MockTransport` and assert the exact endpoint sequence. Assert the created commit has the current `main` SHA as its only parent and the ref PATCH body contains `"force": false`.

- [ ] **Step 2: Implement the happy path**

Add private `_get`, `_post`, and `_patch` boundary helpers that convert GitHub failures into typed publisher errors. Do not expose HTTP response objects outside this module.

- [ ] **Step 3: Write the real race regression test**

Simulate:

```text
read main A
create commit C(parent=A)
ref update rejected because main moved to B
read main B
create commit C2(parent=B)
ref update succeeds
```

Assert `attempts == 2`, parent is B on the successful commit, and no force update appears in any request.

- [ ] **Step 4: Implement bounded retry**

Use five attempts with bounded backoff. Inject the sleep function into the class so tests do not wait.

- [ ] **Step 5: Write the idempotent retry test**

Simulate a network failure after GitHub accepted the ref update. On the next attempt, return the already-published canonical record. Assert that the publisher returns `noop` and does not create a duplicate commit.

- [ ] **Step 6: Write README preservation test under concurrent human edit**

Change text outside the generated marker block between attempts. Assert the successful event commit preserves the new human text and replaces only the generated marker section.

- [ ] **Step 7: Run focused tests**

```bash
pytest tests/test_github_publisher.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit the slice**

```bash
git add src/skill_observatory/github_publisher.py src/skill_observatory/config.py tests/test_github_publisher.py
git commit -m "feat: publish skill events with fast-forward commits"
```

---

### Task 7: Add the publication orchestrator and CLI contract

**Depends on:** Task 6

**Files:**
- Create: `src/skill_observatory/publication.py`
- Modify: `src/skill_observatory/cli.py`
- Test: `tests/test_publication.py`
- Modify: `tests/test_cli.py`

**Interfaces:**

```python
class PublicationReport(BaseModel):
    events_detected: int
    events_published: int
    events_noop: int
    events_deferred: int
    adds: int
    updates: int
    reindexes: int
    removals: int
    conflicts_retried: int
    failures: list[str]
    main_before: str | None
    main_after: str | None


def publish_pending_events(
    session: Session,
    publisher: GitHubAtomicPublisher,
    *,
    checkout_root: Path,
    repository: str,
    branch: str,
    max_events: int,
    time_budget_seconds: int,
    now: datetime | None = None,
) -> PublicationReport: ...
```

**Behavior:**

1. Load observations from the database.
2. Load canonical published records from the checked-out `main` tree.
3. Compute deterministic events.
4. Publish events sequentially.
5. After each `published` or `noop` result, mutate only the in-memory published catalog so the next event renders against the logically current publication state.
6. Stop before exceeding `max_events` or the time budget.
7. On a source-specific malformed Skill, record the failure and continue only if publication truth remains valid.
8. On GitHub authentication, ref, tree, or renderer-integrity failure, stop publication and return a failed report.

**CLI command:**

```text
skillobs publish-events \
  --repository owner/repo \
  --branch main \
  --database-url sqlite+pysqlite:///./.cache/observatory.db \
  --checkout-root . \
  --max-events 100 \
  --time-budget-seconds 420
```

The command reads `SKILLOBS_GITHUB_TOKEN`. It prints one JSON `PublicationReport` to stdout and exits non-zero only for global publication failure. Deferred work is not a failure.

- [ ] **Step 1: Write a failing two-event integration test**

Use a fake publisher that records calls. Provide two add events and assert two publisher calls and two distinct publication results. Assert no batch publisher interface exists.

- [ ] **Step 2: Implement sequential event orchestration**

- [ ] **Step 3: Add budget tests**

Assert `max_events=1` publishes exactly one event and leaves the second for recomputation. Inject a monotonic clock and assert time-budget expiry stops cleanly without marking remaining events failed.

- [ ] **Step 4: Add CLI tests**

Use Typer `CliRunner`. Assert option defaults, JSON report shape, successful exit for deferred work, and non-zero exit for a global publisher failure.

- [ ] **Step 5: Run focused tests**

```bash
pytest tests/test_publication.py tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the slice**

```bash
git add src/skill_observatory/publication.py src/skill_observatory/cli.py tests/test_publication.py tests/test_cli.py
git commit -m "feat: orchestrate atomic skill publication"
```

---

### Task 8: Convert full catalog outputs into explicit materialized views

**Depends on:** Task 7

**Files:**
- Modify: `src/skill_observatory/publishing.py`
- Modify: `src/skill_observatory/catalog.py`
- Modify: `src/skill_observatory/cli.py`
- Test: `tests/test_publishing.py`
- Test: `tests/test_catalog.py`
- Test: `tests/test_cli.py`

**Interfaces:**

Keep the existing `skillobs publish` command for local and service-mode aggregate generation, but redefine its source in GitHub-native operation: aggregate views must be reproducible from canonical published records, not used as the source for Skill event detection.

Add a callable interface:

```python
def materialize_published_catalog(
    published: dict[str, PublishedSkillRecord],
    *,
    generated_at: datetime,
) -> dict[str, str]: ...
```

Return a mapping for these aggregate paths:

```text
AWESOME.md
data/catalog.json
data/catalog.csv
data/repositories.json
data/stats.json
data/refresh.json
```

- [ ] **Step 1: Write a failing materialization test from canonical records**

Create two `PublishedSkillRecord` values without a database session. Assert the generated JSON, CSV, stats, repository rollups, and `AWESOME.md` contain both Skills.

- [ ] **Step 2: Implement pure aggregate materialization**

Do not read `.cache/observatory.db` inside the pure renderer.

- [ ] **Step 3: Add stable-order tests**

Reverse input dictionary insertion order and assert byte-identical aggregate outputs except when an explicit `generated_at` value differs.

- [ ] **Step 4: Add aggregate commit support to the publication orchestrator**

After the event loop, compare aggregate output content with the current aggregate files. If bytes changed, publish one commit with subject `catalog: refresh materialized views`. If only `generated_at` would change and no meaningful aggregate content changed, do not create a timestamp-only commit.

- [ ] **Step 5: Run focused tests**

```bash
pytest tests/test_publishing.py tests/test_catalog.py tests/test_publication.py tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the slice**

```bash
git add src/skill_observatory/publishing.py src/skill_observatory/catalog.py src/skill_observatory/cli.py tests/test_publishing.py tests/test_catalog.py tests/test_publication.py tests/test_cli.py
git commit -m "refactor: materialize catalog from published records"
```

---

### Task 9: Replace the giant push workflow and add resumable bootstrap mode

**Depends on:** Task 8

**Files:**
- Modify: `.github/workflows/refresh.yml`
- Create: `.github/workflows/bootstrap-catalog.yml`
- Modify: `tests/test_workflows.py`
- Modify: `README.md`

**Scheduled workflow contract:**

Keep:

```yaml
on:
  schedule:
    - cron: '7,22,37,52 * * * *'
```

Keep one publication writer with:

```yaml
concurrency:
  group: atomic-skill-publication
  cancel-in-progress: false
```

Replace the current shell `git add`, `git commit`, and `git push` block with:

```text
skillobs refresh
skillobs publish-events --max-events 100 --time-budget-seconds 420
```

Pass:

```text
SKILLOBS_GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }}
```

Keep:

```yaml
permissions:
  contents: write
```

The workflow must never use a PAT by default and must never use a force push.

**Bootstrap workflow contract:**

`bootstrap-catalog.yml` is `workflow_dispatch` only. Use the same concurrency group and the same code path. Inputs:

```text
max_repositories default 100
max_events       default 500
time_budget      default 2400
```

Bootstrap is resumable because each run recomputes the delta from canonical records already on `main`.

- [ ] **Step 1: Update workflow tests first**

Assert:

- the 15-minute cron remains exact;
- `refresh.yml` contains `skillobs publish-events`;
- no workflow contains `git push --force`, `force: true`, or the old giant `git add README.md AWESOME.md ...` publication block;
- scheduled mode passes 100 events and 420 seconds;
- bootstrap is manual only and defaults to 500 events;
- both publication workflows share the same concurrency group.

- [ ] **Step 2: Run the workflow test and observe RED**

```bash
pytest tests/test_workflows.py -v
```

Expected: FAIL against the current snapshot workflow.

- [ ] **Step 3: Replace scheduled publication orchestration**

Keep scan and cache steps. Replace only the publication and summary sections needed for the new report.

- [ ] **Step 4: Add bootstrap workflow**

Do not duplicate publication logic in shell. The workflow only supplies limits to `skillobs publish-events`.

- [ ] **Step 5: Expand the GitHub Action summary**

Report:

```text
Repositories scanned
Skills observed
Events detected
Events published
ADD count
UPDATE count
REINDEX count
REMOVE count
Conflicts retried
Failures
Remaining deferred count
main before SHA
main after SHA
```

- [ ] **Step 6: Update the README operations section**

Explain that catalog history is now per-Skill on `main`, while `AWESOME.md` and `data/*` are aggregate materialized views.

- [ ] **Step 7: Run workflow and CLI tests**

```bash
pytest tests/test_workflows.py tests/test_cli.py tests/test_publication.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit the slice**

```bash
git add .github/workflows/refresh.yml .github/workflows/bootstrap-catalog.yml tests/test_workflows.py README.md
git commit -m "ci: publish each skill as an atomic main commit"
```

---

### Task 10: Prove race safety, crash recovery, and no duplicate publication end to end

**Depends on:** Task 9

**Files:**
- Create: `tests/test_atomic_publication_e2e.py`
- Modify only if a failing acceptance test proves a production defect: `src/skill_observatory/events.py`, `src/skill_observatory/directory.py`, `src/skill_observatory/github_publisher.py`, or `src/skill_observatory/publication.py`

**Acceptance scenarios:**

1. Two new Skills produce two sequential commits with different SHAs.
2. A run that stops after the first of two events leaves the first Skill fully browseable and the second unpublished.
3. The next run recomputes only the second event.
4. A concurrent human commit moves `main` between GitHub commit creation and ref update. The publisher retries on the new head without force and without losing the human commit.
5. A simulated response loss after a successful ref update does not create a duplicate Skill commit on retry.
6. A stars-only change creates no Skill event.
7. One successful miss creates no removal.
8. Two successful misses create one removal commit.
9. A failed repository scan does not increase the miss counter.
10. A malformed generated canonical record fails closed before any GitHub mutation.
11. A root README edit outside the generated marker block survives a concurrent Skill publication.
12. `AWESOME.md` can be regenerated from canonical published records after deleting all local aggregate files.

- [ ] **Step 1: Build the in-memory fake GitHub repository**

Model refs, trees, blobs, commits, and file contents closely enough to exercise the public `GitHubAtomicPublisher` interface without mocking private helpers.

- [ ] **Step 2: Add each acceptance scenario one at a time**

Run the new test after each scenario and fix only the behavior exposed by that test.

- [ ] **Step 3: Run the full unit and integration suite**

```bash
pytest --cov=skill_observatory --cov-report=term-missing --cov-fail-under=80
```

Expected: PASS with coverage at or above 80%.

- [ ] **Step 4: Run static verification**

```bash
ruff check src tests
mypy src
python -m compileall -q src
```

Expected: all commands exit 0.

- [ ] **Step 5: Run migration verification**

```bash
rm -f migration-check.db
SKILLOBS_DATABASE_URL=sqlite+pysqlite:///./migration-check.db skillobs migrate
alembic check
rm -f migration-check.db
```

Expected: migration reaches head and Alembic reports no new upgrade operations.

- [ ] **Step 6: Commit the proof slice**

```bash
git add tests/test_atomic_publication_e2e.py src/skill_observatory/events.py src/skill_observatory/directory.py src/skill_observatory/github_publisher.py src/skill_observatory/publication.py
git commit -m "test: prove atomic publication recovery semantics"
```

Only add production files that actually changed while making a failing acceptance test pass.

---

### Task 11: Roll out the new publication model and capture production proof

**Depends on:** Task 10

**Files:**
- Modify: `VERIFICATION.md`
- Modify: `CHANGELOG.md`
- Modify: `SECURITY.md` only if publication security assumptions are not already documented
- Modify: `README.md` only for final operator-facing instructions not already covered in Task 9

**Rollout sequence:**

1. Merge the implementation branch only after CI, Ruff, mypy, migrations, tests, and CodeQL are green.
2. Run `bootstrap-catalog.yml` manually with `max_events=25` first.
3. Inspect the resulting 25 `skill(...)` commits directly on `main`.
4. Verify one canonical JSON record, one Skill Markdown page, its repository page, its category page, and the root README marker block against the same commit SHA.
5. Run bootstrap again with `max_events=500` after the 25-event canary proves commit correctness.
6. Repeat bootstrap until the observation-to-publication delta reaches zero or only explicitly deferred failures remain.
7. Allow at least two scheduled 15-minute runs to execute after bootstrap.
8. During one controlled verification run, advance `main` with an unrelated documentation commit while publication is active and confirm the publisher retries successfully.
9. Confirm a no-op scheduled run creates no Skill commits and no timestamp-only aggregate commit.
10. Record exact workflow run links, commit SHAs, counts, and remaining failures in `VERIFICATION.md`.

**Production readiness criteria:**

- Every semantic Skill mutation is represented by one `skill(...)` commit.
- No Skill event commit contains two canonical Skill record mutations.
- Every published Skill has both canonical JSON and human-readable Markdown.
- Every published Skill appears in its repository page and each active category page.
- Root README content outside the generated markers is preserved.
- No-op scans create no meaningless commits.
- Stars-only changes do not create per-Skill commits.
- Confirmed removals require two successful misses.
- Failed repository scans cannot remove Skills.
- Ref races recover without force updates.
- Interrupted runs converge on the next run.
- Full `AWESOME.md` and `data/*` regenerate from canonical records.
- Scheduled cadence remains every 15 minutes.
- CI, Ruff, mypy, Alembic check, pytest coverage gate, and CodeQL are green.

- [ ] **Step 1: Perform the 25-event canary and record proof**

- [ ] **Step 2: Complete bootstrap in resumable batches**

- [ ] **Step 3: Observe two scheduled runs and one controlled ref race**

- [ ] **Step 4: Update verification and changelog documentation with measured evidence**

- [ ] **Step 5: Commit rollout documentation**

```bash
git add VERIFICATION.md CHANGELOG.md SECURITY.md README.md
git commit -m "docs: record atomic publication rollout"
```

Only stage files that changed.

---

## Final verification gate

Run this exact gate after all implementation tasks and before declaring the migration complete:

```bash
pytest --cov=skill_observatory --cov-report=term-missing --cov-fail-under=80
ruff check src tests
mypy src
python -m compileall -q src
rm -f migration-check.db
SKILLOBS_DATABASE_URL=sqlite+pysqlite:///./migration-check.db skillobs migrate
alembic check
rm -f migration-check.db
```

Then verify GitHub-hosted evidence:

```text
CI                         PASS
CodeQL                     PASS
Dependency Review          PASS or explicit repository-feature warning with no hidden failure
Agent Skills lint          PASS
25-event bootstrap canary  PASS
500-event bootstrap batch  PASS
2 scheduled refresh runs   PASS
controlled main race       PASS
no-op run                  produces zero Skill commits
```

## Rollback and recovery

Do not rewrite Git history to roll back this migration.

If the new publisher has a production defect:

1. Disable the scheduled publication step or restore the previous workflow through a normal revert commit.
2. Leave already-published canonical Skill records on `main`; they are append/update history, not destructive database migration state.
3. Fix the defect through TDD.
4. Re-enable publication.
5. Recompute the delta from the observation database against canonical records on `main`.
6. Let idempotent publication converge without replaying already-matching Skills.

If a bad generated Skill event commit reached `main`, use a normal Git revert commit for that event. Never use reset or force push.

## Implementation ownership

Use one writer for the publication core because `events.py`, `directory.py`, `github_publisher.py`, and `publication.py` share one atomicity invariant. Parallel workers may independently handle documentation or test-fixture preparation only after their interfaces are fixed. The integration owner must run the full final verification gate and inspect the actual `main` commit history after the bootstrap canary.

## Explicit non-goals for this migration

Do not add these while implementing Atomic Skill Publication v1:

- dynamic execution of third-party Skills;
- malware certification claims;
- embeddings or semantic search;
- user submission or moderation flows;
- GitHub App installation architecture unless `GITHUB_TOKEN` is proven insufficient for repository rules;
- a separate durable event queue;
- per-star or per-fork Skill commits;
- rewriting all existing aggregate APIs around the new canonical layout when current API behavior can remain compatible;
- unrelated discovery expansion or ranking methodology changes.

## Completion statement

This migration is complete only when the GitHub repository itself is the durable, browsable publication surface and the history is meaningful at Skill granularity: one semantic Skill event, one direct fast-forward commit on `main`, deterministic generated directory state, safe retry after races, and reproducible aggregate views.