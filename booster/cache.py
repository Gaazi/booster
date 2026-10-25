"""High-performance in-memory LRU cache with TTL and smart invalidation."""

import hashlib
import json
import time
from functools import wraps
from threading import RLock
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


def synchronized(method: Callable[..., Any]) -> Callable[..., Any]:
    """Serialize cache operations across worker threads."""
    @wraps(method)
    def guarded(self: Any, *args: Any, **kwargs: Any) -> Any:
        """Hold the cache lock for the complete operation."""
        with self._lock:
            return method(self, *args, **kwargs)
    return guarded


@dataclass
class CacheEntry:
    """Cached response item with metadata and expiration."""
    status_code: int
    headers: List[Tuple[bytes, bytes]]
    body: bytes
    etag: str
    content_type: str
    created_at: float
    ttl: float

    @property
    def is_expired(self) -> bool:
        """Check if entry has outlived its time to live."""
        return (time.monotonic() - self.created_at) > self.ttl


class FastMemoryCache:
    """Thread-safe LRU in-memory cache supporting TTL and key invalidation."""

    def __init__(self, max_items: int = 1000, default_ttl: float = 300.0,
                 max_bytes: int = 64 * 1024 * 1024) -> None:
        """Initialize item and byte budgets with a monotonic default expiration."""
        if max_items < 1:
            raise ValueError("max_items must be positive")
        self._lock = RLock()
        self.max_items = max_items
        self.default_ttl = default_ttl
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._url_index: Dict[str, str] = {}
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.max_bytes = max_bytes
        self._bytes = 0
        self.generation = 0

    @staticmethod
    def compute_etag(content: bytes) -> str:
        """Generate a fast ETag for binary payload."""
        digest = hashlib.blake2b(content, digest_size=12).hexdigest()
        return f'W/"{digest}"'

    def make_key(self, method: str, path: str, query: bytes = b"") -> str:
        """Generate unique cache key based on request parameters."""
        raw = json.dumps((method, path, query.decode("latin1")), separators=(",", ":"))
        return hashlib.blake2b(raw.encode("utf-8"), digest_size=16).hexdigest()

    @synchronized
    def get(self, key: str) -> Optional[CacheEntry]:
        """Retrieve entry by key if valid and not expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired:
            self.delete(key)
            return None
        self._store.move_to_end(key)
        return entry

    @synchronized
    def set(
        self,
        key: str,
        path: str,
        status_code: int,
        headers: List[Tuple[bytes, bytes]],
        body: bytes,
        content_type: str = "text/html",
        ttl: Optional[float] = None,
    ) -> CacheEntry:
        """Insert or update a cache entry with LRU eviction."""
        entry = CacheEntry(
            status_code=status_code,
            headers=list(headers),
            body=body,
            etag=self.compute_etag(body),
            content_type=content_type,
            created_at=time.monotonic(),
            ttl=ttl if ttl is not None else self.default_ttl,
        )
        self.delete(key)
        self._insert_entry(key, path, entry)
        return entry

    def _insert_entry(self, key: str, path: str, entry: CacheEntry) -> None:
        """Insert one entry with LRU eviction under the caller's cache lock."""
        size = self._entry_size(entry)
        if size > self.max_bytes:
            return
        while self._store and (len(self._store) >= self.max_items or self._bytes + size > self.max_bytes):
            self.delete(next(iter(self._store)))
        self._store[key] = entry
        self._bytes += size
        self._store.move_to_end(key)
        self._url_index[key] = path

    @staticmethod
    def _entry_size(entry: CacheEntry) -> int:
        """Include response bodies and headers in the memory budget."""
        return len(entry.body) + sum(len(k) + len(v) for k, v in entry.headers)

    @synchronized
    def set_if_current(self, generation: int, *args: Any) -> Optional[CacheEntry]:
        """Reject responses fetched before an invalidation or target change."""
        return self.set(*args) if generation == self.generation else None

    @synchronized
    def delete(self, key: str) -> bool:
        """Remove single entry by key."""
        if key in self._store:
            self._bytes -= self._entry_size(self._store.pop(key))
            self._url_index.pop(key, None)
            return True
        return False

    @synchronized
    def invalidate_path_prefix(self, prefix: str) -> int:
        """Invalidate all cached items whose original path starts with prefix."""
        to_remove = [k for k, p in self._url_index.items() if p.startswith(prefix)]
        self.generation += 1
        for k in to_remove:
            self.delete(k)
        return len(to_remove)

    @synchronized
    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()
        self._url_index.clear()
        self._bytes = 0
        self.generation += 1

    @synchronized
    def count(self) -> int:
        """Return count of active entries."""
        return len(self._store)

    @synchronized
    def get_stats(self) -> dict[str, int]:
        """Expose bounded resident memory counters without cache keys or payloads."""
        return {"items": len(self._store), "bytes": self._bytes,
                "max_items": self.max_items, "max_bytes": self.max_bytes}
