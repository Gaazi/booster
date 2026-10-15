# Booster: Complete Features and System Architecture Reference

> **Document Version:** 1.0.0  
> **Target Audience:** Developers, System Architects, and Autonomous Agents.  
> **Related Guides:** [INTEGRATION.md](INTEGRATION.md) | [USE_CASES.md](USE_CASES.md) | [BUILDS.md](BUILDS.md) | [COMMANDS.md](../COMMANDS.md) | [CODEMAP.md](../CODEMAP.md)

---

## 1. Executive Summary & Philosophy

**Booster** is a unified, ultra-fast caching, conservative minification, and adaptive compression engine engineered for Python (ASGI / FastAPI / Starlette, WSGI / Django) and Node.js (`booster-node`). It operates either as an embedded, single-line middleware or as a standalone local reverse proxy gateway with an interactive telemetry dashboard.

### Core Design Philosophy
1. **Zero External Infrastructure Required:** Eliminates dependencies on external caching services such as Redis, Memcached, or Varnish for local node acceleration, saving cloud cost and network round-trip overhead.
2. **Safety-First HTTP RFC Compliance:** Strictly conforms to RFC 9111 (HTTP Caching) and RFC 9110 (HTTP Semantics). Booster never caches personalized, authenticated, session-scoped, or mutating requests.
3. **Bounded In-Memory Footprint:** Operates within strictly bounded process RAM budgets (`max_cache_bytes`) with monotonic LRU (Least Recently Used) eviction to prevent memory bloat or out-of-memory crashes.
4. **Separation of Concerns:** Booster only handles reusable response acceleration. It does not replace application authentication, authorization, database indexing, frontend asset bundling, or TLS termination.

---

## 2. Complete Feature Catalogue (Facilities Provided)

Booster provides seven core architectural facilities:

### 2.1 Microsecond In-Memory LRU Cache (`FastMemoryCache`)
- **Monotonic TTL Expiration:** Cache entries expire based on high-resolution monotonic timestamps (`time.monotonic()`), remaining immune to system clock skews and NTP adjustments.
- **Dual Budget Limits:** Bounded by total item count (`max_size`) and configurable memory budget (`max_cache_bytes`, defaults to 64 MiB; can be tuned e.g. 8 MiB for tight workers).
- **LRU Eviction Policy:** Transparent eviction of least recently accessed entries whenever size or memory ceilings are reached.
- **Fast Binary ETag & 304 Not Modified:** Generates SHA-256 binary entity tags for cached responses. Automatically processes `If-None-Match` requests and serves standard `304 Not Modified` headers without re-transmitting response bodies.
- **Safe Thread Synchronization:** All cache reads, writes, and evictions are guarded by internal reentrant locks (`@synchronized`).

### 2.2 Strict Privacy & HTTP RFC 9111 Boundaries (`http_policy.py`)
- **Uncompromising Private Data Protection:** Automatically bypasses shared caching if:
  - The request contains `Authorization` headers or cookies.
  - The response declares `Cache-Control: private`, `no-store`, `no-cache`, or `no-transform`.
  - The response contains session, auth, or `Set-Cookie` headers.
  - The request includes conditional headers (`If-Match`, `If-Modified-Since`) not matching valid stored representations.
- **Hop-by-Hop Header Sanitization:** Automatically strips connection-specific headers (`Connection`, `Keep-Alive`, `Proxy-Authenticate`, `Transfer-Encoding`, etc.) to preserve HTTP gateway integrity.
- **Origin Freshness Capping:** Honors origin `max-age` and `s-maxage` directives. A configured TTL will never serve a response past the maximum age declared by the upstream origin.
- **Path Policy Routing (`CachePolicy`):** Granular path control via `include_paths` and `exclude_paths`. Exact path matching and slash-terminated subtrees (e.g., `/static/`) are strictly enforced; exclusions always override inclusions.

