"""High-performance in-memory LRU cache with TTL and smart invalidation."""

import hashlib
import time
from functools import wraps
from threading import RLock
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def synchronized(method):
    """Serialize cache operations across worker threads."""
    @wraps(method)
    def guarded(self, *args, **kwargs):
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

    def __init__(self, max_items: int = 1000, default_ttl: float = 300.0) -> None:
        if max_items < 1:
            raise ValueError("max_items must be positive")
        self._lock = RLock()
        self.max_items = max_items
        self.default_ttl = default_ttl
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._url_index: Dict[str, str] = {}

    @staticmethod
    def compute_etag(content: bytes) -> str:
        """Generate a fast ETag for binary payload."""
        digest = hashlib.blake2b(content, digest_size=12).hexdigest()
        return f'W/"{digest}"'

    def make_key(self, method: str, path: str, query: bytes = b"") -> str:
        """Generate unique cache key based on request parameters."""
        raw = f"{method}:{path}:{query.decode('latin1', 'ignore')}"
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
        if len(self._store) >= self.max_items and key not in self._store:
            oldest_key, _ = self._store.popitem(last=False)
            self._url_index.pop(oldest_key, None)

        entry = CacheEntry(
            status_code=status_code,
            headers=list(headers),
            body=body,
            etag=self.compute_etag(body),
            content_type=content_type,
            created_at=time.monotonic(),
            ttl=ttl if ttl is not None else self.default_ttl,
        )
        self._store[key] = entry
        self._store.move_to_end(key)
        self._url_index[key] = path
        return entry

    @synchronized
    def delete(self, key: str) -> bool:
        """Remove single entry by key."""
        if key in self._store:
            del self._store[key]
            self._url_index.pop(key, None)
            return True
        return False

    @synchronized
    def invalidate_path_prefix(self, prefix: str) -> int:
        """Invalidate all cached items whose original path starts with prefix."""
        to_remove = [k for k, p in self._url_index.items() if p.startswith(prefix)]
        for k in to_remove:
            self.delete(k)
        return len(to_remove)

    @synchronized
    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()
        self._url_index.clear()

    @synchronized
    def count(self) -> int:
        """Return count of active entries."""
        return len(self._store)
