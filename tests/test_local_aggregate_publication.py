from __future__ import annotations

import subprocess
from pathlib import Path

from skill_observatory.aggregate_publication import AGGREGATE_PATHS
from skill_observatory.local_git_publisher import (
    LocalGitAtomicPublisher,
    publish_local_materialized_views,
)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _outputs(marker: str) -> dict[str, str]:
    return {path: f"{path}:{marker}\n" for path in AGGREGATE_PATHS}


def _prepare_repo(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Test Bot")
    _git(root, "config", "user.email", "bot@example.com")
    for relative, text in _outputs("old").items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "README.md").write_text("# Human README\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "initial")


def test_local_materialized_views_create_one_aggregate_commit(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)
    initial_head = _git(tmp_path, "rev-parse", "HEAD")

    result = publish_local_materialized_views(
        publisher,
        _outputs("new"),
        repository="acme/observatory",
        branch="main",
    )

    assert result.status == "published"
    assert result.parent_sha == initial_head
    assert result.commit_sha == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "rev-list", "--count", f"{initial_head}..HEAD") == "1"
    assert _git(tmp_path, "log", "-1", "--pretty=%s") == "catalog: refresh materialized views"
    assert set(result.files_changed) == AGGREGATE_PATHS


def test_refresh_timestamp_only_does_not_create_aggregate_commit(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    outputs = _outputs("old")
    outputs["data/refresh.json"] = "new timestamp only\n"

    result = publish_local_materialized_views(
        publisher,
        outputs,
        repository="acme/observatory",
        branch="main",
    )

    assert result.status == "noop"
    assert result.parent_sha == initial_head
    assert _git(tmp_path, "rev-parse", "HEAD") == initial_head
