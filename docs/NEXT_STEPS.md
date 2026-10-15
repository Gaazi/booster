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
3. **Node parity:** the recent review fixed credential/static isolation, origin
   freshness, header/byte integrity, HEAD poisoning and mutation races. All 31
   native regressions run against canonical TS and the installed generated
   package. See REVIEW_2026-10-15.md; complete framework/HTTP parity is not proven.
4. **Real performance:** record cold/warm p50/p95, origin file reads, CPU, memory
   and payload size on each target website. Benchmark with and without Booster,
   then test on a physical phone. Avoid speculative speed or cost guarantees.
5. **Multiple workers:** plan shared invalidation only when measured workloads
   require it. Today each process has an independent RAM cache. Version asset
   URLs and document coordinated invalidation/restarts before deployment.
6. **Operator usability:** expose cache bypass reasons and a small health summary
   without logging tokens, names or full private URLs. Keep the dashboard optional
   and local. Any dashboard placement/style change needs an approved mockup.

Work on dev only. Keep changes focused, add normal/edge regressions, update state,
commit and push each completed unit. Production rollout and branch promotion
require the user's current explicit request.
