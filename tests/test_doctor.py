"""Verify the installation report."""

import json
import subprocess
import sys
from pathlib import Path

from booster.doctor import format_report, optional_extras, pinned_source, report


def test_report_names_the_engine_and_the_extras() -> None:
    """The report must state the version, the module path and the missing extras."""
    result = report()
    assert result["version"]
    assert result["module_path"].endswith("__init__.py")
    assert isinstance(result["missing_extras"], dict)
    assert "python" in result


def test_report_lists_the_console_script() -> None:
    """The report must locate the installed command."""
    result = report()
    assert "booster" in result["commands"]


def test_pinned_source_is_readable() -> None:
    """The pinned source must be reported without raising."""
    source = pinned_source()
    assert set(source) == {"installed_from", "requested_revision", "commit"}


def test_missing_extras_are_grouped() -> None:
    """Missing optional modules must be grouped by their extra."""
    missing = optional_extras()
    for extra, modules in missing.items():
        assert extra in {"server", "cdn", "brotli"}
        assert modules


def test_formatted_report_mentions_the_pinned_commit() -> None:
    """The text report must show the pinned commit line."""
    text = format_report(report())
    assert "pinned commit" in text
    assert "booster" in text


def test_doctor_command_runs() -> None:
    """The installed command must print the report."""
    result = subprocess.run([sys.executable, "-m", "booster.cli", "doctor", "--json"],
                            capture_output=True, text=True, timeout=60,
                            cwd=Path(__file__).resolve().parent.parent)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"]
    assert "source" in payload
