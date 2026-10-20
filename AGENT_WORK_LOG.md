# Agent Work Log

## 2026-10-20 — Plugin rollout phase 1 (docs + verified conformance template)

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (Phase 1 of `plans/PLUGIN_ROLLOUT_PLAN.md`), not a full-project review.
- Done: added `docs/PLUGIN_RECIPE.md` and `docs/CONFORMANCE_CHECKLIST.md`; linked them from `README.md` and `docs/INTEGRATION.md`; added `plans/PLUGIN_ROLLOUT_PLAN.md`; replaced `PROJECT_STATE.md`.
- Checks: conformance template executed against a temporary Starlette application outside the repository - 5/5 passed; removing the outer security middleware made the security-header check fail, confirming the check is sensitive. No engine file changed, so the recorded Python 185 / Node 31 suites were not re-run.
- Pending: Phase 2 host pilot with before/after measurements; shared invalidation between workers; Node parity; physical-phone verification.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-20 — Plugin rollout phase 2 (reference host + measurement)

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (Phase 2 of `plans/PLUGIN_ROLLOUT_PLAN.md`), not a full-project review.
- Done: added `examples/host_app.py`, `examples/measure_host.py`, `examples/__init__.py` and `tests/test_host_conformance.py`; linked the reference implementation from `docs/PLUGIN_RECIPE.md` and `docs/CONFORMANCE_CHECKLIST.md`; replaced `PROJECT_STATE.md`.
- Checks: `python -m pytest -q` -> 190 passed, 1 existing Starlette deprecation warning. `python -m examples.measure_host` -> 200 requests to a public asset gave 200 origin calls without Booster and 1 with it; warm p50 0.45 ms in both cases because the example origin is trivial, so no speed claim is made.
- Engine files unchanged; no new public API, no new runtime dependency, no configuration format decision taken.
- Pending: real consuming-project pilot (DMS) with its own approval; shared invalidation between workers; Node parity; physical-phone verification.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.