### 2.3 Automatic Mutation Invalidation
- **State-Safety Around Writes:** Any mutating HTTP method (`POST`, `PUT`, `DELETE`, `PATCH`) invalidates derived cached reads.
- **Dual Invalidation:** Invalidation occurs *before* forwarding the mutation to upstream (to avoid serving stale reads during long transactions) and *after* completion (to clear data altered by the write).
- **Path-Prefix Invalidation:** Supports surgical invalidation of subtrees (`invalidate_path_prefix`) or full cache purge when cross-route dependencies exist.

### 2.4 Adaptive Content Compression (`ResponseCompressor`)
- **Client Encoding Negotiation:** Automatically inspects client `Accept-Encoding` headers and negotiates the optimal algorithm:
  1. **Brotli (`br`):** Highest compression ratio (up to 85% reduction for text); loaded lazily via optional `[brotli]` extra.
  2. **Gzip (`gzip`):** Standard, ubiquitous compression using Python standard library `gzip` (zero-dependency).
  3. **Identity (Uncompressed):** Fallback when the client supports neither.
- **MIME Eligibility & Thresholds:** Only compresses textual MIME types (`text/*`, `application/json`, `application/javascript`, `image/svg+xml`, etc.). Small payloads below a configured byte threshold (e.g. 256 bytes) pass through uncompressed to eliminate CPU overhead.
- **Vary Header Preservation:** Accurately attaches or merges `Vary: Accept-Encoding` to prevent intermediate proxies from poisoning client caches.

### 2.5 Conservative & Safe Minification (`FastMinifier`)
- **Lossless JSON Minification:** Safely removes insignificant whitespace from UTF-8 JSON payloads without rounding numbers, altering string literals, or corrupting escaped sequences.
- **HTML & CSS Integrity Preservation:** Intentionally leaves HTML and CSS whitespace intact by default. Aggressive regex-based HTML/CSS minifiers frequently break inline templates, preformatted blocks, and CSS custom properties; Booster prioritizes rendering stability.

### 2.6 Multi-CDN Edge Synchronization (`CDNManager`)
- **Standardized Edge Headers:** Automatically emits `CDN-Cache-Control` and `Surrogate-Control` headers for eligible public static assets.
- **Multi-Provider Purge Integration:** Built-in asynchronous cache purge clients for:
  - **Cloudflare** (via Cloudflare Client API v4).
  - **BunnyCDN** (via Bunny Pull Zone Cache API).
  - **Fastly** (via Fastly Service Cache API).
- **Environment Auto-Detection:** Automatically loads CDN credentials from environment variables (`CLOUDFLARE_API_KEY`, `BUNNY_API_KEY`, `FASTLY_API_KEY`).

### 2.7 Standalone Proxy Gateway & Telemetry Dashboard (`booster[server]`)
- **Zero-Code Reverse Proxy Gateway:** Runs on port `5051` as a standalone reverse proxy (`SpeedProxyServer`), instantly accelerating any upstream web app (Django, Express, Flask, Rails, PHP/Laravel, Go).
- **Interactive Real-Time GUI Dashboard:** Runs on port `5050` (`booster/server.py`), presenting live telemetry metrics:
  - Request counters (total, cached hits, missed, bypassed).
  - Bandwidth savings (raw bytes saved via compression/cache).
  - Real-time cache memory usage and active entry count.
  - Redacted recent request activity logs.
- **Local Access Security Guard (`LocalAccessGuard`):** Blocks DNS rebinding attacks, enforces loopback access, and secures management endpoints using the `X-Booster-Admin` header.
- **Automatic Dev Port Scanner:** Probes common development ports (8000, 3000, 5000, 8080) on loopback to detect running web servers with one click.
- **Smart Update Daemon:** Checks GitHub Releases for updates; features a quiet monthly background heartbeat daemon (`updater.py`) for headless servers without intrusive auto-installs.

---

## 3. System Architecture & Workflows

### 3.1 Request Lifecycle: Cache Read Flow (GET/HEAD)

