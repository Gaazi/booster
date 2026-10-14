"""Lightweight multi-CDN integration for Cloudflare, BunnyCDN, and Fastly."""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

logger = logging.getLogger("booster.cdn")


import os


@dataclass
class CDNConfig:
    """Configuration for CDN automated cache synchronization."""
    provider: str = "none"  # "cloudflare", "bunny", "fastly", "none"
    api_token: str = ""
    zone_id: str = ""

    @classmethod
    def from_env(cls) -> "CDNConfig":
        """Auto-detect CDN credentials from environment variables."""
        if os.getenv("CLOUDFLARE_ZONE_ID") and os.getenv("CLOUDFLARE_API_TOKEN"):
            return cls(
                provider="cloudflare",
                api_token=os.environ["CLOUDFLARE_API_TOKEN"],
                zone_id=os.environ["CLOUDFLARE_ZONE_ID"],
            )
        if os.getenv("BUNNY_ACCESS_KEY") and os.getenv("BUNNY_PULL_ZONE_ID"):
            return cls(
                provider="bunny",
                api_token=os.environ["BUNNY_ACCESS_KEY"],
                zone_id=os.environ["BUNNY_PULL_ZONE_ID"],
            )
        if os.getenv("FASTLY_KEY") and os.getenv("FASTLY_SERVICE_ID"):
            return cls(
                provider="fastly",
                api_token=os.environ["FASTLY_KEY"],
                zone_id=os.environ["FASTLY_SERVICE_ID"],
            )
        return cls(provider="none")


class CDNManager:
    """Zero-overhead multi-CDN cache purger and header generator."""

    def __init__(self, config: Optional[CDNConfig] = None) -> None:
        self.config = config or CDNConfig()

    @staticmethod
    def get_cdn_headers(max_age: int = 300) -> Dict[str, str]:
        """Return standardized edge caching headers compatible with all major CDNs."""
        return {
            "CDN-Cache-Control": f"public, max-age={max_age}",
            "Surrogate-Control": f"max-age={max_age}",
        }

    async def purge_all(self, client: Optional[httpx.AsyncClient] = None) -> bool:
        """Asynchronously purge edge cache across configured CDN provider."""
        provider = self.config.provider.lower()
        if provider == "none" or not self.config.api_token:
            return True

        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
            close_client = True

        try:
            if provider == "cloudflare":
                return await self._purge_cloudflare(client)
            if provider == "bunny":
                return await self._purge_bunny(client)
            if provider == "fastly":
                return await self._purge_fastly(client)
            return False
        finally:
            if close_client:
                await client.aclose()

    async def _purge_cloudflare(self, client: httpx.AsyncClient) -> bool:
        """Purge Cloudflare Zone Cache via Client v4 API."""
        url = f"https://api.cloudflare.com/client/v4/zones/{self.config.zone_id}/purge_cache"
        headers = {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json",
        }
        res = await client.post(url, headers=headers, json={"purge_everything": True})
        return res.status_code == 200

    async def _purge_bunny(self, client: httpx.AsyncClient) -> bool:
        """Purge BunnyCDN Pull Zone Cache."""
        url = f"https://api.bunny.net/pullzone/{self.config.zone_id}/purgeCache"
        headers = {"AccessKey": self.config.api_token}
        res = await client.post(url, headers=headers)
        return res.status_code in (200, 204)

    async def _purge_fastly(self, client: httpx.AsyncClient) -> bool:
        """Purge Fastly Service Cache."""
        url = f"https://api.fastly.com/service/{self.config.zone_id}/purge_all"
        headers = {
            "Fastly-Key": self.config.api_token,
            "Accept": "application/json",
        }
        res = await client.post(url, headers=headers)
        return res.status_code == 200
