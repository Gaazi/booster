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

## Next work, in priority order

1. **Consuming website:** pin the reviewed Booster commit, select only public
   asset routes, retain outer security/host/CORS middleware and one compression
   owner. Test private pages, ranges, signed uploads, cache hits and decoded bytes.
   Never copy the engine or mark private pages public to improve hit counts.
2. **Lightweight distribution:** move standalone server/dashboard dependencies
   into an optional `server` extra, with lazy top-level exports. Preserve current
   public APIs. Verify that core attachment installs and imports without FastAPI,
   Uvicorn or HTTPX when the host supplies its ASGI framework. Test standalone
   installation separately; do not merely remove dependencies required on import.
3. **Node parity:** independently audit Node cache admission, encoded bodies,
   credential/range bypass, Vary and TTL semantics against the Python privacy
   regressions. Current Node tests pass, but passing seven tests is not a full
   security review or evidence of identical policies.
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
