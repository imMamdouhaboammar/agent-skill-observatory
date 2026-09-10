from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlparse

from .aggregate_publication import (
    AGGREGATE_PATHS,
    MEANINGFUL_AGGREGATE_PATHS,
    AggregatePublicationResult,
    validate_aggregate_outputs,
)
from .directory import DirectoryPatch, render_skill_event
from .events import PublicationResult, PublishedSkillRecord, SkillEvent
from .github_publisher import GitHubAtomicPublisher
from .publication_errors import PublicationError

BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


class LocalGitPublisherError(PublicationError):
    pass


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
        except (OSError, subprocess.CalledProcessError) as exc:
            if isinstance(exc, subprocess.CalledProcessError):
                detail = (exc.stderr or exc.stdout or "git command failed").strip()
            else:
                detail = str(exc)
            raise LocalGitPublisherError(detail) from exc
        return result.stdout.strip()

    def _path(self, relative: str) -> Path:
        path = (self.checkout_root / relative).resolve()
        if path != self.checkout_root and self.checkout_root not in path.parents:
            raise LocalGitPublisherError(f"unsafe publication path: {relative}")
        return path

    @staticmethod
    def _normalize_repository(value: str) -> str:
        raw = value.strip()
        if raw.startswith("git@github.com:"):
            path = raw.split(":", 1)[1]
        else:
            parsed = urlparse(raw)
            if parsed.scheme:
                if (parsed.hostname or "").lower() != "github.com":
                    raise LocalGitPublisherError(
                        "remote repository is not hosted on github.com"
                    )
                path = parsed.path
            else:
                path = raw
        path = path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        parts = path.split("/")
        if len(parts) != 2 or not all(parts):
            raise LocalGitPublisherError("invalid GitHub repository identity")
        return f"{parts[0]}/{parts[1]}".lower()

    def _validate_repository(self, repository: str) -> None:
        try:
            fetch_origin = self._git("remote", "get-url", "origin")
            push_origins_text = self._git(
                "remote", "get-url", "--push", "--all", "origin"
            )
        except PublicationError as exc:
            raise LocalGitPublisherError("unable to determine origin repository") from exc

        expected = self._normalize_repository(repository)
        fetch_actual = self._normalize_repository(fetch_origin)
        if fetch_actual != expected:
            raise LocalGitPublisherError(
                f"origin fetch repository {fetch_actual} does not match requested repository {expected}"
            )

        push_origins = [line.strip() for line in push_origins_text.splitlines() if line.strip()]
        if not push_origins:
            raise LocalGitPublisherError("unable to determine origin push repository")
        for push_origin in push_origins:
            push_actual = self._normalize_repository(push_origin)
            if push_actual != expected:
                raise LocalGitPublisherError(
                    f"origin push repository {push_actual} does not match requested repository {expected}"
                )

    def _ensure_clean_worktree(self) -> None:
        status = self._git("status", "--porcelain", "--untracked-files=all")
        if status:
            raise LocalGitPublisherError("local publication requires a clean Git worktree")

    def current_head(self, repository: str, branch: str = "main") -> str:
        self._validate_repository(repository)
        current_branch = self._git("branch", "--show-current")
        if current_branch != branch:
            raise LocalGitPublisherError(
                f"local checkout branch is {current_branch or 'detached'}, expected {branch}"
            )
        return self._git("rev-parse", "HEAD")

    def _read_text(self, relative: str) -> str:
        path = self._path(relative)
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise LocalGitPublisherError(f"failed to read {relative}: {exc}") from exc

    def _read_bytes_if_present(self, relative: str) -> bytes | None:
        path = self._path(relative)
        try:
            if not path.exists():
                return None
            if not path.is_file():
                raise LocalGitPublisherError(f"publication path is not a file: {relative}")
            return path.read_bytes()
        except OSError as exc:
            raise LocalGitPublisherError(f"failed to read {relative}: {exc}") from exc

    def _apply_patch(self, patch: DirectoryPatch) -> None:
        try:
            for relative, text in patch.writes.items():
                path = self._path(relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            for relative in patch.deletes:
                path = self._path(relative)
                if path.exists():
                    path.unlink()
        except OSError as exc:
            raise LocalGitPublisherError(f"failed to apply local publication patch: {exc}") from exc

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

    def _snapshot_patch(self, patch: DirectoryPatch) -> dict[str, bytes | None]:
        return {
            relative: self._read_bytes_if_present(relative)
            for relative in sorted({*patch.writes, *patch.deletes})
        }

    def _restore_snapshot(self, snapshot: dict[str, bytes | None]) -> None:
        paths = sorted(snapshot)
        if paths:
            self._git("reset", "--quiet", "HEAD", "--", *paths)
        try:
            for relative, content in snapshot.items():
                path = self._path(relative)
                if content is None:
                    if path.exists():
                        path.unlink()
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        except OSError as exc:
            raise LocalGitPublisherError(
                f"failed to restore publication paths after error: {exc}"
            ) from exc

    def _commit_patch(
        self,
        patch: DirectoryPatch,
        *,
        message: str,
        parent_sha: str,
    ) -> str | None:
        snapshot = self._snapshot_patch(patch)
        try:
            self._apply_patch(patch)
            self._stage_patch(patch)
            staged = self._git("diff", "--cached", "--name-only")
            if not staged:
                return None
            return self._commit(message)
        except Exception as exc:
            try:
                current_head = self._git("rev-parse", "HEAD")
                if current_head != parent_sha:
                    raise LocalGitPublisherError(
                        "local publication failed after HEAD advanced; refusing path rollback"
                    ) from exc
                self._restore_snapshot(snapshot)
            except PublicationError as rollback_exc:
                if rollback_exc is exc:
                    raise
                raise LocalGitPublisherError(
                    f"local publication failed and rollback could not be completed: {rollback_exc}"
                ) from exc
            if isinstance(exc, PublicationError):
                raise
            raise LocalGitPublisherError(f"local publication failed: {exc}") from exc

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
        self._ensure_clean_worktree()
        readme_path = self._path("README.md")
        if not readme_path.is_file():
            raise LocalGitPublisherError("root README.md is missing")
        patch = render_skill_event(
            event,
            catalog_after_event,
            current_root_readme=self._read_text("README.md"),
        )
        commit_sha = self._commit_patch(
            patch,
            message=GitHubAtomicPublisher._commit_message(event),
            parent_sha=parent_sha,
        )
        if commit_sha is None:
            return PublicationResult(
                canonical_key=event.canonical_key,
                event_type=event.type,
                status="noop",
                parent_sha=parent_sha,
                attempts=1,
            )
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
    publisher._ensure_clean_worktree()

    current: dict[str, str | None] = {}
    for relative in sorted(AGGREGATE_PATHS):
        path = publisher._path(relative)
        current[relative] = publisher._read_text(relative) if path.is_file() else None

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
    commit_sha = publisher._commit_patch(
        patch,
        message="catalog: refresh materialized views",
        parent_sha=parent_sha,
    )
    if commit_sha is None:
        return AggregatePublicationResult(status="noop", parent_sha=parent_sha)
    return AggregatePublicationResult(
        status="published",
        commit_sha=commit_sha,
        parent_sha=parent_sha,
        files_changed=sorted(writes),
    )
