from pathlib import Path

from skill_observatory.parser import parse_skill_directory
from skill_observatory.security import assess_skill_security

FIXTURES = Path(__file__).parent / "fixtures"


def test_safe_skill_has_no_high_risk_findings() -> None:
    parsed = parse_skill_directory(FIXTURES / "sample-skill")
    report = assess_skill_security(parsed)
    assert report.high == 0
    assert report.critical == 0
    assert report.score >= 85


def test_risky_shell_patterns_are_flagged() -> None:
    parsed = parse_skill_directory(FIXTURES / "risky-skill")
    report = assess_skill_security(parsed)
    rules = {finding.rule for finding in report.findings}
    assert "pipe-to-shell" in rules
    assert "recursive-delete" in rules
    assert report.high >= 1
    assert report.score < 85
