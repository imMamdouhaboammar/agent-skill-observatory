from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from skill_observatory.classification import classify_categories, infer_clients
from skill_observatory.domain import DiscoveredRepository
from skill_observatory.github import GitHubError
from skill_observatory.parser import parse_skill_directory
from skill_observatory.pipeline import (
    _candidate_skill_roots,
    _paths_for_skill,
    _repo_has_readme,
    _repo_has_tests,
    _safe_local_path,
    refresh_catalog,
)
from skill_observatory.security import assess_skill_security


def test_safe_local_path_rejects_directory_traversal(tmp_path: Path) -> None:
    base = tmp_path / "sandbox"
    base.mkdir()
    with pytest.raises(ValueError, match="unsafe repository path"):
        _safe_local_path(base, "../../../etc/passwd")


def test_candidate_skill_roots_detects_nested_manifests() -> None:
    tree = [
        {"path": "SKILL.md", "type": "blob"},
        {"path": "nested/skill/SKILL.md", "type": "blob"},
        {"path": "nested/skill/SKILL.md", "type": "tree"},  # ignored: not blob
        {"path": "nested/other/README.md", "type": "blob"},
    ]
    roots = _candidate_skill_roots(tree)
    assert roots == ["", "nested/skill"]


def test_paths_for_skill_filters_supported_resources() -> None:
    tree = [
        {"path": "skills/demo/SKILL.md", "type": "blob"},
        {"path": "skills/demo/scripts/runner.sh", "type": "blob"},
        {"path": "skills/demo/references/doc.txt", "type": "blob"},
        {"path": "skills/demo/unknown/binary.bin", "type": "blob"},
        {"path": "other/unrelated.py", "type": "blob"},
    ]
    paths = _paths_for_skill(tree, "skills/demo")
    assert "skills/demo/SKILL.md" in paths
    assert "skills/demo/scripts/runner.sh" in paths
    assert "skills/demo/references/doc.txt" in paths
    assert "skills/demo/unknown/binary.bin" not in paths
    assert "other/unrelated.py" not in paths


def test_repo_signals_detection_for_tests_and_readme() -> None:
    tree_with_both = [
        {"path": "README.md", "type": "blob"},
        {"path": "tests/test_main.py", "type": "blob"},
    ]
    assert _repo_has_readme(tree_with_both) is True
    assert _repo_has_tests(tree_with_both) is True

    tree_empty: list[dict[str, str]] = []
    assert _repo_has_readme(tree_empty) is False
    assert _repo_has_tests(tree_empty) is False


def test_classification_and_client_inference() -> None:
    categories = classify_categories(
        description="Kubernetes deployment and docker pipeline automation",
        body="Includes terraform and cloud configs for SRE team.",
    )
    assert "devops" in categories

    # Fallback to other
    fallback = classify_categories(description="xyz abc", body="123 456")
    assert fallback == ["other"]

    # Client inference from paths and files
    evidence = infer_clients(
        path=".agents/skills/my-skill",
        compatibility="Claude, OpenAI Codex, Copilot",
        files=[Path("agents/openai.yaml"), Path(".claude/skills/demo/SKILL.md")],
    )
    assert "OpenAI Codex" in evidence
    assert "Claude Code" in evidence
    assert "GitHub Copilot" in evidence


def test_security_scanner_flags_dangerous_commands() -> None:
    fixture = Path("tests/fixtures/risky-skill")
    parsed = parse_skill_directory(fixture)
    security = assess_skill_security(parsed)

    assert security.score < 100
    rules = {f.rule for f in security.findings}
    assert "credential-access" in rules or "pipe-to-shell" in rules or len(rules) > 0


class MockFailingGitHub:
    def discover(self):
        return [
            DiscoveredRepository(
                full_name="org/error-repo",
                html_url="https://github.com/org/error-repo",
                default_branch="main",
                description="Failing repo",
                stars=5,
                forks=1,
                pushed_at=datetime.now(UTC),
                archived=False,
                license_spdx="MIT",
                topics=[],
                discovery_source="test",
            )
        ]

    def recursive_tree(self, repo):
        raise GitHubError("API rate limit exceeded")


def test_refresh_catalog_captures_repository_errors(tmp_path: Path) -> None:
    from skill_observatory.db import init_database, make_session_factory

    db_url = f"sqlite+pysqlite:///{tmp_path / 'refresh_err.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)

    client = MockFailingGitHub()
    with factory() as session:
        report = refresh_catalog(client, session, max_repositories=1)  # type: ignore[arg-type]

    assert report["repositories_seen"] == 1
    assert report["repositories_with_skills"] == 0
    assert len(report["errors"]) == 1
    assert "API rate limit exceeded" in report["errors"][0]
