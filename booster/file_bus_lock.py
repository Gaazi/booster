"""Serialize Python and Node notice-file access with one bounded local lock."""

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def file_bus_lock(path: Path) -> Iterator[None]:
    """Fail closed if a peer cannot release its lock within five seconds."""
    deadline = time.monotonic() + 5
    while True:
        try:
            path.mkdir()
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Invalidation lock is busy: {path}")
            time.sleep(0.005)
    try:
        yield
    finally:
        path.rmdir()
