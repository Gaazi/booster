"""Exercise compressed build integrity and fail-closed promotion checks."""

import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from scripts import build_bundle, ci_runs, promote_demo

SHA = "a" * 40
NAMES = ["booster-1.0-py3-none-any.whl", "booster-1.0.tar.gz", "booster-node-1.0.tgz"]


@pytest.fixture
def packages(tmp_path: Path) -> Path:
    """Provide three independent dummy distributions without installed tools."""
    directory = tmp_path / "packages"
    directory.mkdir()
    for name in NAMES:
        (directory / name).write_bytes(name.encode())
    return directory


def test_bundle_round_trip(packages: Path, tmp_path: Path) -> None:
    """A valid compressed download preserves each distribution byte-for-byte."""
    bundle = build_bundle.create_bundle(packages, SHA)
    destination = tmp_path / "verified"
    build_bundle.verify_bundle(bundle, SHA, destination)
    assert {path.name for path in destination.iterdir()} == set(NAMES)
    for name in NAMES:
        assert (destination / name).read_bytes() == (packages / name).read_bytes()


def test_bundle_rejects_other_commit(packages: Path) -> None:
    """A valid build must not be promoted as a different revision."""
    bundle = build_bundle.create_bundle(packages, SHA)
    with pytest.raises(ValueError, match="commit"):
        build_bundle.verify_bundle(bundle, "b" * 40)


@pytest.mark.parametrize("sha", ["dev", "../demo", "a" * 39, "A" * 40])
def test_bundle_rejects_non_commit_identity(packages: Path, sha: str) -> None:
    """Branch names and partial hashes cannot identify verified builds."""
    with pytest.raises(ValueError, match="SHA"):
        build_bundle.create_bundle(packages, sha)


@pytest.mark.parametrize("extra", ["unexpected.txt", "booster-extra.whl"])
def test_bundle_rejects_extra_distributions(packages: Path, extra: str) -> None:
    """Unreviewed extra files cannot enter the compressed download."""
    (packages / extra).write_bytes(b"extra")
    with pytest.raises(ValueError):
        build_bundle.create_bundle(packages, SHA)


@pytest.mark.parametrize("bad_name", ["../booster-1.whl", "folder/booster-1.whl", "booster-1.whl\\evil"])
def test_rejects_unsafe_archive_names(bad_name: str) -> None:
    """Archive paths cannot escape the extraction directory."""
    with pytest.raises(ValueError, match="Unsafe"):
        build_bundle.package_kind(bad_name)


