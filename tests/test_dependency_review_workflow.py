from pathlib import Path


def test_dependency_manifest_detection_cannot_fail_open_via_pipefail_sigpipe() -> None:
    workflow = Path(".github/workflows/dependency-review.yml").read_text(encoding="utf-8")

    assert "set -euo pipefail" in workflow
    assert "grep -Eq" in workflow
    assert '<<< "$CHANGED_FILES"' in workflow
    assert 'printf \'%s\\n\' "$CHANGED_FILES" | grep -Eq' not in workflow
    assert "steps.dependencies.outputs.changed == 'true'" in workflow
    assert "Dependency Review is a required release gate and must fail closed" in workflow
