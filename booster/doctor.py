"""Report the installed engine, its optional extras and the pinned source.

The report exists because a pinned git dependency is easy to believe and hard
to prove: `pip` keeps an installed distribution whose name and version match,
so a server can run older engine code than the commit it claims to pin. This
module reads the installed distribution metadata and reports what is really
there.
"""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

OPTIONAL_MODULES = {
    "fastapi": "server",
    "starlette": "server",
    "uvicorn": "server",
    "httpx": "server/cdn",
    "brotli": "brotli",
}


def _distribution_metadata() -> Path:
    """Locate the installed distribution metadata of the engine."""
    import booster

    location = Path(booster.__file__).resolve().parent
    for candidate in location.parent.glob("booster-*.dist-info"):
        return candidate
    for candidate in Path(sys.prefix).glob("lib/python*/site-packages/booster-*.dist-info"):
        return candidate
    return location


def pinned_source() -> Dict[str, Any]:
    """Read the direct URL the installed distribution came from."""
    metadata = _distribution_metadata()
    direct = metadata / "direct_url.json"
    if not direct.exists():
        return {"installed_from": "local or wheel", "requested_revision": "", "commit": ""}
    try:
        data = json.loads(direct.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"installed_from": "unknown", "requested_revision": "", "commit": ""}
    url = data.get("url", "")
    return {
        "installed_from": url,
        "requested_revision": data.get("vcs_info", {}).get("requested_revision", ""),
        "commit": data.get("vcs_info", {}).get("commit_id", ""),
    }


def optional_extras() -> Dict[str, List[str]]:
    """Report which optional modules are importable."""
    missing: Dict[str, List[str]] = {}
    for module, extra in OPTIONAL_MODULES.items():
        if importlib.util.find_spec(module) is None:
            missing.setdefault(extra, []).append(module)
    return missing


def report() -> Dict[str, Any]:
    """Collect the installation report."""
    import booster

    return {
        "python": sys.version.split()[0],
        "version": booster.__version__,
        "module_path": str(Path(booster.__file__).resolve()),
        "source": pinned_source(),
        "missing_extras": optional_extras(),
        "commands": {"booster": _command_path("booster")},
    }


def _command_path(name: str) -> str:
    """Return the resolved path of an installed console script."""
    import shutil

    return shutil.which(name) or ""


def format_report(report: Dict[str, Any]) -> str:
    """Render the installation report as a short text block."""
    source = report["source"]
    lines = [
        f"python         {report['python']}",
        f"booster        {report['version']}",
        f"module         {report['module_path']}",
        f"installed from {source['installed_from']}",
        f"pinned commit  {source['commit'] or 'not pinned'} (requested {source['requested_revision'] or '-'})",
        f"command        {report['commands']['booster'] or 'not on PATH'}",
    ]
    if report["missing_extras"]:
        for extra, modules in sorted(report["missing_extras"].items()):
            lines.append(f"missing extra  {extra}: {', '.join(sorted(modules))}")
    else:
        lines.append("extras         all present")
    return "\n".join(lines)
