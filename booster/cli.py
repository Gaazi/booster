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


def main() -> None:
    """Delegate to the server without loading its dependencies on core import."""
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
