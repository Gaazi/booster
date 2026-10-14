"""Conservative text optimization preserving HTML/CSS semantics and JSON values."""

import json
import re

JSON_TOKENS = re.compile(r'"(?:\\.|[^"\\])*"|\s+', re.S)


def minify_html(content: str) -> str:
    """Preserve HTML verbatim; regex rewriting can change markup and text meaning."""
    return content


def minify_css(content: str) -> str:
    """Preserve CSS verbatim; selectors and custom properties depend on whitespace."""
    return content


def minify_json(content: str) -> str:
    """Remove JSON whitespace without rounding numbers or rewriting string values."""
    try:
        json.loads(content)
    except (ValueError, TypeError, RecursionError):
        return content
    return JSON_TOKENS.sub(lambda match: match.group() if match.group().startswith('"') else "", content)


class FastMinifier:
    """Optimize UTF-8 JSON while preserving all other content byte for byte."""

    @staticmethod
    def minify(content: bytes, content_type: str) -> bytes:
        """Remove only insignificant JSON whitespace from explicitly UTF-8 content."""
        base_type = content_type.split(";")[0].strip().lower()
        if base_type not in {"application/json", "application/ld+json"}:
            return content
        parameters = content_type.lower().replace(" ", "")
        if "charset=" in parameters and "charset=utf-8" not in parameters:
            return content
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return content
        return minify_json(text).encode("utf-8")
