from __future__ import annotations

import argparse
import hashlib
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .aggregate_publication import (
    AGGREGATE_PATHS,
    MEANINGFUL_AGGREGATE_PATHS,
    AggregatePublicationResult,
    validate_aggregate_outputs,
)
from .config import Settings
from .db import init_database, make_session_factory
from .directory import DirectoryPatch, render_skill_event
from .events import PublicationResult, PublishedSkillRecord, SkillEvent
from .github_publisher import (
    GitHubAtomicPublisher,
    GitHubPublicationConflict,
    GitHubPublisherError,
    GitHubPublisherTransportError,
)
from .publication import PublicationReport, publish_pending_events
from .publication_errors import PublicationError

BOT_BRANCH_PREFIX = "bot/observatory-patch/"


class GitHubPullRequestPublisher(GitHubAtomicPublisher):
    """Publish one generated patch as one commit on a bot PR branch."""

    def _get_list(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            response = self._client.get(path, params=params)
        except httpx.RequestError as exc:
            raise GitHubPublisherTransportError(f"GitHub transport failure: {exc}") from exc
        if response.is_error:
            raise GitHubPublisherError(
                f"GitHub GET {path} failed with {response.status_code}: {response.text[:500]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubPublisherError(f"GitHub GET {path} returned invalid JSON") from exc
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise GitHubPublisherError(f"GitHub GET {path} returned non-list JSON")
        return payload

    def _open_bot_pr(self, repository: str, base_branch: str) -> dict[str, Any] | None:
        page = 1
        while True:
            pulls = self._get_list(
                f"/repos/{repository}/pulls",
                params={
                    "state": "open",
                    "base": base_branch,
                    "per_page": "100",
                    "page": str(page),
                },
            )
            for pull in pulls:
                head = pull.get("head")
                head_ref = head.get("ref") if isinstance(head, dict) else None
                if isinstance(head_ref, str) and head_ref.startswith(BOT_BRANCH_PREFIX):
                    return pull
            if len(pulls) < 100:
                return None
            page += 1

    @staticmethod
    def _slug(value: str, *, limit: int = 48) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
        return (slug or "patch")[:limit]

    @classmethod
    def _event_branch(cls, event: SkillEvent) -> str:
        record = event.after or event.before
        if record is None:
            raise GitHubPublisherError("Skill event has no state for PR branch")
        identity = "|".join(
            [
                event.type,
                event.canonical_key,
                record.source_fingerprint,
                record.analysis_fingerprint,
            ]
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        return (
            f"{BOT_BRANCH_PREFIX}skill-{event.type}-"
            f"{cls._slug(event.canonical_key)}-{digest}"
        )

    @staticmethod
    def _aggregate_branch(patch: DirectoryPatch) -> str:
        digest = hashlib.sha256()
        for path in sorted(patch.writes):
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(patch.writes[path].encode("utf-8"))
            digest.update(b"\0")
        for path in sorted(patch.deletes):
            digest.update(b"delete\0")
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
        return f"{BOT_BRANCH_PREFIX}catalog-{digest.hexdigest()[:12]}"

    def _branch_head(self, repository: str, branch: str) -> str | None:
        payload = self._get(
            f"/repos/{repository}/git/ref/heads/{quote(branch, safe='')}",
            allow_not_found=True,
        )
        if payload is None:
            return None
        return self._required_str(payload, "object", "sha")

    def _open_pull_request(
        self,
        *,
        repository: str,
        base_branch: str,
        patch_branch: str,
        title: str,
        body: str,
    ) -> None:
        self._post(
            f"/repos/{repository}/pulls",
            {
                "title": title,
                "head": patch_branch,
                "base": base_branch,
                "body": body,
                "maintainer_can_modify": False,
            },
        )

    def _propose_patch(
        self,
        patch: DirectoryPatch,
        *,
        repository: str,
        base_branch: str,
        parent_sha: str,
        patch_branch: str,
        commit_message: str,
        pr_title: str,
        pr_body: str,
    ) -> str:
        if self._open_bot_pr(repository, base_branch) is not None:
            raise GitHubPublicationConflict("another generated patch PR is still open")

        existing_branch_head = self._branch_head(repository, patch_branch)
        if existing_branch_head is not None:
            self._open_pull_request(
                repository=repository,
                base_branch=base_branch,
                patch_branch=patch_branch,
                title=pr_title,
                body=pr_body,
            )
            return existing_branch_head

        if self.current_head(repository, base_branch) != parent_sha:
            raise GitHubPublicationConflict("base branch moved while building generated patch")

        base_tree = self._commit_tree(repository, parent_sha)
        blob_shas = self._create_blobs(repository, patch)
        tree_sha = self._create_tree(
            repository,
            base_tree=base_tree,
            patch=patch,
            blob_shas=blob_shas,
        )
        commit_payload = self._post(
            f"/repos/{repository}/git/commits",
            {"message": commit_message, "tree": tree_sha, "parents": [parent_sha]},
        )
        commit_sha = self._required_str(commit_payload, "sha")
        self._post(
            f"/repos/{repository}/git/refs",
            {"ref": f"refs/heads/{patch_branch}", "sha": commit_sha},
        )
        self._open_pull_request(
            repository=repository,
            base_branch=base_branch,
            patch_branch=patch_branch,
            title=pr_title,
            body=pr_body,
        )
        return commit_sha

    def publish_event(
        self,
        event: SkillEvent,
        catalog_after_event: dict[str, PublishedSkillRecord],
        *,
        repository: str,
        branch: str = "main",
        max_attempts: int = 5,
    ) -> PublicationResult:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        patch_branch = self._event_branch(event)
        for attempt in range(1, max_attempts + 1):
            try:
                if self._open_bot_pr(repository, branch) is not None:
                    return PublicationResult(
                        canonical_key=event.canonical_key,
                        event_type=event.type,
                        status="deferred",
                        attempts=attempt,
                    )

                head_sha = self.current_head(repository, branch)
                readme = self._read_text(repository, "README.md", ref=head_sha)
                if readme is None:
                    raise GitHubPublisherError("root README.md is missing")
                current = self._read_canonical_record(repository, event, ref=head_sha)
                if self._already_applied(event, current):
                    return PublicationResult(
                        canonical_key=event.canonical_key,
                        event_type=event.type,
                        status="noop",
                        parent_sha=head_sha,
                        attempts=attempt,
                    )

                patch = render_skill_event(
                    event,
                    catalog_after_event,
                    current_root_readme=readme,
                )
                commit_sha = self._propose_patch(
                    patch,
                    repository=repository,
                    base_branch=branch,
                    parent_sha=head_sha,
                    patch_branch=patch_branch,
                    commit_message=self._commit_message(event),
                    pr_title=self._commit_subject(event),
                    pr_body="\n".join(
                        [
                            "Automated atomic Skill publication patch.",
                            "",
                            f"- Skill-Key: `{event.canonical_key}`",
                            f"- Event: `{event.type}`",
                            f"- Base: `{branch}@{head_sha}`",
                            "- Generated commits: `1`",
                            "- Merge policy: required checks, app review, then merger bot",
                            "",
                            "<!-- skill-observatory-generated-patch -->",
                        ]
                    ),
                )
                return PublicationResult(
                    canonical_key=event.canonical_key,
                    event_type=event.type,
                    status="published",
                    commit_sha=commit_sha,
                    parent_sha=head_sha,
                    attempts=attempt,
                    files_changed=sorted([*patch.writes, *patch.deletes]),
                )
            except GitHubPublicationConflict:
                if attempt >= max_attempts:
                    return PublicationResult(
                        canonical_key=event.canonical_key,
                        event_type=event.type,
                        status="deferred",
                        attempts=attempt,
                    )
                self._sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))
            except GitHubPublisherTransportError:
                if attempt >= max_attempts:
                    raise
                self._sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))

        raise AssertionError("unreachable PR publication retry state")


