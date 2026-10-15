"""Launch the optional standalone server with a clear installation hint."""


def main() -> None:
    """Delegate to the server without loading its dependencies on core import."""
    try:
        from booster.server import main as run_server
    except ModuleNotFoundError as error:
        if error.name in {"uvicorn", "fastapi", "starlette", "httpx"}:
            raise SystemExit("Standalone mode requires: pip install 'booster[server]'") from error
        raise
    run_server()


if __name__ == "__main__":
    main()
