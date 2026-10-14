import asyncio
import logging
import os
import re

import subprocess
import sys
import time
from typing import Any, Dict, Optional, Tuple

import httpx

import booster

logger = logging.getLogger("booster.updater")

CACHE_TTL_SECONDS = 86400  # 24 hours (1 day)
_cached_update_info: Optional[Dict[str, Any]] = None
_last_check_timestamp: float = 0.0



def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse a semantic version string into a (major, minor, patch) tuple."""
    cleaned = re.sub(r"^[^\d]*", "", version_str.strip())
    parts = cleaned.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2].split("-")[0].split("+")[0]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except (ValueError, IndexError):
        return (0, 0, 0)


def classify_update(current: str, latest: str) -> str:
    """Classify update level: 'none', 'patch', 'minor', or 'major'."""
    cur_maj, cur_min, cur_pat = parse_version(current)
    lat_maj, lat_min, lat_pat = parse_version(latest)

    if (lat_maj, lat_min, lat_pat) <= (cur_maj, cur_min, cur_pat):
        return "none"
    if lat_maj > cur_maj:
        return "major"
    if lat_min > cur_min:
        return "minor"
    return "patch"


async def fetch_latest_release(repo: str = "Gaazi/booster", timeout: float = 4.0) -> Optional[Dict[str, Any]]:
    """Query GitHub releases API for the latest released version."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {"User-Agent": f"booster-updater/{booster.__version__}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            logger.debug("GitHub release check returned status %d", resp.status_code)
    except httpx.RequestError as exc:
        logger.debug("Network error checking for updates: %s", exc)
    except Exception as exc:
        logger.warning("Unexpected error during update check: %s", exc)
    return None


def apply_patch_update() -> bool:
    """Safely apply a patch update in the background using pip."""
    try:
        logger.info("Auto-applying bugfix patch update...")
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "booster"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("Failed to automatically install patch update: %s", exc)
        return False


async def check_for_updates(force: bool = False, repo: str = "Gaazi/booster") -> Dict[str, Any]:
    """Check for available updates with caching and auto-patch application."""
    global _cached_update_info, _last_check_timestamp
    now = time.time()

    if not force and _cached_update_info and (now - _last_check_timestamp < CACHE_TTL_SECONDS):
        return _cached_update_info

    current = booster.__version__
    release = await fetch_latest_release(repo)
    if not release or "tag_name" not in release:
        result = {"current_version": current, "latest_version": current, "update_type": "none"}
        _cached_update_info = result
        _last_check_timestamp = now
        return result

    latest = release.get("tag_name", current)
    update_type = classify_update(current, latest)
    auto_patched = False

    if update_type == "patch" and os.getenv("BOOSTER_AUTO_UPDATE", "true").lower() in ("1", "true", "yes"):
        auto_patched = apply_patch_update()

    result = {
        "current_version": current,
        "latest_version": latest,
        "update_type": update_type,
        "release_url": release.get("html_url", ""),
        "release_name": release.get("name", latest),
        "auto_applied": auto_patched,
        "message": _build_update_message(current, latest, update_type, auto_patched),
    }
    _cached_update_info = result
    _last_check_timestamp = now
    return result


def _build_update_message(current: str, latest: str, update_type: str, auto_applied: bool) -> str:
    """Format a clear human-readable status message for the dashboard and CLI."""
    if update_type == "none":
        return f"booster is up to date (v{current})."
    if update_type == "patch":
        if auto_applied:
            return f"Bugfix patch v{latest} was automatically installed."
        return f"Bugfix patch v{latest} available. Run 'pip install --upgrade booster'."
    return f"New {update_type} version v{latest} available! Please update: pip install --upgrade booster"



MONTHLY_INTERVAL_SECONDS = 30 * 86400  # 30 days


async def run_monthly_heartbeat_check(interval: float = MONTHLY_INTERVAL_SECONDS) -> Dict[str, Any]:
    """Execute low-frequency background check for passive/headless server instances."""
    logger.info("Running periodic background update check for booster...")
    info = await check_for_updates(force=True)

    update_type = info.get("update_type", "none")
    latest = info.get("latest_version", "")
    if update_type == "patch":
        if info.get("auto_applied"):
            logger.info("✅ [booster] Automated patch v%s installed successfully.", latest)
        else:
            logger.info("⚡ [booster] Bugfix patch v%s available. Run: pip install --upgrade booster", latest)
    elif update_type in ("minor", "major"):
        logger.warning(
            "🔔 [booster] New %s version v%s available! Please upgrade: pip install --upgrade booster",
            update_type, latest
        )
    return info


async def start_heartbeat_daemon(interval: float = MONTHLY_INTERVAL_SECONDS) -> None:
    """Run monthly update check in a quiet background daemon loop."""
    while True:
        try:
            await asyncio.sleep(interval)
            await run_monthly_heartbeat_check(interval)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.debug("Background heartbeat check encountered: %s", exc)