```mermaid
flowchart TD
    Req([Incoming HTTP Request]) --> CheckPolicy{Allowed by CachePolicy?}
    CheckPolicy -- No --> Bypass[Forward Directly to Upstream]
    CheckPolicy -- Yes --> CheckPrivacy{Request Cacheable?<br/>No Auth / Cookies / Unsafe Vary}
    
    CheckPrivacy -- No --> Bypass
    CheckPrivacy -- Yes --> Lookup{Lookup in FastMemoryCache}
    
    Lookup -- Hit & Not Expired --> Conditional{If-None-Match ETag Match?}
    Conditional -- Yes --> Send304[Return 304 Not Modified<br/>+ Preserved Security Headers]
    Conditional -- No --> SendCached[Return Cached Payload<br/>+ Age & Representation Headers]
    
    Lookup -- Miss or Expired --> FetchOrigin[Fetch from Upstream Origin]
    FetchOrigin --> RespEligible{Response Cacheable?<br/>Status 200, public, no-store false}
    
    RespEligible -- No --> ReturnOrigin[Return Original Upstream Response]
    RespEligible -- Yes --> Optimize[Minify JSON & Negotiate Brotli/Gzip]
    Optimize --> StoreCache[Store in FastMemoryCache with TTL & Size Budget]
    StoreCache --> ReturnTransformed[Return Optimized Response to Client]
```

### 3.2 Mutation Lifecycle: Invalidation Flow (POST/PUT/DELETE/PATCH)

```mermaid
flowchart TD
    MutReq([Incoming Mutating Request]) --> PreInvalidate[1. Pre-Invalidate FastMemoryCache<br/>Flushes pending read state]
    PreInvalidate --> ExecuteUpstream[2. Forward Mutation to Upstream Application]
    ExecuteUpstream --> PostInvalidate[3. Post-Invalidate FastMemoryCache<br/>Flushes derived state]
    PostInvalidate --> ReturnMutResp([Return Mutation Response to Client])
```

### 3.3 Recommended Middleware Layering Order

To preserve security, authentication, and CORS invariants, Booster must be registered inside outer security and host-validation layers:

```mermaid
flowchart TD
    subgraph Host Application Middleware Stack
        direction TB
        M1[SecurityMiddleware / TrustedHost / SSL Redirect]
        M2[CORSMiddleware]
        M3[Booster Middleware: booster.attach or DjangoRocketMiddleware]
        M4[Authentication & Session Middleware]
        M5[Application Routes / Controllers / Database]
    end
    M1 --> M2 --> M3 --> M4 --> M5
```
*Why this matters:* When Booster serves a cached public asset from RAM, outer layers (`M1`, `M2`) still execute, ensuring security headers and CORS policies are faithfully applied to every hit.

---

## 4. Module Map & Source Code Directory Structure

