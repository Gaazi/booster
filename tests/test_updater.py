"""Unit tests for booster updater module and update endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from starlette.testclient import TestClient

from booster import __version__
from booster.updater import parse_version, classify_update, check_for_updates
from booster.server import app


def next_patch_release() -> str:
    """Return a release tag that is newer than the current engine version."""
    major, minor, patch = parse_version(__version__)
    return f"v{major}.{minor}.{patch + 1}"


def test_parse_version() -> None:
    """Verify semantic version parsing."""
    assert parse_version("1.0.0") == (1, 0, 0)
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("2.1.0-beta.1") == (2, 1, 0)
    assert parse_version("invalid") == (0, 0, 0)


def test_classify_update() -> None:
    """Verify classification of update severity."""
    assert classify_update("1.0.0", "1.0.0") == "none"
    assert classify_update("1.0.1", "1.0.0") == "none"
    assert classify_update("1.0.0", "1.0.1") == "patch"
    assert classify_update("1.0.0", "1.1.0") == "minor"
    assert classify_update("1.0.0", "2.0.0") == "major"


@pytest.mark.anyio
async def test_default_update_check_does_not_install(monkeypatch) -> None:
    """A release check never changes the environment without explicit opt-in."""
    monkeypatch.delenv("BOOSTER_AUTO_UPDATE", raising=False)
    release = {"tag_name": next_patch_release()}
    with patch("booster.updater.fetch_latest_release", new_callable=AsyncMock, return_value=release):
        with patch("booster.updater.apply_patch_update") as install:
            result = await check_for_updates(force=True)
    assert result["update_type"] == "patch" and result["auto_applied"] is False
    install.assert_not_called()


@pytest.mark.anyio
async def test_check_for_updates_patch(monkeypatch) -> None:
    """Verify patch update detection and auto-apply formatting."""
    mock_release = {
        "tag_name": next_patch_release(),
        "name": "next patch release",
        "html_url": "https://github.com/Gaazi/booster/releases/tag/next-patch",
    }
    monkeypatch.setenv("BOOSTER_AUTO_UPDATE", "true")
    with patch("booster.updater.fetch_latest_release", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_release
        with patch("booster.updater.apply_patch_update", return_value=True):
            res = await check_for_updates(force=True)
            assert res["update_type"] == "patch"
            assert res["auto_applied"] is True
            assert "automatically installed" in res["message"]


@pytest.mark.anyio
async def test_check_for_updates_major() -> None:
    """Verify major update detection and notification formatting."""
    mock_release = {
        "tag_name": "v2.0.0",
        "name": "v2.0.0 Next Gen",
        "html_url": "https://github.com/Gaazi/booster/releases/tag/v2.0.0",
    }
    with patch("booster.updater.fetch_latest_release", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_release
        res = await check_for_updates(force=True)
        assert res["update_type"] == "major"
        assert res["auto_applied"] is False
        assert "Please update" in res["message"]


def test_server_update_endpoints() -> None:
    """Verify /api/check-update and /api/apply-update endpoints."""
    client = TestClient(app, base_url="http://127.0.0.1:5050", client=("127.0.0.1", 12345))
    headers = {"X-Booster-Admin": "1"}

    with patch("booster.updater.fetch_latest_release", new_callable=AsyncMock, return_value={"tag_name": "v1.0.1"}):
        res = client.get("/api/check-update", headers=headers)
        assert res.status_code == 200

        data = res.json()
        assert "current_version" in data
        assert "update_type" in data

    with patch("booster.updater.apply_patch_update", return_value=True):
        res_apply = client.post("/api/apply-update", headers=headers)
        assert res_apply.status_code == 200
        assert res_apply.json()["success"] is True
