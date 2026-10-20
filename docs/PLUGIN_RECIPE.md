# Plugin Recipe: embed Booster in any project

Booster runs **inside** the host application as middleware. No extra server, no
extra port, no external cache database. This is the recommended production shape.

Verified against Booster `1.0.1.dev1` (Python 3.10+, FastAPI/Starlette, Django,
Node 18+). Engines and behaviour are described in [INTEGRATION.md](INTEGRATION.md).

## 1. Install a pinned revision

```bash
pip install "booster @ git+https://github.com/Gaazi/booster.git@<REVIEWED_COMMIT>"
```

Pin the exact reviewed commit. Never install a moving branch in production.

## 2. One adapter file in the host project

```python
# myapp/booster_plugin.py
import booster

engine = booster.attach(
    app,
    cache_policy=booster.CachePolicy(
        include_paths=("/static/css/", "/static/js/"),   # public assets only
        exclude_paths=("/media/", "/account/", "/api/"), # private, user uploads, APIs
    ),
    enable_compression=False,   # keep False when the app already compresses
    enable_minification=False,  # keep False when the build step minifies
    max_cache_bytes=8 * 1024 * 1024,
    cache_ttl=600,
)
```

`include_paths=None` allows every eligible route, `()` disables route caching
entirely. Exclusions always win.

## 3. Attach before the other middleware

```python
# myapp/main.py
from myapp.booster_plugin import engine   # 1) Booster first
from myapp.middleware import setup_middlewares

setup_middlewares(app)                     # 2) security/CORS/session after
```

Starlette/FastAPI wrap the **last registered** middleware outermost. Registering
Booster first puts it innermost, directly above the router. That guarantees:

- security, CORS, host validation and session layers run on **every** request,
  including a cache hit;
- Booster stores the **uncompressed** representation, so the app's own
  compression layer stays the single compression owner.

Register Booster at import time. Adding middleware after the app has started
raises `RuntimeError`.

## 4. Choose routes that are genuinely public

- Booster bypasses any request carrying `Cookie`, `Authorization` or a session
  scope, and any response marked `private`, `no-store`, `no-cache` or
  `no-transform`.
- The origin must declare `Cache-Control: public`. Responses without it are not
  stored.
- Personalised pages (per-user HTML, CSRF tokens, dashboards) must stay out of
  `include_paths`.
- User uploads (`/media/`, avatars, documents) must stay excluded.

Starlette's `StaticFiles` does not send `Cache-Control`, so mounted assets are
not cached until the mount declares it:

```python
class PublicStatic(StaticFiles):
    """Serve mounted assets with an explicit public cache policy."""
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response

app.mount("/static", PublicStatic(directory="static"), name="static")
```

Use content-versioned asset names (`app.v2.css`) so a deploy never needs a
cache purge.

## 5. Keep one compression owner

If the app already has GZip/Brotli middleware, set `enable_compression=False`.
Two owners double-compress or corrupt the `Content-Length`/`ETag` pair.

## 6. Several workers

Each worker owns an independent RAM cache, and a write invalidates only the
worker that received it. Until shared invalidation exists:

- cache only immutable, versioned assets;
- keep the byte budget per worker in mind (4 workers × 64 MiB = 256 MiB);
- a short TTL bounds how long a stale entry can live, but does not remove it.

## 7. Status and administration

`engine.get_status()` returns configuration and counters without cache keys,
payloads, tokens or URLs. Expose it only behind the host's own admin
authentication. `engine.cache.clear()` clears the current worker only. Never
mount the standalone dashboard or proxy on a public site.

## 8. Verify before rollout

1. Run the [conformance checklist](CONFORMANCE_CHECKLIST.md) in the host
   project; all checks must pass.
2. Measure cold and warm p50/p95, origin call counts and payload sizes with and
   without Booster.
3. Confirm private routes, range requests and signed uploads still bypass the
   cache.

Local RAM timings do not prove mobile network or production loading speed.
Report measured results only.

A working reference implementation lives in this repository:
`examples/host_app.py` (adapter, route policy and registration order),
`examples/measure_host.py` (before/after measurement) and
`tests/test_host_conformance.py` (the checklist executed on every CI run).

## Django

```python
MIDDLEWARE = [
    "booster.DjangoRocketMiddleware",
    "django.middleware.security.SecurityMiddleware",
]
```

Django responses must declare `Cache-Control: public` themselves. Django
middleware does not consult a route policy, so restrict caching through the
response headers of the views you trust.

## Node

```javascript
import { booster } from "booster-node";
app.use(booster({ includePaths: ["/static/"], excludePaths: ["/api/"] }));
```

The Node engine is the canonical TypeScript build (`booster-node/src`).

## What Booster does not do

- It does not authorize anything. Route policy is defence in depth.
- It does not coordinate caches between workers, browsers or CDNs.
- It does not minify HTML or CSS, and it does not replace a build pipeline.
- It does not make a slow origin fast. It removes repeated work and bytes.
