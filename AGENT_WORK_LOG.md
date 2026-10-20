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

## 2026-10-20 — Plugin rollout phase 2b (real host pilot on DMS)

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (Phase 2 of `plans/PLUGIN_ROLLOUT_PLAN.md`), not a full-project review.
- Done: applied the recipe to the DMS FastAPI project in its own repository - adapter file, static-only route policy, engine handle on `app.state`, six regression tests, pinned dependency in `pyproject.toml`/`uv.lock`/`requirements.txt`. DMS commits 029f0bd1 and 1981d22d, pushed to `dev` only.
- Checks: DMS suite 319 passed; new plugin tests 6 passed; real application check reported 1 miss and 50 hits (98 percent hit ratio), warm p50 about 0.60 ms, browser-visible cache headers unchanged; live dev site health 200 before and after the deploys.
- Findings worth keeping: the site sets its browser cache policy in an outer middleware, so the engine sees no public policy and stores nothing until the static mount repeats it; Starlette reports the mounted path in `scope["path"]` with `root_path` set separately; the deploy kit never runs `pip install`, so a pushed dependency does not reach the server by itself.
- Pending: server-side install (operator action), live measurement, shared invalidation between workers, Node parity, physical-phone verification.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-20 — Remaining plan: shared invalidation, site config, operator visibility, Node parity

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (the four remaining plan items), not a full-project review.
- Done, four focused commits on `dev`: `724e060` shared invalidation bus for the Python engine, `72e0a53` declarative JSON site configuration, `cb35078` bypass reason counters, and the Node parity commit with `bypass.ts`, `status.ts` and `invalidation.ts`.
- Checks: Python suite 216 passed, 1 existing Starlette deprecation warning; Node suite 36 passed (was 31); TypeScript build and strict type check pass; `CODEMAP.md` regenerated with `refresh_docs.py`; relative doc links resolve.
- Findings worth keeping: Node's strip-only TypeScript mode rejects constructor parameter properties, so the file bus stores its fields explicitly; two engines must open their own bus instance on the shared file, because one shared reader position would let one worker consume the other worker's notice.
- Pending: server-side install (operator action), physical-phone and network measurement, Node declarative configuration, no `main` merge and no deployment.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-20 — Consumption path: `booster init` scaffolding command

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (consumption path for host projects), not a full-project review.
- Done: added `booster/initializer.py` and the `booster init` command that writes a ready-to-edit `booster_plugin.py` into any host project; documented the GitHub install plus `booster init` flow in the README, `docs/PLUGIN_RECIPE.md` and `docs/INTEGRATION.md`; recorded the outcome in `PROJECT_STATE.md`.
- Checks: `python -m pytest -q` -> 194 passed, 1 existing Starlette deprecation warning; `tests/test_initializer.py` -> 4 passed, including a real `python -m booster.cli init` run; generated adapter compiles, exposes `attach_booster` and refuses to overwrite an existing file.
- Constraints kept: the new module uses only the standard library, so core stays dependency free and the standalone server path is unchanged; no engine behaviour change.
- Pending: shared invalidation between workers, Node parity, physical-phone verification, server-side install (operator action).
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.
