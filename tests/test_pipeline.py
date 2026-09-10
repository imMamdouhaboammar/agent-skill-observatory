from datetime import UTC, datetime

from sqlalchemy import select

from skill_observatory.db import SkillRecord, init_database, make_session_factory
from skill_observatory.domain import DiscoveredRepository
from skill_observatory.pipeline import index_repository


class FakeGitHub:
    tree = [
        {"path": "README.md", "type": "blob"},
        {"path": "tests/test_demo.py", "type": "blob"},
        {"path": "skills/demo/SKILL.md", "type": "blob"},
        {"path": "skills/demo/scripts/check.py", "type": "blob"},
    ]
    files = {
        "skills/demo/SKILL.md": (
            "---\n"
            "name: demo\n"
            "description: Review repositories safely. "
            "Use when an agent must inspect project evidence.\n"
            "license: MIT\n"
            "---\n"
            "# Demo\n"
            "Inspect evidence before making claims.\n"
        ),
        "skills/demo/scripts/check.py": "print('ok')\n",
    }

    def recursive_tree(self, repo):
        return self.tree

    def read_text_file(self, repo, path, max_bytes=512_000):
        return self.files[path]


def test_indexes_verified_skill_into_database(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'pipeline.db'}"
    init_database(url)
    factory = make_session_factory(url)
    repo = DiscoveredRepository(
        full_name="example/skills",
        html_url="https://github.com/example/skills",
        default_branch="main",
        description="demo",
        stars=12,
        forks=2,
        pushed_at=datetime.now(UTC),
        archived=False,
        license_spdx="MIT",
        discovery_source="test",
    )
    with factory() as session:
        count, errors = index_repository(FakeGitHub(), session, repo)  # type: ignore[arg-type]
        record = session.scalar(select(SkillRecord).where(SkillRecord.name == "demo"))
    assert errors == []
    assert count == 1
    assert record is not None
    assert record.spec_json["valid"] is True
    assert record.security_score == 100
    assert record.overall_score > 60
