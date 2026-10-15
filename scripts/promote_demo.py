"""Verify a completed dev build before an explicitly authorized demo promotion."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.build_bundle import check_sha, verify_bundle
from scripts.ci_runs import find_build


def command(repo: Path, arguments: list[str]) -> str:
    """Run an exact command in the repository and surface any failure."""
    environment = {**os.environ, "GIT_CONFIG_COUNT": "1",
                   "GIT_CONFIG_KEY_0": "merge.ff", "GIT_CONFIG_VALUE_0": "only"}
    result = subprocess.run(
        arguments, cwd=repo, env=environment, check=True, text=True, capture_output=True,
    )
    return result.stdout.strip()


def check_checkout(repo: Path) -> str:
    """Require clean dev and aligned branches before a fast-forward promotion."""
    if command(repo, ["git", "branch", "--show-current"]) != "dev":
        raise ValueError("Run promotion from the dev checkout")
    if command(repo, ["git", "status", "--porcelain"]):
        raise ValueError("Commit and push local changes before promotion")
    command(repo, ["git", "fetch", "origin", "dev", "demo"])
    sha = check_sha(command(repo, ["git", "rev-parse", "dev"]))
    if sha != command(repo, ["git", "rev-parse", "origin/dev"]):
        raise ValueError("Local dev must match origin/dev")
    if command(repo, ["git", "rev-parse", "demo"]) != command(
        repo, ["git", "rev-parse", "origin/demo"]
    ):
        raise ValueError("Local demo must match origin/demo")
    command(repo, ["git", "merge-base", "--is-ancestor", "demo", "dev"])
    return sha


def verified_download(repo: Path, sha: str) -> Path:
    """Download and validate the trusted exact-commit compressed dev build."""
    repository = command(repo, ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    run_id = find_build(repository, sha)
    if run_id is None:
        raise ValueError("No completed successful dev build; wait for Verified build CI")
    directory = repo / "build"
    directory.mkdir(exist_ok=True)
    download = Path(tempfile.mkdtemp(prefix=f"promotion-{run_id}-", dir=directory))
    command(repo, [
        "gh", "run", "download", str(run_id), "--repo", repository,
        "--name", f"booster-build-{sha}", "--dir", str(download),
    ])
    bundle = download / f"booster-{sha}.zip"
    verify_bundle(bundle, sha)
    return bundle


def promote(repo: Path, authorized: bool) -> Path:
    """Verify first, then use the shared merge helper and immediately push demo."""
    sha = check_checkout(repo)
    bundle = verified_download(repo, sha)
    if not authorized:
        print(f"Verified {sha}; preview only. Use --authorized for a requested promotion.")
        return bundle
    if check_checkout(repo) != sha:
        raise ValueError("Dev changed during verification; verify the new build first")
    helper = Path.home() / ".agents" / "manage_agents.py"
    if not helper.is_file():
        raise ValueError("Shared merge helper is unavailable; no branches changed")
    command(repo, [
        sys.executable, str(helper), "merge", "--repo", str(repo),
        "--source", "dev", "--target", "demo", "--authorized",
    ])
    command(repo, ["git", "push", "origin", "demo"])
    remote = command(repo, ["git", "ls-remote", "origin", "refs/heads/demo"])
    if remote.split()[0] != sha:
        raise RuntimeError("Remote demo does not match the verified commit")
    print(f"Promoted verified commit {sha} to demo; compressed build: {bundle}")
    return bundle


def main() -> None:
    """Preview promotion unless this invocation explicitly authorizes it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    promote(repo, args.authorized)


if __name__ == "__main__":
    main()
