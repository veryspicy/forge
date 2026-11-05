"""富文本净化单元测试（写入侧 XSS 防护）。"""

from __future__ import annotations

import pytest

from forge.application.services.richtext import sanitize_html


def test_empty_input_returns_empty_string() -> None:
    assert sanitize_html(None) == ""
    assert sanitize_html("") == ""


def test_keeps_whitelisted_structure() -> None:
    html = "<h2>标题</h2><p>正文 <strong>加粗</strong></p><ul><li>项</li></ul>"
    assert sanitize_html(html) == html


def test_strips_script_and_its_content() -> None:
    html = '<p onclick="alert(1)">hi<script>alert(1)</script></p>'
    assert sanitize_html(html) == "<p>hi</p>"


def test_drops_javascript_scheme_in_links() -> None:
    assert sanitize_html('<a href="javascript:alert(1)">x</a>') == (
        '<a rel="noopener noreferrer">x</a>'
    )


def test_drops_obfuscated_scheme_with_control_chars() -> None:
    html = '<a href="java\tscript:alert(1)">x</a>'
    assert "javascript" not in sanitize_html(html)


def test_external_link_gets_target_and_rel() -> None:
    html = '<a href="https://example.com" target="_blank">ok</a>'
    assert sanitize_html(html) == (
        '<a href="https://example.com" target="_blank" rel="noopener noreferrer">ok</a>'
    )


def test_relative_link_is_kept() -> None:
    assert 'href="/contact"' in sanitize_html('<a href="/contact">c</a>')


@pytest.mark.parametrize("scheme", ["mailto:a@b.com", "tel:+8613800000000"])
def test_contact_schemes_allowed(scheme: str) -> None:
    assert f'href="{scheme}"' in sanitize_html(f'<a href="{scheme}">c</a>')


def test_strips_event_handlers_on_images() -> None:
    assert sanitize_html('<img src="/a.png" onerror="alert(1)">') == '<img src="/a.png">'


def test_style_limited_to_text_align() -> None:
    html = '<p style="text-align: center; background: url(javascript:1)">c</p>'
    assert sanitize_html(html) == '<p style="text-align: center">c</p>'


def test_video_keeps_safe_attributes() -> None:
    html = '<video src="/v.mp4" controls poster="/p.jpg" onload="x"></video>'
    assert sanitize_html(html) == '<video src="/v.mp4" controls poster="/p.jpg"></video>'


def test_drops_style_tag_and_comments() -> None:
    html = "<style>body{display:none}</style><!--[if IE]><script>x</script><![endif]--><h2>t</h2>"
    assert sanitize_html(html) == "<h2>t</h2>"


def test_unclosed_tags_are_balanced() -> None:
    assert sanitize_html("<p>a<div>b") == "<p>a<div>b</div></p>"


def test_keeps_multilingual_text() -> None:
    html = "<h2>隐私政策 Privacy</h2><p>مرحبا 你好</p>"
    assert sanitize_html(html) == html