```text
booster/
├── __init__.py           # Package entry point; lazy imports for optional server/cdn/brotli
├── asgi_response.py      # ASGIResponseOptimizer: captures, minifies, and compresses ASGI responses
├── booster.py            # RocketBooster: ASGI middleware and lifecycle orchestrator
├── cache.py              # FastMemoryCache: LRU thread-safe cache, ETag calculation, byte budgets
├── cache_policy.py       # CachePolicy: path prefix and exclusion rules
├── cdn.py                # CDNManager: multi-CDN purge and CDN-Cache-Control header management
├── cli.py                # Command-line interface launcher
├── compressor.py         # ResponseCompressor: Brotli and Gzip adaptive compression
├── django_support.py     # DjangoRocketMiddleware: WSGI/Django cache adapter
├── http_policy.py        # RFC 9111 HTTP compliance, privacy rules, and header filtering
├── local_security.py     # LocalAccessGuard: DNS rebinding defense and X-Booster-Admin auth
├── minifier.py           # FastMinifier: conservative JSON minification
├── proxy.py              # SpeedProxyServer: standalone reverse proxy engine
├── proxy_transport.py    # Gateway streaming, upload bounds, and pooled upstream connections
├── server.py             # Management telemetry dashboard (port 5050) & gateway runner (5051)
├── telemetry.py          # TelemetryTracker: thread-safe hit/miss/bandwidth metrics
└── updater.py            # Update checking against GitHub Releases and monthly heartbeat daemon

booster-node/             # Node.js Express/Connect implementation
├── lib/                  # Node cache, compression, and middleware units
├── test/                 # Test suites for Node.js engine
└── package.json          # Node package manifest

docs/                     # Specialized Technical Guides
├── BUILDS.md             # Package build bundle, verification, and promotion
├── FEATURES_AND_ARCHITECTURE.md # (This file) Complete reference & architecture
├── INTEGRATION.md        # Step-by-step framework integration and review guide
├── NEXT_STEPS.md         # Priority handoff tasks for next agents
└── USE_CASES.md          # Workload-based suitability and decision matrix

plans/                    # Multi-language roadmap and design blueprints
├── ROADMAP_MULTI_LANGUAGE.md # Strategy across Node, Go, and Rust
├── GO_BOOSTER_PLAN.md        # Phase 2 Go implementation design
└── RUST_BOOSTER_PLAN.md      # Phase 3 Rust high-throughput engine design

scripts/                  # Distribution, bundle packaging, and CI verification
├── build_bundle.py       # SHA-256 verified package bundling script
└── promote_demo.py       # Controlled release branch promotion script
```

---

## 5. Deployment & Integration Patterns

### 5.1 Embedded ASGI (FastAPI / Starlette)
```python
import booster
from fastapi import FastAPI

app = FastAPI()

# Single-line attachment with custom policy
engine = booster.attach(
    app,
    cache_policy=booster.CachePolicy(
        include_paths=("/static/", "/public/"),
        exclude_paths=("/static/uploads/",),
    ),
    enable_minification=True,
    enable_compression=True,
    cache_ttl=300,                  # 5 minutes RAM TTL
    max_cache_bytes=32 * 1024 * 1024 # 32 MiB RAM budget
)
```

### 5.2 Embedded Django (WSGI)
In `settings.py`:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'booster.DjangoRocketMiddleware',  # Place after security, before auth/sessions
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ...
]

BOOSTER_CONFIG = {
    'CACHE_TTL': 300,
    'MAX_CACHE_BYTES': 32 * 1024 * 1024,
    'ENABLE_COMPRESSION': True,
}
```

### 5.3 Embedded Node.js / Express
```javascript
const express = require('express');
const { booster } = require('booster-node');

const app = express();
app.use(booster({
    ttl: 300,
    maxCacheBytes: 32 * 1024 * 1024,
}));
```

### 5.4 Standalone Proxy Gateway
Accelerate any legacy or external upstream service without code changes:
```bash
# Starts proxy gateway on port 5051 and dashboard on port 5050
booster --target http://127.0.0.1:8000
```

---

## 6. Operational Boundaries & Golden Rules for Agents

When integrating or maintaining Booster, all agents must adhere to the following principles:

1. **Never Cache Personalized HTML:** Never cache responses containing user names, account IDs, session tokens, or CSRF tokens. Public page caching is valid only when every visitor receives the exact same representation.
2. **Per-Process Memory Budgets:** The RAM cache lives inside the running process. In multi-worker deployments (e.g. Gunicorn with multiple Uvicorn workers), each worker maintains an independent cache. Multi-worker invalidations do not synchronize automatically across worker boundaries.
3. **One Compression Owner:** If upstream or a CDN reverse proxy already performs Gzip/Brotli compression, disable Booster's compression (`enable_compression=False`) to avoid duplicate CPU work.
4. **Preserve Range & Stream Requests:** Booster deliberately bypasses media streaming and HTTP 206 Partial Content requests; never attempt to force large audio/video streams into RAM cache.
5. **Conservative Minification:** Do not replace `FastMinifier` with naive regular-expression string replacers on HTML/CSS; whitespace and comments can carry syntax meaning in modern web templates.
