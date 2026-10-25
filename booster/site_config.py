"""Declarative site configuration for a Booster deployment.

A host project can describe its route policy and cache limits in one JSON
file instead of Python code. The module uses only the standard library, so
core stays free of runtime dependencies, and it fails fast on an unknown or
invalid setting.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from booster.cache_policy import CachePolicy

KNOWN_KEYS = {
    "include_paths",
    "exclude_paths",
    "cache_ttl",
    "max_cache_bytes",
    "enable_compression",
    "enable_minification",
    "surgical_invalidation",
    "invalidation_file",
}


@dataclass(frozen=True)
class SiteConfig:
    """One site's route policy and cache limits."""

    include_paths: Optional[Tuple[str, ...]] = None
    exclude_paths: Tuple[str, ...] = ()
    cache_ttl: float = 300.0
    max_cache_bytes: int = 64 * 1024 * 1024
    enable_compression: bool = True
    enable_minification: bool = True
    surgical_invalidation: bool = False
    invalidation_file: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SiteConfig":
        """Build a configuration from a mapping and reject unknown settings."""
        unknown = sorted(set(data) - KNOWN_KEYS)
        if unknown:
            raise ValueError(f"Unknown site configuration keys: {', '.join(unknown)}")
        return cls(
            include_paths=_optional_paths(data.get("include_paths")),
            exclude_paths=_paths(data.get("exclude_paths", ())),
            cache_ttl=_positive_number(data.get("cache_ttl", 300.0), "cache_ttl"),
            max_cache_bytes=_positive_bytes(data.get("max_cache_bytes", 64 * 1024 * 1024)),
            enable_compression=_boolean(data.get("enable_compression", True), "enable_compression"),
            enable_minification=_boolean(data.get("enable_minification", True), "enable_minification"),
            surgical_invalidation=_boolean(data.get("surgical_invalidation", False), "surgical_invalidation"),
            invalidation_file=_invalidation_file(data.get("invalidation_file")),
        )

    @classmethod
    def from_file(cls, path: Path) -> "SiteConfig":
        """Read a configuration from a JSON file."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Site configuration must be a JSON object")
        return cls.from_dict(raw)

    def cache_policy(self) -> CachePolicy:
        """Build the route policy for this site."""
        return CachePolicy(include_paths=self.include_paths, exclude_paths=self.exclude_paths)

    def attach_options(self) -> Dict[str, Any]:
        """Build the keyword arguments for the engine attach call."""
        options = {
            "cache_policy": self.cache_policy(),
            "cache_ttl": self.cache_ttl,
            "max_cache_bytes": int(self.max_cache_bytes),
            "enable_compression": self.enable_compression,
            "enable_minification": self.enable_minification,
            "surgical_invalidation": self.surgical_invalidation,
        }
        if self.invalidation_file:
            from booster.invalidation import FileInvalidationBus

            options["invalidation_bus"] = FileInvalidationBus(self.invalidation_file)
        return options


def attach_from_config(app: Any, config: SiteConfig) -> Any:
    """Attach the engine to an application using a declarative configuration."""
    import booster

    return booster.attach(app, **config.attach_options())


def _paths(value: Any) -> Tuple[str, ...]:
    """Validate a list of absolute route prefixes."""
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValueError("Route paths must be a list of absolute URL prefixes")
    for path in value:
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError("Route paths must be absolute URL prefixes")
    return tuple(value)


def _optional_paths(value: Any) -> Optional[Tuple[str, ...]]:
    """Validate an optional list of absolute route prefixes."""
    if value is None:
        return None
    return _paths(value)


def _positive_number(value: Any, name: str) -> float:
    """Validate a positive numeric setting."""
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0):
        raise ValueError(f"{name} must be a positive number")
    return value


def _boolean(value: Any, name: str) -> bool:
    """Reject misspelled booleans instead of coercing strings to true."""
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _positive_bytes(value: Any) -> int:
    """Validate a whole-byte budget before it reaches the cache."""
    number = _positive_number(value, "max_cache_bytes")
    if int(number) != number:
        raise ValueError("max_cache_bytes must be a positive integer")
    return int(number)


def _invalidation_file(value: Any) -> Optional[str]:
    """Accept only an explicit notice path or no shared bus."""
    if value is not None and (not isinstance(value, str) or not value.strip() or "\0" in value):
        raise ValueError("invalidation_file must be a nonempty path string or null")
    return value
