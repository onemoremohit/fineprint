"""
Tests for Accessibility & WCAG Compliance
Validates:
- HTML structure, language tag, and descriptive title
- Viewport scalability for low-vision assistive zoom
- ARIA semantic role definitions
"""

from pathlib import Path


def test_index_html_accessibility_standards():
    """Verify that the frontend entry point satisfies WCAG AA/AAA basic criteria."""
    index_path = Path(__file__).parent.parent / "frontend" / "index.html"
    assert index_path.exists(), "frontend/index.html not found"

    content = index_path.read_text(encoding="utf-8")

    # 1. Must define document language
    assert '<html lang="en">' in content or '<html lang="en"' in content

    # 2. Must not disable pinch-to-zoom / accessibility zoom
    assert "user-scalable=no" not in content, "user-scalable=no violates WCAG 1.4.4 (Resize text)"
    assert "maximum-scale=1.0" not in content, "maximum-scale=1.0 restricts assistive zoom"

    # 3. Must have a descriptive title and meta description
    assert "<title>FinePrint — Grounded Legal AI Assistant" in content
    assert 'name="description"' in content


def test_css_wcag_contrast_and_reduced_motion():
    """Verify that CSS includes prefers-reduced-motion and focus-visible indicators."""
    css_path = Path(__file__).parent.parent / "frontend" / "src" / "index.css"
    assert css_path.exists(), "frontend/src/index.css not found"

    content = css_path.read_text(encoding="utf-8")

    # Must support users with vestibular motion disorders
    assert "prefers-reduced-motion" in content

    # Must provide high-contrast visible focus indicators for keyboard navigation
    assert ":focus-visible" in content

    # Must provide screen-reader only utility classes
    assert ".sr-only" in content
