# Booster integration and review guide

## Purpose and ownership

Booster owns reusable response caching, optional compression, conservative
minification, mutation invalidation and performance counters. Website projects
import Booster and provide configuration; they must not copy its engine.
It does not replace authentication, authorization, database tuning, upload
validation, security middleware, frontend builds or website business logic.

The supported package and command are both `booster`. This development change
removes the retired package and command. Existing consumers must use Booster
imports before upgrading. The Python ASGI/Django engine and Node engine are
separate runtime implementations; Python consumers do not install Node.

## Install a reviewed revision

Pin a full reviewed Git commit in the consuming application's requirements:

```text
booster @ git+https://github.com/Gaazi/booster.git@FULL_REVIEWED_COMMIT
```

Install in that project's virtual environment. Do not install an unverified
similarly named package or follow a moving branch in production. `attach()`
starts no dashboard, proxy, port scan, update worker or separate process.
Standalone update checks do not auto-install by default; keep
`BOOSTER_AUTO_UPDATE=false` for reviewed deployments.

## FastAPI example

```python
import booster

engine = booster.attach(
    app,
    cache_policy=booster.CachePolicy(
        include_paths=("/static/css/", "/static/js/", "/static/fonts/"),
        exclude_paths=("/static/uploads/",),
    ),
    enable_minification=False,
    enable_compression=False,
    cache_ttl=300,
)
```

Register Booster before the application's security, host-validation, CORS and
compression middleware so those layers still execute on every cache hit. The
source response must explicitly declare `Cache-Control: public`. If an outer
security layer adds that declaration, apply the same shared cache-policy helper
at the static-file source too. Do not declare private pages public to force hits.

`include_paths=None` permits eligible routes; an empty tuple disables route
caching. A slash-ended prefix selects a subtree; other entries select an exact
path. Exclusions win. Cookies, authorization, session/user scope, range requests,
revalidation instructions, private/no-store/no-cache/no-transform responses,
varying responses and already encoded payloads bypass shared storage.

`compress_dynamic=True` is opt-in. It cannot store authenticated responses or
advertise private responses as public to a CDN. Leave it off for pages carrying
secrets and when another layer already owns compression.

## Correctness and operational limits

- Origin static max-age/s-maxage bounds the configured RAM TTL. Cache hits report
  Age; conditional hits retain origin cache/security headers.
- The cache is per process, bounded by items and a 64 MiB byte budget. Restarting
  clears it. Multiple workers do not share invalidation.
- Writes invalidate all cached reads before and after completion by default.
  Surgical invalidation is opt-in and unsafe when writes affect other paths.
- Public static bodies with Content-Length up to 2 MB can be assembled from
  chunks. Dynamic streams, file-send extensions and larger bodies pass through.
- Preserve asset query-version bumps when editing CSS/JS. For several workers,
  use content-versioned URLs and restart/invalidate deliberately on deployment.
- Existing privacy headers, upload checks and rate limits remain application
  responsibilities. Route policy is defense in depth, not authorization.

## Verification and performance review

Run `python -m pytest -q`, `python -m pip check` and the Node tests documented in
[COMMANDS.md](../COMMANDS.md). Tests cover normal RAM hits, credential isolation,
range bypass, encoded responses, freshness limits, bounded static chunks,
mutation invalidation and origin headers. Review code only for the active task;
[CODEMAP.md](../CODEMAP.md) locates the relevant units.

Measure cold and warm requests on the consuming app, confirm origin call counts
and identical decoded bytes, then check private routes and security headers.
Local RAM timings do not prove mobile network or production loading speed.
Report measured results and limitations; do not promise universal milliseconds,
zero bugs or fixed hosting savings.
