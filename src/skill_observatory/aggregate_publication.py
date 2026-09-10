from __future__ import annotations

import time
from collections.abc import Callable
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, Field

from .directory import DirectoryPatch
from .github_publisher import (
    GitHubAtomicPublisher,
    GitHubPublicationConflict,
    GitHubPublisherTransportError,
)

AGGREGATE_PATHS = frozenset(
    {
        "AWESOME.md",
        "data/catalog.json",
        "data/catalog.csv",
        "data/repositories.json",
        "data/stats.json",
        "data/refresh.json",
    }
)
MEANINGFUL_AGGREGATE_PATHS = AGGREGATE_PATHS - {"data/refresh.json"}


class AggregatePublicationResult(BaseModel):
    status: Literal["published", "noop", "deferred"]
    commit_sha: str | None = None
    parent_sha: str | None = None
    attempts: int = 1
    files_changed: list[str] = Field(default_factory=list)


def _validate_outputs(outputs: dict[str, str]) -> None:
    invalid = set(outputs) - AGGREGATE_PATHS
    if invalid:
        raise ValueError(f"invalid aggregate path(s): {', '.join(sorted(invalid))}")
    missing = AGGREGATE_PATHS - set(outputs)
    if missing:
        raise ValueError(f"missing aggregate path(s): {', '.join(sorted(missing))}")


def publish_materialized_views(
    publisher: GitHubAtomicPublisher,
    outputs: dict[str, str],
    *,
    repository: str,
    branch: str = "main",
    max_attempts: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> AggregatePublicationResult:
    _validate_outputs(outputs)
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(1, max_attempts + 1):
        try:
            head_sha = publisher.current_head(repository, branch)
            tree_sha = publisher._commit_tree(repository, head_sha)
            current: dict[str, str | None] = {}
            for path in sorted(AGGREGATE_PATHS):
                current[path] = publisher._read_text(
                    repository,
                    path,
                    ref=head_sha,
                    allow_missing=True,
                )

            meaningful_changed = any(
                current[path] != outputs[path]
                for path in MEANINGFUL_AGGREGATE_PATHS
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
            blob_shas = publisher._create_blobs(repository, patch)
            new_tree_sha = publisher._create_tree(
                repository,
                base_tree=tree_sha,
                patch=patch,
                blob_shas=blob_shas,
            )
            payload = publisher._post(
                f"/repos/{repository}/git/commits",
                {
                    "message": "catalog: refresh materialized views",
                    "tree": new_tree_sha,
                    "parents": [head_sha],
                },
            )
            commit_sha = publisher._required_str(payload, "sha")
            publisher._patch_ref(
                f"/repos/{repository}/git/refs/heads/{quote(branch, safe='')}",
                {"sha": commit_sha, "force": False},
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
                return AggregatePublicationResult(
                    status="deferred",
                    attempts=attempt,
                )
            sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))
        except GitHubPublisherTransportError:
            if attempt >= max_attempts:
                raise
            sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))

    raise AssertionError("unreachable aggregate publication retry state")
