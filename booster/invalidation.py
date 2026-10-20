"""Exchange cache invalidation notices between worker processes.

The engine keeps its cache inside each worker. Without coordination a write
that reaches one worker leaves the other workers serving a stale copy until
their entry expires. An invalidation bus closes that window: the worker that
handled the write publishes a notice, and every other worker applies it before
it serves the next request.
"""

from pathlib import Path
from typing import List, Protocol

FULL_CLEAR = "*"


class InvalidationBus(Protocol):
    """Publish and observe invalidation notices."""

    def publish(self, prefix: str) -> None:
        """Publish one notice for the other workers."""

    def drain(self) -> List[str]:
        """Return the notices published since the last drain."""


class LocalInvalidationBus:
    """Keep invalidation inside the current process."""

    def publish(self, prefix: str) -> None:
        """Ignore the notice because no other worker exists."""

    def drain(self) -> List[str]:
        """Return no notices."""


class FileInvalidationBus:
    """Exchange notices through one shared file, for workers on the same host.

    Every worker keeps its own read position, so one worker never consumes
    another worker's notice. The file is truncated when it grows past the size
    limit; a reader that notices the truncation applies a full clear, because
    that is the only safe interpretation of a lost notice.
    """

    def __init__(self, path: Path, max_bytes: int = 1_000_000) -> None:
        """Open the shared notice file for reading and later appending."""
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._reader = self.path.open("r", encoding="utf-8")

    def publish(self, prefix: str) -> None:
        """Append one notice for the other workers."""
        with self.path.open("a", encoding="utf-8") as writer:
            writer.write(prefix + "\n")
        self._truncate_if_large()

    def drain(self) -> List[str]:
        """Read the notices written since the last drain."""
        if self._reader.tell() > self.path.stat().st_size:
            self._reader.seek(0)
            return [FULL_CLEAR]
        return [line.strip() for line in self._reader.read().splitlines() if line.strip()]

    def _truncate_if_large(self) -> None:
        """Truncate the notice file so it cannot grow without bound."""
        if self.path.stat().st_size > self.max_bytes:
            self.path.write_text("", encoding="utf-8")
