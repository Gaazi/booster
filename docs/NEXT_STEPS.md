# Handoff: reusable Booster improvements

## Completed on dev

The Python engine is defined once in `booster/`. Removed the retired duplicate
package, command, dashboard and imports. Source originals are recoverable in
ignored `.trash/`; Git history was preserved. Management requests now use
`X-Booster-Admin` consistently in the dashboard, launcher documentation and tests.

Implemented reusable CachePolicy, request/response privacy checks, freshness
limits, bounded static-file buffering and duplicate-attachment detection.
Private optimization no longer sets public CDN cache headers. Encoded responses
and no-transform instructions are respected. Update checks are read-only unless
the operator explicitly opts in. Full integration guidance is in
[INTEGRATION.md](INTEGRATION.md); engine locations are in [CODEMAP.md](../CODEMAP.md).

The plugin path is complete on both engines. `docs/PLUGIN_RECIPE.md` holds the
copy-ready recipe, `docs/CONFORMANCE_CHECKLIST.md` holds the copy-paste privacy
and correctness tests, `booster init` and `npx booster-node init` scaffold the
adapter plus the JSON site configuration, and `booster/site_config.py` reads
that configuration with fail-fast validation.

Shared invalidation is implemented and opt-in: `booster/invalidation.py`
publishes each worker's invalidation scope through a file-backed bus, so peers
on one host apply it before serving their next request. Without a bus the
documented process-local behaviour is unchanged. Two real worker processes prove
it (`tests/test_shared_invalidation.py`).

Operator visibility is in place: `metrics["bypass_reasons"]` counts why a
response was not stored using fixed reason names only, with no cookie, token,
path or payload recorded. The Node engine matches the Python one on route
policy, JSON site configuration, status snapshot, bypass reasons and the
invalidation bus.

Core/server packaging is now separated with lazy optional exports. CI builds
compressed wheel/source/Node packages after tests and verifies installation;
see [BUILDS.md](BUILDS.md). Workload-specific guidance and research are in
[USE_CASES.md](USE_CASES.md). Runtime/production performance remains to be measured.

## Next work, in priority order

Primary product priority: the personalized invitation delivered to a guest must
open quickly while retaining its full styles, music and animations. Prefer
improving asset delivery and measured server work over dashboard refinements.
Never use shared caching of personalized card HTML or remove visual features to
claim speed. Invite's consuming integration is on dev at `a7aa413`; its short
agent reference and `docs/10-booster-verification.md` document the actual adapter
and local measurements. Live/physical-phone performance is still unverified.

1. **Consuming website:** pin the reviewed Booster commit, select only public
   asset routes, retain outer security/host/CORS middleware and one compression
   owner. Test private pages, ranges, signed uploads, cache hits and decoded bytes.
   Never copy the engine or mark private pages public to improve hit counts.
2. **Lightweight distribution:** optional `server`, `cdn` and `brotli` extras and
   lazy top-level exports are implemented. Maintain core-only import/install
   and standalone package regressions when extending public APIs.
   Per-host `max_cache_bytes` is already available; Invite uses an 8 MiB cap.
   The deploy kit never runs `pip install`, so a pinned dependency only reaches
   a server when an operator installs it inside the virtualenv.
3. **Node parity:** the Node engine now matches the Python engine on route
   policy, site configuration, status snapshot, bypass reasons and shared
   invalidation. 47 native regressions run against canonical TS and the
   installed generated package. Remaining limits: no Node release is published
   to a registry yet, and framework adapters (Next.js, Fastify) are still
   host-owned.
4. **Real performance:** record cold/warm p50/p95, origin file reads, CPU, memory
   and payload size on each target website. Benchmark with and without Booster,
   then test on a physical phone. Avoid speculative speed or cost guarantees.
5. **Multiple workers:** the shared bus closes the stale window for workers on
   one host. Still unproven with a real load balancer, a network file system or
   a container restart. Until then keep mutable routes out of the cache and
   count the RAM budget per worker.
6. **Operator usability:** the status snapshot now explains why a response was
   not stored. Any dashboard placement or style change needs an approved mockup,
   and the dashboard must stay optional and local.

Work on dev only. Keep changes focused, add normal/edge regressions, update state,
commit and push each completed unit. Production rollout and branch promotion
require the user's current explicit request.
