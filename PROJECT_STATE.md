# Project State
Updated: 2026-10-20 15:40
## Done
- Phase 1 (e82d78d) plugin recipe and conformance checklist; Phase 2 (cc48328) reference host that runs the checklist in CI; DMS host pilot (DMS commits 029f0bd1, 1981d22d on `dev` only) with 319 passing tests and a healthy live dev site.
- Consumption path (cd1a4f6): `booster init` scaffolds a ready-to-edit `booster_plugin.py` into any host project, never overwrites existing work, standard library only.
- Shared invalidation (724e060): `booster/invalidation.py` with the bus protocol, a local no-op and a file-backed bus for workers on one host. `RocketBooster` and `SpeedProxyServer` accept `invalidation_bus`, publish their own invalidation scope and apply peer notices before serving; the admin clear now reaches every worker; `get_status()` reports `shared` or `process`. Two real worker processes prove the peer returns fresh bytes after the other worker wrote, and the process-local behaviour is unchanged without a bus.
- Declarative site configuration (72e0a53): `booster/site_config.py` reads one JSON file into a `SiteConfig`, rejects unknown keys, relative prefixes and non-positive limits, and `booster init --config` writes the matching `booster.json` that the generated adapter prefers.
- Operator visibility (cb35078): `booster/bypass.py` counts fixed reason names for every response that was not stored; `metrics["bypass_reasons"]` explains a route without recording any cookie, token, path or payload.
- Node parity: the Node engine gained the same features - `bypass.ts` reason counters, `status.ts` operator snapshot with `middleware.status()`, `invalidation.ts` file bus, and request/response reason recording. Node suite 36 passed (was 31), TypeScript build and strict type check pass.
- Python suite 216 passed, 1 existing Starlette deprecation warning. `CODEMAP.md` regenerated with `refresh_docs.py`.
## Pending
- The engine is not installed on any server. The DMS deploy kit runs git, rsync, migrate, restart and a health check but never `pip install`, so installing the pinned package needs one explicit operator action inside the cPanel virtualenv.
- The shared invalidation bus is proven with two local processes and two Node engines on one host; it is not proven with a real load balancer, a network file system or a container restart.
- Physical-phone verification and a measured public-network comparison are still missing; only in-process numbers exist.
- Node still has no declarative JSON site configuration like the Python engine; its options object covers the same settings.
- No `main` merge, production deployment or restart performed; those need a current explicit request.
## Next Step
- Confirm the whole consumption path with one more independent host project, then run the conformance checklist and a measured comparison on a real device and network before any rollout.
