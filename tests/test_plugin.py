"""One-click setup regressions for nested folders, reuse and failed installations."""

from __future__ import annotations
from typing import Any, Callable, AsyncIterator, Iterator

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
import setup_plugin


def plugin_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    """Make a nested plugin directory containing spaces and an existing interpreter."""
    root = tmp_path / "Main Project" / "booster"
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nname="booster"')
    environment = root / ".venv"
    monkeypatch.setattr(setup_plugin, "ROOT", root)
    monkeypatch.setattr(setup_plugin, "ENVIRONMENT", environment)
    monkeypatch.setattr(setup_plugin, "STAMP", root / ".booster-setup.json")
    interpreter = setup_plugin.environment_python()
    interpreter.parent.mkdir(parents=True)
    interpreter.touch()
    return root, interpreter


def test_setup_installs_once_and_reuses_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Repeated clicks reuse dependencies and changed requirements trigger setup."""
    root, interpreter = plugin_folder(monkeypatch, tmp_path)
    runner = Mock()
    monkeypatch.setattr(setup_plugin, "run_checked", runner)
    assert setup_plugin.setup_environment() == interpreter
    installs = [call.args[0] for call in runner.call_args_list if "install" in call.args[0]]
    assert len(installs) == 2
    assert installs[-1][-1] == f"{root}[server,brotli]"
    runner.reset_mock()
    setup_plugin.setup_environment()
    assert runner.call_count == 1 and "install" not in runner.call_args.args[0]
    (root / "pyproject.toml").write_text('[project]\nname="changed"')
    setup_plugin.setup_environment()
    assert any("install" in call.args[0] for call in runner.call_args_list)


def test_failed_installation_does_not_mark_setup_complete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A failed pip command remains visible and can be retried on the next click."""
    root, interpreter = plugin_folder(monkeypatch, tmp_path)
    monkeypatch.setattr(setup_plugin, "run_checked", Mock(side_effect=subprocess.CalledProcessError(1, "pip")))
    with pytest.raises(subprocess.CalledProcessError):
        setup_plugin.setup_environment()
    assert not setup_plugin.STAMP.exists()


def test_launch_preserves_target_as_one_literal_argument(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """URLs cannot become shell commands, including under a folder containing spaces."""
    root, interpreter = plugin_folder(monkeypatch, tmp_path)
    monkeypatch.setattr(setup_plugin, "setup_environment", lambda: interpreter)
    monkeypatch.setattr(setup_plugin.sys, "argv", ["setup_plugin.py", "--target", "http://localhost:8000/path;echo", "--no-browser"])
    runner = Mock()
    monkeypatch.setattr(setup_plugin, "run_checked", runner)
    assert setup_plugin.main() == 0
    assert runner.call_args.args[0] == [str(interpreter), str(root / "run.py"),
                    "--target", "http://localhost:8000/path;echo", "--no-browser"]


def test_run_checked_uses_no_shell_and_plugin_working_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Setup and startup retain checked exit codes and an exact argument vector."""
    root, interpreter = plugin_folder(monkeypatch, tmp_path)
    runner = Mock()
    monkeypatch.setattr(setup_plugin.subprocess, "run", runner)
    setup_plugin.run_checked([str(interpreter), "-m", "pip", "check"])
    assert runner.call_args.kwargs == {"cwd": root, "check": True}
