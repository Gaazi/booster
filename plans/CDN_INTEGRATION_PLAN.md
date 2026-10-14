# 🌐 Multi-CDN Integration Architecture & Guide

> **Providers Supported:** Cloudflare, BunnyCDN, Fastly  
> **Module:** `booster.cdn.CDNManager`  
> **Status:** Implemented, Tested, Zero-Bloat  

---

## ⚡ Why Multi-CDN Integration Adds ZERO Load

1. **Standardized HTTP Headers (صفر سی پی یو لوڈ):**
   - Major CDNs (Cloudflare, Bunny, Fastly, CloudFront) follow universal HTTP caching standards.
   - `booster` automatically provides `CDN-Cache-Control` and `Surrogate-Control` headers.
   - The edge network automatically reads these headers and caches assets globally.

2. **Asynchronous Background Purge (نان بلاکنگ):**
   - Cache purge requests to Cloudflare or BunnyCDN are executed asynchronously via `httpx.AsyncClient`.
   - Never blocks client requests or adds even 0.1ms of latency to responses.

3. **Sleeping State when Unused:**
   - If no CDN API token is configured, the CDN module remains completely idle (0 memory/CPU usage).

---

## 🛠️ Supported CDN Providers

| Provider | Logo / Identity | Purge API Endpoint | Auth Method |
| :--- | :--- | :--- | :--- |
| **Cloudflare** | 🟧 Orange Cloud | `/client/v4/zones/{id}/purge_cache` | Bearer API Token |
| **BunnyCDN** | 🐰 Bunny.net | `/pullzone/{id}/purgeCache` | AccessKey Header |
| **Fastly** | 🔴 Fastly Edge | `/service/{id}/purge_all` | Fastly-Key Header |

---

## 💻 Python Usage Example

```python
from booster import CDNConfig, CDNManager

# Configure for Cloudflare
cf_manager = CDNManager(CDNConfig(
    provider="cloudflare",
    api_token="your-cloudflare-api-token",
    zone_id="your-zone-id"
))

# Configure for BunnyCDN
bunny_manager = CDNManager(CDNConfig(
    provider="bunny",
    api_token="your-bunny-access-key",
    zone_id="your-pull-zone-id"
))

# Trigger instant global purge
await cf_manager.purge_all()
```
