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


def test_unrestricted_host_filesystem_server_is_flagged(tmp_path: Path) -> None:
    skill_root = tmp_path / "file-server"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\n"
        "name: file-server\n"
        "description: The built-in file browser serves any file on the host filesystem.\n"
        "---\n\n"
        "# File server\n"
        "Use the built-in file browser to serve any file on the host filesystem.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" in {finding.rule for finding in report.findings}
    assert report.high >= 1
    assert report.score < 85


def test_explicitly_confined_file_server_is_not_flagged(tmp_path: Path) -> None:
    skill_root = tmp_path / "file-server"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\n"
        "name: file-server\n"
        "description: Serve files from a configured shared directory only.\n"
        "---\n\n"
        "# File server\n"
        "Restrict access to a configured share root; deny paths outside it.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" not in {finding.rule for finding in report.findings}


def test_host_file_access_variants_are_detected_independently(tmp_path: Path) -> None:
    for index, sentence in enumerate(
        [
            "Serve any file on the host filesystem.",
            "Provides access to any host file.",
        ]
    ):
        skill_root = tmp_path / f"case-{index}" / "file-server"
        skill_root.mkdir(parents=True)
        (skill_root / "SKILL.md").write_text(
            "---\n"
            "name: file-server\n"
            f"description: {sentence}\n"
            "---\n\n"
            "# File server\n"
            "Follow the manifest instructions.\n",
            encoding="utf-8",
        )
        report = assess_skill_security(parse_skill_directory(skill_root))
        assert "unrestricted-host-file-access" in {item.rule for item in report.findings}, sentence
        assert report.score < 85, sentence


def test_access_within_local_share_root_is_not_flagged(tmp_path: Path) -> None:
    skill_root = tmp_path / "file-server"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\n"
        "name: file-server\n"
        "description: Reads any file in the local share root.\n"
        "---\n\n"
        "# File server\n"
        "Only access files within the local share root.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" not in {item.rule for item in report.findings}


def test_wrapped_unrestricted_host_access_is_detected(tmp_path: Path) -> None:
    skill_root = tmp_path / "file-server"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: file-server\n"
        "description: File navigation instructions.\n---\n\n"
        "# File serving\n"
        "Serve any file\n"
        "on the host filesystem.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" in {finding.rule for finding in report.findings}


def test_denied_unrestricted_access_is_not_flagged(tmp_path: Path) -> None:
    skill_root = tmp_path / "file-server"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: file-server\n"
        "description: Restricted file access.\n---\n\n"
        "# Protection\n"
        "Never serve any file on the host filesystem.\n"
        "Block attempts to read all local files.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" not in {finding.rule for finding in report.findings}


def test_confined_all_local_files_are_not_unrestricted(tmp_path: Path) -> None:
    skill_root = tmp_path / "file-server"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: file-server\n"
        "description: Restricted local file sharing.\n---\n\n"
        "# Shared files\n"
        "The server reads all local files inside the configured share root only.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" not in {finding.rule for finding in report.findings}


def test_unrelated_prohibition_does_not_hide_unrestricted_access(tmp_path: Path) -> None:
    skill_root = tmp_path / "mixed-security-clauses"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: mixed-security-clauses\ndescription: Security guidance.\n---\n\n"
        "Never delete local data. Serve any file on the host filesystem.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" in {finding.rule for finding in report.findings}


def test_bounded_default_does_not_hide_unrestricted_mode(tmp_path: Path) -> None:
    skill_root = tmp_path / "mixed-share-modes"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: mixed-share-modes\ndescription: Configurable files.\n---\n\n"
        "Serve files from the configured share root by default; --root / exposes every host file.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" in {finding.rule for finding in report.findings}


def test_safe_prohibition_and_bounded_clause_remain_unflagged(tmp_path: Path) -> None:
    skill_root = tmp_path / "allowed-bounded-mode"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: allowed-bounded-mode\ndescription: Configured share only.\n---\n\n"
        "Never serve any file on the host filesystem.\n"
        "Read all local files inside the configured share root only.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    assert "unrestricted-host-file-access" not in {finding.rule for finding in report.findings}


def test_wrapped_unrestricted_access_is_reported_once_at_starting_line(tmp_path: Path) -> None:
    skill_root = tmp_path / "wrapped-single-finding"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: wrapped-single-finding\ndescription: Documentation.\n---\n\n"
        "Serve any file\n"
        "on the host filesystem.\n",
        encoding="utf-8",
    )
    report = assess_skill_security(parse_skill_directory(skill_root))
    findings = [f for f in report.findings if f.rule == "unrestricted-host-file-access"]
    assert len(findings) == 1
    assert findings[0].line == 6
