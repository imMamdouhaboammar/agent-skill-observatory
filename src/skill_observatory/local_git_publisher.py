from __future__ import annotations

import subprocess
from pathlib import Path

from .aggregate_publication import (
    AGGREGATE_PATHS,
    MEANINGFUL_AGGREGATE_PATHS,
    AggregatePublicationResult,
    validate_aggregate_outputs,
)
from .directory import DirectoryPatch, render_skill_event
from .events import PublicationResult, PublishedSkillRecord, SkillEvent
from .github_publisher import GitHubAtomicPublisher, GitHubPublisherError

BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


class LocalGitAtomicPublisher:
    """Create atomic publication commits in an existing local Git checkout."""

    def __init__(self, *, checkout_root: Path) -> None:
        self.checkout_root = checkout_root.resolve()

    def _git(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.checkout_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "git command failed").strip()
            raise GitHubPublisherError(detail) from exc
        return result.stdout.strip()

    def _path(self, relative: str) -> Path:
        path = (self.checkout_root / relative).resolve()
        if path != self.checkout_root and self.checkout_root not in path.parents:
            raise GitHubPublisherError(f"unsafe publication path: {relative}")
        return path

    def _ensure_clean_index(self) -> None:
        staged = self._git("diff", "--cached", "--name-only")
        if staged:
            raise GitHubPublisherError("local publication requires a clean Git index")

    def current_head(self, repository: str, branch: str = "main") -> str:
        del repository
        current_branch = self._git("branch", "--show-current")
        if current_branch != branch:
            raise GitHubPublisherError(
                f"local checkout branch is {current_branch or 'detached'}, expected {branch}"
            )
        return self._git("rev-parse", "HEAD")

    def _apply_patch(self, patch: DirectoryPatch) -> None:
        for relative, text in patch.writes.items():
            path = self._path(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for relative in patch.deletes:
            path = self._path(relative)
            if path.exists():
                path.unlink()

    def _stage_patch(self, patch: DirectoryPatch) -> None:
        paths = sorted({*patch.writes, *patch.deletes})
        if paths:
            self._git("add", "-A", "--", *paths)

    def _commit(self, message: str) -> str:
        self._git(
            "-c",
            f"user.name={BOT_NAME}",
            "-c",
            f"user.email={BOT_EMAIL}",
            "commit",
            "-m",
            message,
        )
        return self._git("rev-parse", "HEAD")

    def publish_event(
        self,
        event: SkillEvent,
        catalog_after_event: dict[str, PublishedSkillRecord],
        *,
        repository: str,
        branch: str = "main",
        max_attempts: int = 1,
    ) -> PublicationResult:
        if max_attempts != 1:
            raise ValueError("local Git publication supports exactly one attempt")

        parent_sha = self.current_head(repository, branch)
        self._ensure_clean_index()
        readme_path = self._path("README.md")
        if not readme_path.is_file():
            raise GitHubPublisherError("root README.md is missing")
        patch = render_skill_event(
            event,
            catalog_after_event,
            current_root_readme=readme_path.read_text(encoding="utf-8"),
        )
        self._apply_patch(patch)
        self._stage_patch(patch)

        staged = self._git("diff", "--cached", "--name-only")
        if not staged:
            return PublicationResult(
                canonical_key=event.canonical_key,
                event_type=event.type,
                status="noop",
                parent_sha=parent_sha,
                attempts=1,
            )

        commit_sha = self._commit(GitHubAtomicPublisher._commit_message(event))
        return PublicationResult(
            canonical_key=event.canonical_key,
            event_type=event.type,
            status="published",
            commit_sha=commit_sha,
            parent_sha=parent_sha,
            attempts=1,
            files_changed=sorted({*patch.writes, *patch.deletes}),
        )


def publish_local_materialized_views(
    publisher: LocalGitAtomicPublisher,
    outputs: dict[str, str],
    *,
    repository: str,
    branch: str = "main",
) -> AggregatePublicationResult:
    validate_aggregate_outputs(outputs)
    parent_sha = publisher.current_head(repository, branch)
    publisher._ensure_clean_index()

    current: dict[str, str | None] = {}
    for relative in sorted(AGGREGATE_PATHS):
        path = publisher._path(relative)
        current[relative] = path.read_text(encoding="utf-8") if path.is_file() else None

    meaningful_changed = any(
        current[path] != outputs[path] for path in MEANINGFUL_AGGREGATE_PATHS
    )
    if not meaningful_changed:
        return AggregatePublicationResult(status="noop", parent_sha=parent_sha)

    writes = {
        path: outputs[path]
        for path in sorted(AGGREGATE_PATHS)
        if current[path] != outputs[path]
    }
    patch = DirectoryPatch(writes=writes)
    publisher._apply_patch(patch)
    publisher._stage_patch(patch)
    commit_sha = publisher._commit("catalog: refresh materialized views")
    return AggregatePublicationResult(
        status="published",
        commit_sha=commit_sha,
        parent_sha=parent_sha,
        files_changed=sorted(writes),
    )
