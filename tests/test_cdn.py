"""Unit tests for multi-CDN integration."""

import pytest
from unittest.mock import AsyncMock, patch
from booster.cdn import CDNConfig, CDNManager


def test_cdn_headers_generation() -> None:
    headers = CDNManager.get_cdn_headers(max_age=600)
    assert headers["CDN-Cache-Control"] == "public, max-age=600"
    assert headers["Surrogate-Control"] == "max-age=600"


@pytest.mark.anyio
async def test_purge_disabled_provider() -> None:
    mgr = CDNManager(CDNConfig(provider="none"))
    res = await mgr.purge_all()
    assert res is True


@pytest.mark.anyio
async def test_purge_cloudflare_call() -> None:
    mgr = CDNManager(CDNConfig(provider="cloudflare", api_token="cf-token", zone_id="zone-123"))

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response

    res = await mgr.purge_all(client=mock_client)
    assert res is True
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert "https://api.cloudflare.com/client/v4/zones/zone-123/purge_cache" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer cf-token"


@pytest.mark.anyio
async def test_purge_bunny_call() -> None:
    mgr = CDNManager(CDNConfig(provider="bunny", api_token="bunny-key", zone_id="pull-456"))

    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response

    res = await mgr.purge_all(client=mock_client)
    assert res is True
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert "https://api.bunny.net/pullzone/pull-456/purgeCache" in args[0]
    assert kwargs["headers"]["AccessKey"] == "bunny-key"
