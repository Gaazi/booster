# Project State
Updated: 2026-10-20 14:10
## Done
- Phase 1 (commit e82d78d): `docs/PLUGIN_RECIPE.md`, `docs/CONFORMANCE_CHECKLIST.md`, `plans/PLUGIN_ROLLOUT_PLAN.md`, README and `docs/INTEGRATION.md` links. The checklist was executed against a temporary Starlette app: 5/5 pass, and the security-header check fails when the outer middleware is removed.
- Phase 2 (commit cc48328): `examples/host_app.py`, `examples/measure_host.py` and `tests/test_host_conformance.py` (the checklist runs in CI). Python suite after the change: 190 passed, 1 existing Starlette deprecation warning.
- Phase 2 host pilot on a real consumer: the DMS FastAPI project embeds Booster as a plugin (`app/core/booster_plugin.py`, static-only policy, engine exposed on `app.state`). The pilot found the real integration trap: the site sets its browser cache policy in an outer middleware, so the engine must repeat that policy at the static mount to see it; client-visible headers stay unchanged. DMS suite 319 passed, 6 new tests, live dev site healthy. DMS commits 029f0bd1 and 1981d22d on `dev` only.
- `booster init` command: scaffolds a ready-to-edit `booster_plugin.py` into any host project (`--include`, `--exclude`, `--path`, `--force`), never overwrites existing work. New module `booster/initializer.py` uses only the standard library, so core stays dependency free. Covered by `tests/test_initializer.py` (4 tests).
- Consumption path documented in the README: install the reviewed revision from GitHub, run `booster init`, register the adapter before the other middleware, then run the conformance checklist. Node install from GitHub documented too.
- Python suite after the new command: 194 passed, 1 existing Starlette deprecation warning.
- Engine behaviour unchanged throughout: no change to caching, privacy or compression rules.
## Pending
- The engine is not installed on any server. The DMS deploy kit runs git, rsync, migrate, restart and a health check but never `pip install`, so installing the pinned package needs one explicit operator action inside the cPanel virtualenv.
- Shared invalidation between workers still unimplemented; exclude mutable cached routes until coordination is implemented and tested.
- Node/framework/HTTP full parity, physical-phone verification and operator bypass-reason reporting remain unproven.
- Phase 3 shared abstraction (config-driven site policy, standard-library only) is deferred until two or more hosts need the same boilerplate.
- No `main` merge, production deployment or restart performed; those need a current explicit request.
## Next Step
- Confirm the `booster init` path with one more independent host project, then decide whether Phase 3 (declarative site config) is justified by real demand.
