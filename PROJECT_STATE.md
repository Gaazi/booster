# Project State
Updated: 2026-10-20 12:40
## Done
- Phase 1 of the plugin rollout: `docs/PLUGIN_RECIPE.md` (embed Booster as middleware in any host project: pinned install, adapter file, registration order, route policy, one compression owner, worker limits, status/admin, verification) and `docs/CONFORMANCE_CHECKLIST.md` (copy-paste test file with five privacy/correctness checks plus manual checks).
- Conformance template executed against a real Starlette app with Booster attached: 5/5 checks pass; the security-header check failed when the outer middleware was removed, so the checks detect real regressions.
- Docs only: no engine change, no new public API, no new dependency. README and `docs/INTEGRATION.md` link the new guides; `plans/PLUGIN_ROLLOUT_PLAN.md` records the phased plan.
- Pre-existing verified state unchanged: demo artifact `bbaa523`, dev at `8655226`, Python 185 tests and Node 31 tests last recorded green.
## Pending
- Phase 2 host pilot: apply the recipe in one FastAPI host (static-only policy, existing compression owner) and record measured cold/warm p50/p95, origin call counts, payload sizes and RAM.
- Shared invalidation between workers still unimplemented; exclude mutable cached routes until coordination is implemented and tested.
- Node/framework/HTTP full parity, physical-phone verification and operator bypass-reason reporting remain unproven.
- No `main` merge, production deployment or restart performed; those need a current explicit request.
## Next Step
- Run the Phase 2 pilot against the host FastAPI project: adapter file plus one registration line, then the conformance checklist and a before/after measurement. Phase 3 (shared config/adapters) only after two or more hosts need the same boilerplate.
