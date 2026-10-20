# Project State
Updated: 2026-10-20 13:15
## Done
- Phase 2 pilot inside this repository: `examples/host_app.py` (reference host with adapter, static-only route policy, outer security middleware), `examples/measure_host.py` (before/after measurement), `tests/test_host_conformance.py` (the documented checklist executed in CI).
- Conformance checklist verified against the reference host: 5/5 checks pass, and the check fails when the outer security middleware is removed.
- Measured on the reference host, 200 requests to a public asset: origin calls 200 without Booster versus 1 with it; warm p50 unchanged in-process (0.45 ms both) because the example origin is trivial. Recorded as a limitation, not a speed claim.
- Full Python suite after the change: 190 passed, 1 existing Starlette deprecation warning. Docs only for the engine itself.
- Phase 1 (previous commit e82d78d): `docs/PLUGIN_RECIPE.md`, `docs/CONFORMANCE_CHECKLIST.md`, `plans/PLUGIN_ROLLOUT_PLAN.md`, README and `docs/INTEGRATION.md` links.
## Pending
- Phase 2 host pilot on a real consuming project (the DMS FastAPI application) with measured before/after numbers; not started, needs its own approval.
- Shared invalidation between workers still unimplemented; exclude mutable cached routes until coordination is implemented and tested.
- Node/framework/HTTP full parity, physical-phone verification and operator bypass-reason reporting remain unproven.
- No `main` merge, production deployment or restart performed; those need a current explicit request.
## Next Step
- Apply the recipe to the DMS host project: one adapter file plus one registration line, then the conformance checklist and a before/after measurement. Phase 3 (shared config/adapters) only after two or more hosts need the same boilerplate.
