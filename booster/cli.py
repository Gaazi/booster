"""Launch the optional standalone server and scaffold a host-project adapter."""

import argparse
import sys
from pathlib import Path


def run_init(arguments: argparse.Namespace) -> int:
    """Generate a Booster adapter inside the host project."""
    from booster.initializer import (DEFAULT_EXCLUDE, DEFAULT_INCLUDE, write_adapter,
                                     write_config)

    include = tuple(arguments.include or DEFAULT_INCLUDE)
    exclude = tuple(arguments.exclude or DEFAULT_EXCLUDE)
    directory = Path(arguments.path).resolve()
    try:
        target = write_adapter(directory, include, exclude, force=arguments.force)
        written = [target]
        if arguments.config:
            written.append(write_config(directory, include, exclude, force=arguments.force))
    except (OSError, FileExistsError) as error:
        print(f"Booster init failed: {error}", file=sys.stderr)
        return 1
    for path in written:
        print(f"Created {path}")
    print("Next: import attach_booster from it and call it before your other middleware.")
    print("See docs/PLUGIN_RECIPE.md and docs/CONFORMANCE_CHECKLIST.md in the Booster repository.")
    return 0


def run_measure(arguments: argparse.Namespace) -> int:
    """Measure one URL and report whether the engine could store it."""
    import json

    from booster.measurement import format_report, measure_or_error

    report = measure_or_error(arguments.url, arguments.requests, arguments.timeout)
    if report is None:
        print(f"Could not reach {arguments.url}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2) if arguments.json else format_report(report))
    return 0


def run_doctor(arguments: argparse.Namespace) -> int:
    """Report the installed engine, its extras and the pinned source."""
    import json

    from booster.doctor import format_report, report

    result = report()
    print(json.dumps(result, indent=2) if arguments.json else format_report(result))
    return 0


def main() -> None:
    """Delegate to the server without loading its dependencies on core import."""
    if len(sys.argv) > 1 and sys.argv[1] == "doctor":
        parser = argparse.ArgumentParser(prog="booster doctor", description="Report the installation")
        parser.add_argument("--json", action="store_true", help="Print the report as JSON")
        raise SystemExit(run_doctor(parser.parse_args(sys.argv[2:])))
    if len(sys.argv) > 1 and sys.argv[1] == "measure":
        parser = argparse.ArgumentParser(prog="booster measure", description="Measure one URL")
        parser.add_argument("url", help="URL to measure")
        parser.add_argument("--requests", type=int, default=20, help="How many requests to send")
        parser.add_argument("--timeout", type=float, default=15.0, help="Timeout per request in seconds")
        parser.add_argument("--json", action="store_true", help="Print the report as JSON")
        raise SystemExit(run_measure(parser.parse_args(sys.argv[2:])))
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        parser = argparse.ArgumentParser(prog="booster init", description="Create a Booster adapter")
        parser.add_argument("--path", default=".", help="Host project directory")
        parser.add_argument("--include", action="append", help="Public route prefix to cache")
        parser.add_argument("--exclude", action="append", help="Route prefix to keep out")
        parser.add_argument("--force", action="store_true", help="Replace an existing adapter")
        parser.add_argument("--config", action="store_true", help="Also write booster.json")
        raise SystemExit(run_init(parser.parse_args(sys.argv[2:])))
    try:
        from booster.server import main as run_server
    except ModuleNotFoundError as error:
        if error.name in {"uvicorn", "fastapi", "starlette", "httpx"}:
            raise SystemExit("Standalone mode requires: pip install 'booster[server]'") from error
        raise
    run_server()


if __name__ == "__main__":
    main()
