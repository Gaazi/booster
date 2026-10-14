"""Unit tests for booster updater module and update endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from starlette.testclient import TestClient

from booster.updater import parse_version, classify_update, check_for_updates
from booster.server import app


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
async def test_check_for_updates_patch() -> None:
    """Verify patch update detection and auto-apply formatting."""
    mock_release = {
        "tag_name": "v1.0.1",
        "name": "v1.0.1 Bugfix",
        "html_url": "https://github.com/Gaazi/booster/releases/tag/v1.0.1",
    }
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
    headers = {"X-Go-Fast-Admin": "1"}

    res = client.get("/api/check-update", headers=headers)
    assert res.status_code == 200

    data = res.json()
    assert "current_version" in data
    assert "update_type" in data

    with patch("booster.updater.apply_patch_update", return_value=True):
        res_apply = client.post("/api/apply-update", headers=headers)
        assert res_apply.status_code == 200
        assert res_apply.json()["success"] is True
