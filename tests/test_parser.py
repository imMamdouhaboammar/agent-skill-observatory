from pathlib import Path

import pytest

from skill_observatory.parser import SkillParseError, parse_skill_directory

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_valid_skill_and_resources() -> None:
    parsed = parse_skill_directory(FIXTURES / "sample-skill")
    assert parsed.name == "sample-skill"
    assert parsed.description.startswith("Analyze repositories")
    assert parsed.license == "MIT"
    assert parsed.metadata["author"] == "example"
    assert parsed.allowed_tools == ["Bash", "Read", "Grep"]
    assert parsed.resource_counts.scripts == 1
    assert parsed.spec.valid is True
    assert parsed.spec.errors == []


def test_rejects_directory_name_mismatch(tmp_path: Path) -> None:
    skill_dir = tmp_path / "wrong-directory"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: different-name\ndescription: Useful skill. Use when needed.\n---\nBody\n",
        encoding="utf-8",
    )
    parsed = parse_skill_directory(skill_dir)
    assert parsed.spec.valid is False
    assert any("parent directory" in error for error in parsed.spec.errors)


def test_missing_frontmatter_raises(tmp_path: Path) -> None:
    skill_dir = tmp_path / "missing"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# No metadata", encoding="utf-8")
    with pytest.raises(SkillParseError):
        parse_skill_directory(skill_dir)
