"""Set up the cloned plugin in its own environment and launch it in one step."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
ENVIRONMENT = ROOT / ".venv"
STAMP = ROOT / ".booster-setup.json"


def environment_python() -> Path:
    """Locate the plugin interpreter independently of the current directory."""
    return ENVIRONMENT / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def run_checked(arguments: list[str]) -> None:
    """Run an exact argument vector and surface installation or startup failures."""
    subprocess.run(arguments, cwd=ROOT, check=True)


def setup_environment() -> Path:
    """Install dependencies only on first use or when project requirements change."""
    interpreter = environment_python()
    if not interpreter.exists():
        print("Preparing the plugin environment...")
        venv.EnvBuilder(with_pip=True).create(ENVIRONMENT)
    signature = hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()
    previous = json.loads(STAMP.read_text()) if STAMP.exists() else {}
    if previous.get("requirements") != signature:
        print("Installing plugin dependencies...")
        run_checked([str(interpreter), "-m", "pip", "install", "--upgrade", "pip>=26.2.1"])
        run_checked([str(interpreter), "-m", "pip", "install", "-e", str(ROOT)])
        STAMP.write_text(json.dumps({"requirements": signature}), encoding="utf-8")
    run_checked([str(interpreter), "-c", "from booster.server import app, gateway"])
    return interpreter


def main() -> int:
    """Prepare the plugin, optionally check setup, and open the local dashboard."""
    parser = argparse.ArgumentParser(description="One-click booster setup and launch")
    parser.add_argument("--check", action="store_true", help="Prepare and verify without launching")
    parser.add_argument("--target", help="Trusted upstream base URL (otherwise auto-detect)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser")
    arguments = parser.parse_args()
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.", file=sys.stderr)
        return 1
    try:
        interpreter = setup_environment()
        if not arguments.check:
            command = [str(interpreter), str(ROOT / "run.py")]
            if arguments.target:
                command += ["--target", arguments.target]
            if arguments.no_browser:
                command.append("--no-browser")
            run_checked(command)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Plugin setup or launch failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
