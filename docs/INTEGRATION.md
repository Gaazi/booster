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

## Plugin recipe

[PLUGIN_RECIPE.md](PLUGIN_RECIPE.md) is the step-by-step recipe for embedding
Booster as middleware inside a host project: adapter file, registration order,
route policy, one compression owner, worker limits and rollout verification.
The installed command `booster init --path . --include /static/` writes the
adapter file into the host project.
[CONFORMANCE_CHECKLIST.md](CONFORMANCE_CHECKLIST.md) is the copy-paste test file
each host project runs to prove that private data never enters the shared cache.

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

The default installation contains the core cache/compression engine without
server dependencies. The host provides its own ASGI/Django framework. Optional
extras are `server` (standalone dashboard/proxy and HTTP client), `cdn` (HTTP
client for CDN integration), and `brotli` (optional codec). Core GZip uses the
standard library; without Brotli, compatible requests can still use GZip.
Core supports Python 3.10+. The current standalone/server extra requires Python
3.11+ through its Starlette dependency; use a matching interpreter for that extra.
For a pinned standalone installation, use:

```text
booster[server,brotli] @ git+https://github.com/Gaazi/booster.git@FULL_REVIEWED_COMMIT
```

Existing top-level optional API names load lazily; requesting the proxy/CDN
without its dependencies gives an installation hint. The plugin launcher
installs its own required extras. See [compressed builds](BUILDS.md) for
verified wheel/Node downloads and [use cases](USE_CASES.md) for choosing scope.

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
    max_cache_bytes=8 * 1024 * 1024,
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

## Embed in the owner's existing dashboard

Use `engine.get_status()` for the shared version, configuration, cache memory
and processed-response counters. It exposes no cache keys, payloads or request
logs. The host website must authorize an administrator before reading this
snapshot or calling `engine.cache.clear()`. Keep both actions under its existing
owner dashboard, and apply the host's private/no-store and CSRF/origin policies.
Do not mount the standalone dashboard or proxy on the public website.

Counters describe responses processed by Booster, not browser page-load times.
Resident memory includes entries awaiting lazy expiry. With external compression
disabled in Booster, its bandwidth-savings counter is not the host GZip savings.
Cache clearing retains lifetime counters. A multi-worker dashboard samples only
the serving process; it is not a fleet-wide cache purge or aggregate report.

## Correctness and operational limits

- Origin static max-age/s-maxage bounds the configured RAM TTL. Cache hits report
  Age; conditional hits retain origin cache/security headers.
- The cache is per process, bounded by items and a configurable byte budget
  (`max_cache_bytes`, default 64 MiB). Restarting
  clears it. Multiple workers do not share invalidation.
- Writes invalidate all cached reads before and after completion by default.
  Surgical invalidation is opt-in and unsafe when writes affect other paths.
- Public static bodies with Content-Length up to 2 MB can be assembled from
  chunks. Dynamic streams, file-send extensions and larger bodies pass through.
- Preserve asset query-version bumps when editing CSS/JS. For several workers,
  use content-versioned URLs and restart/invalidate deliberately on deployment.
- Existing privacy headers, upload checks and rate limits remain application
  responsibilities. Route policy is defense in depth, not authorization.

### Multiple workers: choose a freshness strategy

Each worker owns its own RAM cache. A mutation or authorized dashboard clear
invalidates only the worker that handles it. Repeated requests to a load-balanced
clear endpoint do not guarantee that every worker has received the request.
The Python two-process regression in `tests/test_workers.py` verifies this
boundary, credential bypass on a stale peer, and recovery after clearing both
workers explicitly. It also verifies static-only route selection across workers.

**Shared invalidation (opt-in).** When the workers run on the same host, pass
one shared notice file so every worker applies the invalidation before it
serves the next request:

```python
from booster import FileInvalidationBus

engine = booster.attach(app, invalidation_bus=FileInvalidationBus("/var/run/booster/notices.log"))
```

The worker that handled the write publishes the notice; every other worker
applies it on its next request. The file is truncated when it grows past its
size limit, and a reader that notices the truncation applies a full clear,
because that is the only safe reading of a lost notice. The bus is best
effort: a worker that never receives a request keeps its old entries until
they expire. `tests/test_shared_invalidation.py` runs two real processes and
proves the peer returns the fresh body after the other worker wrote, and that
the documented process-local behaviour is unchanged when no bus is configured.
`engine.get_status()["configuration"]["invalidation"]` reports `shared` or
`process`.

For the lightest deployment, use the static-only `CachePolicy` example above.
Exclude mutable catalog, price, stock, account and live-status routes even when
their origin declares them public. Use content-versioned asset URLs and retain
the old asset bytes while old pages reference them. Each worker can then warm
the new asset URL independently; no shared invalidation service is needed for
those immutable files. This does not coordinate caches in browsers or a CDN.

If mutable public responses must be cached across workers, the host needs an
authenticated coordination mechanism that invalidates every worker and handles
in-flight reads. Booster does not currently provide that mechanism. Until it is
implemented and tested, exclude those routes from RAM caching. A short TTL
bounds retention but does not guarantee immediate freshness after a write.
Application `no-store` responses and credentialed requests continue to bypass
storage; changing the route policy does not replace authorization.

Budget RAM per worker: four engines with the default 64 MiB cache budget can
retain up to 256 MiB of counted entries, plus process and other memory overhead.
The budget is not a whole-application RSS limit. Measure the actual worker count
and workload before adding a shared backend or raising cache limits.

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