def test_corrupt_package_is_rejected_before_extraction(tmp_path: Path) -> None:
    """Checksum failure prevents every package from being written."""
    bundle = tmp_path / "corrupt.zip"
    manifest = {"schema": 1, "commit": SHA, "sha256": {
        name: hashlib.sha256(b"original").hexdigest() for name in NAMES
    }}
    with ZipFile(bundle, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name in NAMES:
            archive.writestr(name, b"changed")
    destination = tmp_path / "verified"
    with pytest.raises(ValueError, match="checksum"):
        build_bundle.verify_bundle(bundle, SHA, destination)
    assert not destination.exists()


def trusted_run() -> dict[str, object]:
    """Represent a successful same-repository push build on dev."""
    return {"id": 123, "head_sha": SHA, "head_branch": "dev", "event": "push",
            "status": "completed", "conclusion": "success",
            "path": ".github/workflows/build.yml",
            "repository": {"full_name": "owner/booster"},
            "head_repository": {"full_name": "owner/booster"}}


@pytest.mark.parametrize("field,value", [
    ("head_sha", "b" * 40), ("head_branch", "demo"), ("event", "pull_request"),
    ("status", "in_progress"), ("conclusion", "failure"),
    ("path", ".github/workflows/untrusted.yml"),
    ("head_repository", {"full_name": "fork/booster"}),
])
def test_reuse_rejects_untrusted_run(field: str, value: object) -> None:
    """Reuse must never accept PRs, forks, failures or other revisions."""
    run = trusted_run()
    run[field] = value
    assert not ci_runs.matching_run(run, "owner/booster", SHA)


@pytest.mark.parametrize("expired,expected", [(False, 123), (True, None)])
def test_reuse_requires_available_artifact(expired: bool, expected: int | None) -> None:
    """Expired builds require a fresh test/build rather than stale promotion."""
    artifact = {"name": f"booster-build-{SHA}", "expired": expired}
    with patch.object(ci_runs, "api", side_effect=[
        {"workflow_runs": [trusted_run()]}, {"artifacts": [artifact]},
    ]):
        assert ci_runs.find_build("owner/booster", SHA) == expected


def test_no_successful_build_cannot_promote(tmp_path: Path) -> None:
    """Promotion stops before downloads or merges when CI is not successful."""
    with patch.object(promote_demo, "command", return_value="owner/booster") as command:
        with patch.object(promote_demo, "find_build", return_value=None):
            with pytest.raises(ValueError, match="successful"):
                promote_demo.verified_download(tmp_path, SHA)
    assert command.call_count == 1


def test_preview_does_not_merge_or_push(tmp_path: Path) -> None:
    """A normal invocation prepares the verified download without promotion."""
    with patch.object(promote_demo, "check_checkout", return_value=SHA):
        with patch.object(promote_demo, "verified_download", return_value=tmp_path / "build.zip"):
            with patch.object(promote_demo, "command") as command:
                promote_demo.promote(tmp_path, authorized=False)
    command.assert_not_called()


@pytest.mark.parametrize("branch,dirty", [("main", ""), ("dev", " M README.md")])
def test_promotion_preserves_wrong_branch_or_dirty_work(tmp_path: Path, branch: str, dirty: str) -> None:
    """Unsafe checkout conditions stop before fetching or modifying branches."""
    responses = [branch, dirty] if branch == "dev" else [branch]
    with patch.object(promote_demo, "command", side_effect=responses) as command:
        with pytest.raises(ValueError):
            promote_demo.check_checkout(tmp_path)
    assert command.call_count == len(responses)


def test_authorized_promotion_pushes_immediately_after_merge(tmp_path: Path) -> None:
    """The shared merge helper is followed directly by a non-force demo push."""
    helper = tmp_path / ".agents" / "manage_agents.py"
    helper.parent.mkdir()
    helper.write_text("", encoding="utf-8")
    with patch.object(promote_demo.Path, "home", return_value=tmp_path):
        with patch.object(promote_demo, "check_checkout", return_value=SHA):
            with patch.object(promote_demo, "verified_download", return_value=tmp_path / "build.zip"):
                with patch.object(promote_demo, "prepare_demo"):
                    results = ["", "", f"{SHA}\trefs/heads/demo", SHA, "", ""]
                    with patch.object(promote_demo, "command", side_effect=results) as command:
                        promote_demo.promote(tmp_path, authorized=True, authorization_note="merge dev to demo")
    calls = [call.args[1] for call in command.call_args_list]
    assert calls[0][2] == "merge"
    assert calls[1] == ["git", "push", "origin", "demo"]
    assert calls[0][-2:] == ["--authorization-note", "merge dev to demo"]


def test_changed_dev_cannot_promote_previous_build(tmp_path: Path) -> None:
    """A concurrent dev update cannot reuse a different commit's verification."""
    with patch.object(promote_demo, "check_checkout", side_effect=[SHA, "b" * 40]):
        with patch.object(promote_demo, "verified_download", return_value=tmp_path / "build.zip"):
            with patch.object(promote_demo, "command") as command:
                with pytest.raises(ValueError, match="changed"):
                    promote_demo.promote(tmp_path, authorized=True, authorization_note="merge dev to demo")
    command.assert_not_called()


def test_duplicate_archive_members_are_rejected(tmp_path: Path) -> None:
    """Ambiguous ZIP members cannot be accepted as a verified package set."""
    bundle = tmp_path / "duplicate.zip"
    with ZipFile(bundle, "w") as archive:
        archive.writestr("manifest.json", "{}")
        with pytest.warns(UserWarning, match="Duplicate"):
            archive.writestr("manifest.json", "{}")
    with pytest.raises(ValueError, match="duplicate"):
        build_bundle.verify_bundle(bundle, SHA)


def test_outdated_local_dev_cannot_promote(tmp_path: Path) -> None:
    """Local branch drift stops promotion instead of dropping unseen work."""
    responses = ["dev", "", "", SHA, "b" * 40]
    with patch.object(promote_demo, "command", side_effect=responses):
        with pytest.raises(ValueError, match="match origin"):
            promote_demo.check_checkout(tmp_path)


def test_diverged_demo_cannot_promote(tmp_path: Path) -> None:
    """Divergence requires reconciliation and testing on dev before promotion."""
    failure = subprocess.CalledProcessError(1, ["git", "merge-base"])
    responses = ["c" * 40, "c" * 40, failure]
    with patch.object(promote_demo, "command", side_effect=responses):
        with pytest.raises(subprocess.CalledProcessError):
            promote_demo.prepare_demo(tmp_path)


def test_outdated_demo_catches_up_without_force(tmp_path: Path) -> None:
    """An older local demo is synchronized automatically only when safe."""
    with patch.object(promote_demo, "command", side_effect=["old", "new", "", "", ""]) as command:
        promote_demo.prepare_demo(tmp_path)
    calls = [call.args[1] for call in command.call_args_list]
    assert calls[2] == ["git", "merge-base", "--is-ancestor", "demo", "origin/demo"]
    assert calls[3] == ["git", "fetch", "origin", "refs/heads/demo:refs/heads/demo"]


def test_unpublished_demo_work_is_preserved(tmp_path: Path) -> None:
    """An unrelated local demo is never reset to the remote branch."""
    failure = subprocess.CalledProcessError(1, ["git", "merge-base"])
    with patch.object(promote_demo, "command", side_effect=["local", "remote", failure]) as command:
        with pytest.raises(subprocess.CalledProcessError):
            promote_demo.prepare_demo(tmp_path)
    assert command.call_count == 3


def test_merge_commands_force_fast_forward_only(tmp_path: Path) -> None:
    """A user merge.ff=false setting cannot create an unverified merge commit."""
    with patch.object(promote_demo.subprocess, "run") as run:
        run.return_value.stdout = "ok"
        assert promote_demo.command(tmp_path, ["git", "status"]) == "ok"
    environment = run.call_args.kwargs["env"]
    assert environment["GIT_CONFIG_KEY_0"] == "merge.ff"
    assert environment["GIT_CONFIG_VALUE_0"] == "only"


def test_reuse_before_workflow_reaches_default_branch() -> None:
    """New dev workflows are discoverable without registering them on main."""
    artifact = {"name": f"booster-build-{SHA}", "expired": False}
    with patch.object(ci_runs, "api", side_effect=[
        {"workflow_runs": [trusted_run()]}, {"artifacts": [artifact]},
    ]) as api:
        assert ci_runs.find_build("owner/booster", SHA) == 123
    assert api.call_args_list[0].args[1].startswith("actions/runs?")