def publish_materialized_views_pr(
    publisher: GitHubPullRequestPublisher,
    outputs: dict[str, str],
    *,
    repository: str,
    branch: str = "main",
    max_attempts: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> AggregatePublicationResult:
    validate_aggregate_outputs(outputs)
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(1, max_attempts + 1):
        try:
            if publisher._open_bot_pr(repository, branch) is not None:
                return AggregatePublicationResult(status="deferred", attempts=attempt)

            head_sha = publisher.current_head(repository, branch)
            current: dict[str, str | None] = {}
            for path in sorted(AGGREGATE_PATHS):
                current[path] = publisher._read_text(
                    repository,
                    path,
                    ref=head_sha,
                    allow_missing=True,
                )

            meaningful_changed = any(
                current[path] != outputs[path] for path in MEANINGFUL_AGGREGATE_PATHS
            )
            if not meaningful_changed:
                return AggregatePublicationResult(
                    status="noop",
                    parent_sha=head_sha,
                    attempts=attempt,
                )

            writes = {
                path: outputs[path]
                for path in sorted(AGGREGATE_PATHS)
                if current[path] != outputs[path]
            }
            patch = DirectoryPatch(writes=writes)
            patch_branch = publisher._aggregate_branch(patch)
            commit_sha = publisher._propose_patch(
                patch,
                repository=repository,
                base_branch=branch,
                parent_sha=head_sha,
                patch_branch=patch_branch,
                commit_message="catalog: refresh materialized views",
                pr_title="catalog: refresh materialized views",
                pr_body="\n".join(
                    [
                        "Automated atomic catalog materialization patch.",
                        "",
                        f"- Base: `{branch}@{head_sha}`",
                        "- Generated commits: `1`",
                        "- Merge policy: required checks, app review, then merger bot",
                        "",
                        "<!-- skill-observatory-generated-patch -->",
                    ]
                ),
            )
            return AggregatePublicationResult(
                status="published",
                commit_sha=commit_sha,
                parent_sha=head_sha,
                attempts=attempt,
                files_changed=sorted(writes),
            )
        except GitHubPublicationConflict:
            if attempt >= max_attempts:
                return AggregatePublicationResult(status="deferred", attempts=attempt)
            sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))
        except GitHubPublisherTransportError:
            if attempt >= max_attempts:
                raise
            sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))

    raise AssertionError("unreachable aggregate PR publication retry state")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish one generated patch through a pull request")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--checkout-root", type=Path, default=Path("."))
    parser.add_argument("--max-events", type=int, default=1)
    parser.add_argument("--time-budget-seconds", type=int, default=420)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.max_events != 1:
        raise SystemExit("PR-gated publication requires --max-events 1")

    settings = Settings(database_url=args.database_url)
    init_database(settings.database_url)
    factory = make_session_factory(settings.database_url)
    publisher: GitHubPullRequestPublisher | None = None
    try:
        publisher = GitHubPullRequestPublisher(
            token=settings.github_token,
            api_url=settings.github_api_url,
            timeout_seconds=settings.request_timeout_seconds,
        )
        with factory() as session:
            report = publish_pending_events(
                session,
                publisher,
                checkout_root=args.checkout_root,
                repository=args.repository,
                branch=args.branch,
                max_events=1,
                time_budget_seconds=args.time_budget_seconds,
                aggregate_publish=publish_materialized_views_pr,
            )
    except PublicationError as exc:
        report = PublicationReport(failures=[str(exc)], global_failure=True)
    finally:
        if publisher is not None:
            publisher.close()

    print(report.model_dump_json(indent=2))
    if report.global_failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
