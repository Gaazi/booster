"""Unit tests for FastMinifier."""

from go_fast.minifier import FastMinifier, minify_css, minify_html, minify_json


def test_minify_html() -> None:
    raw = "<div>   <!-- comment -->   <p>Hello   World</p>   </div>"
    result = minify_html(raw)
    assert "<!-- comment -->" not in result
    assert "><p>" in result


def test_minify_css() -> None:
    raw = """
    /* Main style */
    body {
        margin: 0px ;
        color: #ffffff ;
    }
    """
    result = minify_css(raw)
    assert "/* Main style */" not in result
    assert "margin:0px" in result
    assert "color:#ffffff" in result


def test_minify_json() -> None:
    raw = '{\n  "title": "fast",\n  "active": true\n}'
    result = minify_json(raw)
    assert result == '{"title":"fast","active":true}'


def test_fast_minifier_dispatch() -> None:
    minifier = FastMinifier()
    html_bytes = b"<div>   <span>test</span>   </div>"
    res = minifier.minify(html_bytes, "text/html")
    assert res == b"<div><span>test</span></div>"
