from pathlib import Path

from skill_observatory.classification import classify_categories, infer_clients


def test_classifies_engineering_and_security_keywords() -> None:
    categories = classify_categories(
        "Review pull requests for security vulnerabilities and dependency risks",
        "Run static analysis and inspect CI failures",
    )
    assert "engineering" in categories
    assert "security" in categories


def test_classifies_new_domain_categories() -> None:
    categories = classify_categories(
        "Build an LLM marketing research workflow for campaign analytics",
        "Use embeddings and model evaluation, then generate ads and browser reports.",
    )
    assert "ai-ml" in categories
    assert "marketing" in categories
    assert "research" in categories


def test_classifies_architecture_orchestration_and_business_domains() -> None:
    categories = classify_categories(
        "Plan software architecture and multi-agent orchestration for business strategy",
        "Record architecture decisions and coordinate subagents around the operating model.",
    )

    assert "architecture" in categories
    assert "agent-orchestration" in categories
    assert "business" in categories


def test_classifies_sales_hr_localization_and_document_domains() -> None:
    categories = classify_categories(
        "Support recruiting and sales operations across localized customer documents",
        "Screen candidate resumes, update CRM outreach, translate PDFs, and review DOCX files.",
    )

    assert "sales" in categories
    assert "hr-recruiting" in categories
    assert "localization" in categories
    assert "documents" in categories


def test_short_keywords_do_not_match_inside_unrelated_words() -> None:
    categories = classify_categories(
        "Build reliable workflows for repeatable delivery",
        "Follow the workflow and report the result.",
    )

    assert "productivity" in categories
    assert "design" not in categories


def test_category_assignment_is_bounded_and_deterministic() -> None:
    description = "API browser automation for mobile product analytics and documentation"
    body = (
        "Integrate REST webhooks with databases, run UI tests, write docs, plan product tasks, "
        "and automate browser workflows for mobile releases."
    )

    first = classify_categories(description, body)
    second = classify_categories(description, body)

    assert first == second
    assert 1 <= len(first) <= 6


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
