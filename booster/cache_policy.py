"""Select cacheable routes without embedding website-specific rules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CachePolicy:
    """Allow optional route prefixes and let exclusions always take precedence."""

    include_paths: tuple[str, ...] | None = None
    exclude_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject ambiguous prefixes before middleware starts serving traffic."""
        for paths in (self.include_paths, self.exclude_paths):
            if paths is not None and (not isinstance(paths, tuple) or
                    any(not isinstance(path, str) or not path.startswith("/") for path in paths)):
                raise ValueError("Cache paths must be tuples of absolute URL prefixes")

    def allows(self, path: str) -> bool:
        """Match complete route names or explicitly slash-terminated subtrees."""
        if any(self._matches(path, prefix) for prefix in self.exclude_paths):
            return False
        return self.include_paths is None or any(
            self._matches(path, prefix) for prefix in self.include_paths)

    @staticmethod
    def _matches(path: str, prefix: str) -> bool:
        """Keep /public from accidentally matching /public-private."""
        return path.startswith(prefix) if prefix.endswith("/") else path == prefix
