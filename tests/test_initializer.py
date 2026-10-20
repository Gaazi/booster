"""Verify the host-project adapter scaffolding command."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from booster.initializer import (ADAPTER_NAME, CONFIG_NAME, DEFAULT_EXCLUDE, DEFAULT_INCLUDE,
                                 render_adapter, write_adapter, write_config)


def test_rendered_adapter_uses_the_requested_policy() -> None:
    """The generated module must contain the requested route prefixes."""
    source = render_adapter(("/static/css/",), ("/media/",))
    assert 'CACHEABLE_PREFIXES = ("/static/css/",)' in source
    assert 'EXCLUDED_PREFIXES = ("/media/",)' in source
    assert "enable_compression" in source


def load_generated(path: Path) -> dict:
    """Execute a generated adapter and return its namespace."""
    namespace: dict = {"__file__": str(path), "__name__": "booster_plugin"}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


def test_written_adapter_is_valid_python() -> None:
    """The generated file must import and expose the attach helper."""
    target = write_adapter(Path("/tmp/booster-init-check"), ("/static/",), DEFAULT_EXCLUDE, force=True)
    try:
        compile(target.read_text(encoding="utf-8"), str(target), "exec")
        namespace = load_generated(target)
        assert callable(namespace["attach_booster"])
        policy = namespace["build_cache_policy"]()
        assert policy.include_paths == ("/static/",)
        assert policy.exclude_paths == DEFAULT_EXCLUDE
    finally:
        target.unlink()


def test_existing_adapter_is_not_overwritten(tmp_path: Path) -> None:
    """A second run must protect existing work."""
    target = write_adapter(tmp_path, DEFAULT_INCLUDE, DEFAULT_EXCLUDE)
    target.write_text("# hand written\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_adapter(tmp_path, DEFAULT_INCLUDE, DEFAULT_EXCLUDE)
    assert target.read_text(encoding="utf-8") == "# hand written\n"
    write_adapter(tmp_path, DEFAULT_INCLUDE, DEFAULT_EXCLUDE, force=True)
    assert "attach_booster" in target.read_text(encoding="utf-8")


def test_init_command_creates_the_adapter(tmp_path: Path) -> None:
    """The installed command must scaffold the adapter in the host project."""
    result = subprocess.run(
        [sys.executable, "-m", "booster.cli", "init", "--path", str(tmp_path),
         "--include", "/static/js/"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent, timeout=60)
    assert result.returncode == 0, result.stderr
    created = tmp_path / ADAPTER_NAME
    assert created.exists()
    assert 'CACHEABLE_PREFIXES = ("/static/js/",)' in created.read_text(encoding="utf-8")


def test_init_command_can_write_the_site_configuration(tmp_path: Path) -> None:
    """The configuration file must match the requested route policy."""
    result = subprocess.run(
        [sys.executable, "-m", "booster.cli", "init", "--path", str(tmp_path),
         "--include", "/static/js/", "--exclude", "/media/", "--config"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent, timeout=60)
    assert result.returncode == 0, result.stderr
    document = json.loads((tmp_path / CONFIG_NAME).read_text(encoding="utf-8"))
    assert document["include_paths"] == ["/static/js/"]
    assert document["exclude_paths"] == ["/media/"]


def test_generated_adapter_reads_the_site_configuration(tmp_path: Path) -> None:
    """The generated adapter must use the configuration when it exists."""
    write_config(tmp_path, ("/static/css/",), ("/media/",))
    target = write_adapter(tmp_path, DEFAULT_INCLUDE, DEFAULT_EXCLUDE)
    namespace = load_generated(target)
    policy = namespace["build_cache_policy"]()
    assert policy.include_paths == ("/static/css/",)
    assert policy.exclude_paths == ("/media/",)
