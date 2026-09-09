from pathlib import Path

from skill_observatory.classification import classify_categories, infer_clients


def test_classifies_engineering_and_security_keywords() -> None:
    categories = classify_categories(
        "Review pull requests for security vulnerabilities and dependency risks",
        "Run static analysis and inspect CI failures",
    )
    assert "engineering" in categories
    assert "security" in categories


def test_infers_clients_from_standard_paths_and_openai_metadata() -> None:
    files = [Path("agents/openai.yaml")]
    evidence = infer_clients(
        path=".agents/skills/review-code",
        compatibility="Designed for Claude Code",
        files=files,
    )
    assert "OpenAI Codex" in evidence
    assert "Claude Code" in evidence
    assert "GitHub Copilot" in evidence
