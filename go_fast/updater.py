"""go_fast backwards-compatibility shim for booster.updater."""

from booster.updater import (
    parse_version,
    classify_update,
    check_for_updates,
    apply_patch_update,
)

__all__ = [
    "parse_version",
    "classify_update",
    "check_for_updates",
    "apply_patch_update",
]
