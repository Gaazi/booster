# Project State
Updated: 2026-10-20 13:40
## Done
- Phase 1 (commit e82d78d): `docs/PLUGIN_RECIPE.md`, `docs/CONFORMANCE_CHECKLIST.md`, `plans/PLUGIN_ROLLOUT_PLAN.md`, README and `docs/INTEGRATION.md` links. The checklist was executed against a temporary Starlette app: 5/5 pass, and the security-header check fails when the outer middleware is removed.
- Phase 2 (commit cc48328): `examples/host_app.py`, `examples/measure_host.py` and `tests/test_host_conformance.py` (the checklist runs in CI). Python suite after the change: 190 passed, 1 existing Starlette deprecation warning. Reference measurement: 200 requests to a public asset gave 200 origin calls without Booster and 1 with it; warm p50 unchanged in-process because the example origin is trivial, so no speed claim is made.
- Phase 2 host pilot on a real consumer: the DMS FastAPI project now embeds Booster as a plugin (`app/core/booster_plugin.py`, static-only policy, engine exposed on `app.state`). The pilot found the real integration trap: the site sets its browser cache policy in an outer middleware, so the engine must repeat that policy at the static mount to see it; client-visible headers stay unchanged. DMS suite 319 passed, 6 new tests, live dev site healthy.
- Engine files unchanged throughout: no new public API, no new runtime dependency, no configuration format decided.
## Pending
- The engine is not installed on any server yet. The DMS deploy kit runs git, rsync, migrate, restart and a health check but never `pip install`, so installing the pinned package needs one explicit operator action inside the cPanel virtualenv.
- Shared invalidation between workers still unimplemented; exclude mutable cached routes until coordination is implemented and tested.
- Node/framework/HTTP full parity, physical-phone verification and operator bypass-reason reporting remain unproven.
- Phase 3 shared abstraction (config-driven site policy, standard-library only) is deferred until two or more hosts need the same boilerplate.
- No `main` merge, production deployment or restart performed; those need a current explicit request.
## Next Step
- With explicit approval, install the pinned Booster package in the DMS server virtualenv, deploy, and record live before/after numbers for the static asset path.
