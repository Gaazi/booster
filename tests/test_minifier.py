"""Unit tests for FastMinifier."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

from go_fast.minifier import FastMinifier, minify_css, minify_html, minify_json


def test_minify_html() -> None:
    """Verify minify html."""
    raw = "<div>   <!-- comment -->   <p>Hello   World</p>   </div>"
    result = minify_html(raw)
    assert result == raw


def test_minify_css() -> None:
    """Verify minify css."""
    raw = """
    /* Main style */
    body {
        margin: 0px ;
        color: #ffffff ;
    }
    """
    result = minify_css(raw)
    assert result == raw


def test_minify_json() -> None:
    """Verify minify json."""
    raw = '{\n  "title": "fast",\n  "active": true\n}'
    result = minify_json(raw)
    assert result == '{"title":"fast","active":true}'


def test_fast_minifier_dispatch() -> None:
    """Verify fast minifier dispatch."""
    minifier = FastMinifier()
    html_bytes = b"<div>   <span>test</span>   </div>"
    res = minifier.minify(html_bytes, "text/html")
    assert res == html_bytes
