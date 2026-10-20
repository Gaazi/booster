# Project State
Updated: 2026-10-20 14:45
## Done
- Phase 1 (commit e82d78d): `docs/PLUGIN_RECIPE.md`, `docs/CONFORMANCE_CHECKLIST.md`, `plans/PLUGIN_ROLLOUT_PLAN.md`, README and `docs/INTEGRATION.md` links. The checklist was executed against a temporary Starlette app: 5/5 pass, and the security-header check fails when the outer middleware is removed.
- Phase 2 (commit cc48328): `examples/host_app.py`, `examples/measure_host.py` and `tests/test_host_conformance.py` (the checklist runs in CI). Python suite after the change: 190 passed.
- Phase 2 host pilot on a real consumer: the DMS FastAPI project embeds Booster as a plugin. The pilot found the real integration trap: a site that sets its browser cache policy in an outer middleware leaves the engine with no public policy, so the static mount must repeat it. DMS suite 319 passed, live dev site healthy. DMS commits 029f0bd1 and 1981d22d on `dev` only.
- Consumption path (commit cd1a4f6): `booster init` scaffolds a ready-to-edit `booster_plugin.py` into any host project; standard library only, never overwrites existing work. README, plugin recipe and integration guide show the GitHub install plus `booster init` flow. Suite 194 passed, CI green.
- Shared invalidation (opt-in): new `booster/invalidation.py` with `InvalidationBus`, `LocalInvalidationBus` and `FileInvalidationBus`. `RocketBooster` and `SpeedProxyServer` accept `invalidation_bus`, publish their own invalidation scope and apply peer notices before serving a request. The admin clear endpoint now reaches every worker. `get_status()` reports `shared` or `process`. Default behaviour is unchanged: no bus means the documented process-local boundary.
- Two real worker processes prove the peer returns the fresh body after the other worker wrote, and that the process-local behaviour stays identical without a bus (`tests/test_shared_invalidation.py`, 6 tests). Python suite: 200 passed.
## Pending
- The engine is not installed on any server. The DMS deploy kit runs git, rsync, migrate, restart and a health check but never `pip install`, so installing the pinned package needs one explicit operator action inside the cPanel virtualenv.
- The shared invalidation bus is proven on one host with two processes; it is not proven with a real load balancer, a network file system or a container restart.
- Node/framework/HTTP full parity, physical-phone verification and operator bypass-reason reporting remain unproven.
- Phase 3 shared abstraction (config-driven site policy, standard-library only) is deferred until two or more hosts need the same boilerplate.
- No `main` merge, production deployment or restart performed; those need a current explicit request.
## Next Step
- Continue the remaining plan: declarative site configuration, operator bypass reasons in the status snapshot, then the Node parity gaps.
