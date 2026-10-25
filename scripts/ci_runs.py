"""Find only successful same-repository dev builds for an exact commit."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from scripts.build_bundle import check_sha

WORKFLOW_PATH = ".github/workflows/build.yml"


def api(repository: str, endpoint: str) -> dict[str, Any]:
    """Read repository metadata with the authenticated GitHub CLI."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository identity")
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/{endpoint}"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def matching_run(run: dict[str, Any], repository: str, sha: str) -> bool:
    """Reject failed, PR, fork, other-branch and different-commit builds."""
    return (
        run.get("head_sha") == check_sha(sha)
        and run.get("head_branch") == "dev"
        and run.get("event") == "push"
        and run.get("path") == WORKFLOW_PATH
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and (run.get("repository") or {}).get("full_name") == repository
        and (run.get("head_repository") or {}).get("full_name") == repository
    )


def find_build(repository: str, sha: str) -> int | None:
    """Return a successful dev run with an available exact-commit artifact."""
    check_sha(sha)
    endpoint = f"actions/runs?branch=dev&event=push&head_sha={sha}&per_page=20"
    for run in api(repository, endpoint).get("workflow_runs", []):
        if not matching_run(run, repository, sha):
            continue
        run_id = int(run["id"])
        artifacts = api(repository, f"actions/runs/{run_id}/artifacts?per_page=100")
        if any(
            artifact.get("name") == f"booster-build-{sha}"
            and artifact.get("expired") is False
            for artifact in artifacts.get("artifacts", [])
        ):
            return run_id
    return None


def main() -> None:
    """Reuse dev artifacts only for a demo push of the identical commit."""
    run_id = None
    if os.environ.get("CI_EVENT") == "push" and os.environ.get("CI_BRANCH") == "demo":
        run_id = find_build(os.environ["CI_REPOSITORY"], os.environ["CI_SHA"])
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
        output.write(f"run_id={run_id or ''}\n")
    print(f"Reuse verified dev run {run_id}" if run_id else "Build and test this commit")


if __name__ == "__main__":
    main()
