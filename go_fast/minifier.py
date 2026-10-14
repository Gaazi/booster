"""Fast on-the-fly minification engine for HTML, CSS, JavaScript, and JSON."""

import json
import re
from typing import Optional

RE_PROTECTED_HTML = re.compile(r"<(pre|textarea|script|style)\b[^>]*>.*?</\1\s*>", re.I | re.S)
RE_CSS_STRINGS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)

RE_HTML_COMMENTS = re.compile(r"<!--(?!\[if).*?-->", re.DOTALL)
RE_HTML_SPACES = re.compile(r">\s+<")
RE_CSS_COMMENTS = re.compile(r"/\*.*?\*/", re.DOTALL)
RE_CSS_SPACES = re.compile(r"\s*([\{\}:;,>])\s*")


def minify_html(content: str) -> str:
    """Safely collapse redundant whitespace and strip comments from HTML."""
    protected = []
    def protect(match: re.Match) -> str:
        """Keep whitespace-sensitive HTML verbatim."""
        protected.append(match.group())
        return f"<go-fast-protected-{len(protected) - 1}>"
    content = RE_PROTECTED_HTML.sub(protect, content)
    no_comments = RE_HTML_COMMENTS.sub("", content)
    collapsed = RE_HTML_SPACES.sub("><", no_comments)
    for index, value in enumerate(protected):
        collapsed = collapsed.replace(f"<go-fast-protected-{index}>", value)
    return collapsed.strip()


def minify_css(content: str) -> str:
    """Minify CSS by stripping comments and unneeded spacing."""
    protected = []
    def protect(match: re.Match) -> str:
        """Keep quoted CSS values verbatim."""
        protected.append(match.group())
        return f"GOFASTSTRING{len(protected) - 1}TOKEN"
    content = RE_CSS_STRINGS.sub(protect, content)
    no_comments = RE_CSS_COMMENTS.sub("", content)
    compacted = RE_CSS_SPACES.sub(r"\1", no_comments)
    for index, value in enumerate(protected):
        compacted = compacted.replace(f"GOFASTSTRING{index}TOKEN", value)
    return compacted.strip()


def minify_json(content: str) -> str:
    """Serialize JSON without extraneous whitespace."""
    try:
        parsed = json.loads(content)
        return json.dumps(parsed, separators=(",", ":"))
    except (ValueError, TypeError):
        return content


class FastMinifier:
    """Dispatches payload to type-specific minifier."""

    @staticmethod
    def minify(content: bytes, content_type: str) -> bytes:
        """Minify text content based on its content-type."""
        base_type = content_type.split(";")[0].strip().lower()
        if base_type not in {"text/html", "text/css", "application/json", "application/ld+json"}:
            return content
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return content

        if base_type == "text/html":
            return minify_html(text).encode("utf-8")
        if base_type == "text/css":
            return minify_css(text).encode("utf-8")
        if base_type in ("application/json", "application/ld+json"):
            return minify_json(text).encode("utf-8")

        return content
