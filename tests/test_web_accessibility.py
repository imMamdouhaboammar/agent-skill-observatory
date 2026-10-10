"""Regression checks for shipped static dashboard accessibility semantics."""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "src" / "skill_observatory" / "web"


def test_keyboard_skip_link_targets_main_content() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    assert '<a class="skip-link" href="#main-content">Skip to main content</a>' in html
    assert 'id="main-content"' in html
    assert re.search(r"\.skip-link:focus-visible\s*\{[^}]*transform:\s*none", css)
    assert "GitHub repository (opens in a new tab)" in html


def test_dynamic_empty_state_has_live_announcement() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<div[^>]*id="filterAnnouncement"[^>]*role="status"[^>]*aria-live="polite"', html)
    assert 'id="empty"' in html
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert "$('filterAnnouncement').textContent=" in script
    assert "No skills match these filters." in script
    assert ".sr-only" in (WEB / "styles.css").read_text(encoding="utf-8")


def test_external_new_tab_links_announce_behavior_and_are_isolated() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    links = re.findall(r"<a\b[^>]*target=\"_blank\"[^>]*>", html)
    assert links
    for link in links:
        assert re.search(r'aria-label="[^"]*opens in a new tab[^"]*"', link), link
        rel_match = re.search(r'rel="([^"]+)"', link)
        assert rel_match is not None, link
        assert {"noopener", "noreferrer"} <= set(rel_match.group(1).split()), link
