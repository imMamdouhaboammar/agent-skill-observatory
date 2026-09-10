from skill_observatory.dedupe import canonical_skill_key, content_fingerprint


def test_canonical_key_normalizes_owner_repo_and_path() -> None:
    expected = "openai/skills:.agents/skills/review-code"
    assert canonical_skill_key("OpenAI", "Skills", ".agents/skills/Review-Code") == expected


def test_content_fingerprint_ignores_line_endings_and_trailing_space() -> None:
    a = "name: demo  \r\nbody\r\n"
    b = "name: demo\nbody\n"
    assert content_fingerprint(a) == content_fingerprint(b)
