"""Exchange cache invalidation notices between worker processes.

The engine keeps its cache inside each worker. Without coordination a write
that reaches one worker leaves the other workers serving a stale copy until
their entry expires. An invalidation bus closes that window: the worker that
handled the write publishes a notice, and every other worker applies it before
it serves the next request.
"""

import json
from pathlib import Path
from typing import List, Protocol
from uuid import uuid4

from booster.file_bus_lock import file_bus_lock

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
        return []


class FileInvalidationBus:
    """Exchange notices through one shared file, for workers on the same host.

    A generation header detects rotation even after the file has refilled.
    Python and Node serialize reads/writes with the same local directory lock.
    Rotation discards notices and forces a full clear in every existing reader.
    """

    def __init__(self, path: Path, max_bytes: int = 1_000_000) -> None:
        """Initialize one independent cursor over the bounded shared journal."""
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        self.path = Path(path).resolve()
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Path(str(self.path) + ".lock")
        with file_bus_lock(self._lock):
            self._epoch = self._header()
        self._position = len(self._epoch)

    def _header(self) -> bytes:
        """Initialize or migrate the journal to the shared generation protocol."""
        if self.path.exists():
            with self.path.open("rb") as reader:
                header = reader.readline(35)
            if len(header) == 34 and header.startswith(b"#") and header.endswith(b"\n"):
                return header
        header = b"#" + uuid4().hex.encode("ascii") + b"\n"
        self.path.write_bytes(header)
        return header

    def publish(self, prefix: str) -> None:
        """Append a complete notice or rotate to a full-clear generation."""
        record = (json.dumps(prefix, ensure_ascii=False) + "\n").encode("utf-8")
        with file_bus_lock(self._lock):
            self._header()
            if self.path.stat().st_size + len(record) > self.max_bytes:
                self.path.write_bytes(b"#" + uuid4().hex.encode("ascii") + b"\n")
            else:
                with self.path.open("ab") as writer:
                    writer.write(record)

    def drain(self) -> List[str]:
        """Read complete records, treating any generation change as a full clear."""
        with file_bus_lock(self._lock):
            epoch = self._header()
            if epoch != self._epoch or self._position > self.path.stat().st_size:
                self._epoch = epoch
                self._position = self.path.stat().st_size
                return [FULL_CLEAR]
            with self.path.open("rb") as reader:
                reader.seek(self._position)
                records = reader.read().decode("utf-8").splitlines()
                self._position = reader.tell()
            return [json.loads(record) for record in records if record]
