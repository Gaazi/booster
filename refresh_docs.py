"""Generate the source map and browsable HTML with the standard library."""

import ast
import html
from pathlib import Path


def main() -> None:
    """Refresh both documentation artifacts from project source only."""
    lines = ["# Code Map", "", "Generated with `python refresh_docs.py`.", ""]
    edges = set()
    paths = sorted(Path("booster").glob("*.py")) + sorted(Path("scripts").glob("*.py"))
    for path in paths + [Path("run.py"), Path("setup_plugin.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        lines.extend([f"## {path.as_posix()}", ""])
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = (ast.get_docstring(node) or "Internal implementation.").splitlines()[0]
                lines.append(f"- `{node.name}` (line {node.lineno}): {doc}")
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("booster."):
                edges.add(f"  {path.stem} --> {node.module.split('.')[-1]}")

        lines.append("")
    lines.extend(["```mermaid", "graph TD", *sorted(edges), "```", ""])
    text = "\n".join(lines)
    Path("CODEMAP.md").write_text(text, encoding="utf-8")
    Path("docs").mkdir(exist_ok=True)
    Path("docs/index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>booster Code Map</title>'
        + '<pre>' + html.escape(text) + '</pre></html>', encoding="utf-8")


if __name__ == "__main__":
    main()
