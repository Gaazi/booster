"""Declarative site configuration for a Booster deployment.

A host project can describe its route policy and cache limits in one JSON
file instead of Python code. The module uses only the standard library, so
core stays free of runtime dependencies, and it fails fast on an unknown or
invalid setting.
"""

import json
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
            exclude_paths=_paths(data.get("exclude_paths") or ()),
            cache_ttl=_positive_number(data.get("cache_ttl", 300.0), "cache_ttl"),
            max_cache_bytes=_positive_number(data.get("max_cache_bytes", 64 * 1024 * 1024),
                                            "max_cache_bytes"),
            enable_compression=bool(data.get("enable_compression", True)),
            enable_minification=bool(data.get("enable_minification", True)),
            surgical_invalidation=bool(data.get("surgical_invalidation", False)),
            invalidation_file=data.get("invalidation_file"),
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
        return {
            "cache_policy": self.cache_policy(),
            "cache_ttl": self.cache_ttl,
            "max_cache_bytes": int(self.max_cache_bytes),
            "enable_compression": self.enable_compression,
            "enable_minification": self.enable_minification,
            "surgical_invalidation": self.surgical_invalidation,
        }


def attach_from_config(app: Any, config: SiteConfig) -> Any:
    """Attach the engine to an application using a declarative configuration."""
    import booster

    options = config.attach_options()
    if config.invalidation_file:
        options["invalidation_bus"] = booster.FileInvalidationBus(config.invalidation_file)
    return booster.attach(app, **options)


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
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return value
