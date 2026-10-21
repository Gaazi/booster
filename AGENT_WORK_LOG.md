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

## 2026-10-20 — Node route policy and JSON site configuration

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (closing the last Node parity gap), not a full-project review.
- Done: added `routeAllowed` to the Node policy module with the same matching rules as the Python `CachePolicy`, wired `includePaths`/`excludePaths` into the Node middleware, and added `site-config.ts` for the same JSON configuration with the same validation. Node suite 41 passed.
- Checks: Node suite 41 passed; TypeScript build and strict type check pass; Python suite 216 passed; `CODEMAP.md` regenerated.
- Finding worth keeping: the Node engine had no route policy at all, so every eligible public route was cached regardless of the site's rules; the Python engine already had `CachePolicy`.
- Pending: server-side install (operator action), physical-phone and network measurement, no `main` merge and no deployment.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-21 — Node scaffolding command

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (Node consumption path parity), not a full-project review.
- Done: added `booster-node/src/initializer.ts` and `booster-node/src/cli.ts` with a `bin` entry, so `npx booster-node init` writes `booster_plugin.ts` and the matching `booster.json` into a host project; README for both engines now shows the command flow.
- Checks: Node suite 47 passed; TypeScript build and strict type check pass; the compiled `dist/cli.js` was run and created both files; Python suite 216 passed; `CODEMAP.md` regenerated.
- Findings worth keeping: the package builds to CommonJS, so `import.meta` is not allowed in the CLI source; the entry check now matches the script name instead, which works for both the TypeScript source and the compiled file.
- Pending: server-side install (operator action), physical-phone and network measurement, no `main` merge and no deployment.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-21 — Documentation of record updated

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (documentation only), not a full-project review.
- Done: added the shared invalidation, declarative site configuration and bypass reason sections to `docs/FEATURES_AND_ARCHITECTURE.md`, corrected its install and verification steps, updated the module map and doc index, refreshed the multi-worker guidance in `docs/USE_CASES.md`, and rewrote `docs/NEXT_STEPS.md` so the handoff matches the current state.
- Checks: Python suite 216 passed; Node suite 47 passed; all relative documentation links resolve.
- Pending: server-side install (operator action), physical-phone and network measurement, no `main` merge and no deployment.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-21 — Django example and stack-specific conformance checklists

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (proof path for the Django and Node stacks), not a full-project review.
- Done: added `examples/django_host.py` with a regression test, and extended `docs/CONFORMANCE_CHECKLIST.md` with a Django (WSGI) variant and a Node.js variant next to the ASGI one, so every supported stack has a copy-paste proof.
- Checks: Python suite 218 passed (2 new Django example tests); Node suite 47 passed; `CODEMAP.md` regenerated.
- Note worth keeping: Django has no route policy, so a Django site opts in per response by declaring `Cache-Control: public`; the checklist variant proves that only such views are cached.
- Pending: server-side install (operator action), physical-phone and network measurement, no `main` merge and no deployment.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-21 — Published artifact proof in CI

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (build verification), not a full-project review.
- Done: the verified-build job now runs the installed command from the built wheel and from the installed Node tarball and checks that the scaffolded adapter and configuration files appear in a scratch host project.
- Checks: both flows executed locally before the change - the wheel was installed into a fresh virtualenv and `booster init` produced `booster_plugin.py` and `booster.json`; the tarball was installed with npm and `dist/cli.js init` produced `booster_plugin.ts` and `booster.json`; the workflow YAML parses.
- Pending: server-side install (operator action), physical-phone and network measurement, no `main` merge and no deployment.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-21 — Measurement command and the Vary allow list

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (measurement and the caching gap it revealed), not a full-project review.
- Done: added `booster/measurement.py` and the `booster measure` command, which reports status, size, cache headers, p50/p95 timings and the engine's own cacheability verdict for a live URL. Added the opt-in `allowed_vary` option to the Python engine, the Django middleware, the standalone proxy and the Node engine, with the default left closed.
- Checks: Python suite 226 passed (3 new tests); Node suite 48 passed (1 new test); TypeScript build and strict type check pass; the command was run against the live DMS dev site and reported `public, max-age=31536000, immutable` with a `response_not_public` verdict.
- Finding worth keeping: the LiteSpeed layer adds `Vary: User-Agent` to static files, so the engine refused to store them and the live site cached nothing; the bytes and validator were proven identical for four different user agents, which is the evidence a host needs before allowing that field.
- Second finding worth keeping: after the deploy, `pip` did not install the new commit because the package version was unchanged - it treated the installed distribution as already satisfied and the site kept the older engine code. The fix is a version bump with every engine change, now recorded in `docs/INTEGRATION.md`.
- Third finding worth keeping: the upstream LiteSpeed layer sends `Age: 81`, so the engine refused to store the asset even after the Vary fix. The engine now stores an aged response while its remaining freshness is positive and reports the origin age plus the time in the cache, which matches the RFC 9111 age model the Node engine already used.
- Pending: enable the allow list in the DMS adapter and verify the live dev site caches, server-side install (operator action), physical-phone and network measurement, no `main` merge and no deployment.
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.

## 2026-10-20 — Consumption path: `booster init` scaffolding command

- Agent/model: OpenCode (MiniMax M3.1 Flash Free)
- Scope reviewed: focused (consumption path for host projects), not a full-project review.
- Done: added `booster/initializer.py` and the `booster init` command that writes a ready-to-edit `booster_plugin.py` into any host project; documented the GitHub install plus `booster init` flow in the README, `docs/PLUGIN_RECIPE.md` and `docs/INTEGRATION.md`; recorded the outcome in `PROJECT_STATE.md`.
- Checks: `python -m pytest -q` -> 194 passed, 1 existing Starlette deprecation warning; `tests/test_initializer.py` -> 4 passed, including a real `python -m booster.cli init` run; generated adapter compiles, exposes `attach_booster` and refuses to overwrite an existing file.
- Constraints kept: the new module uses only the standard library, so core stays dependency free and the standalone server path is unchanged; no engine behaviour change.
- Pending: shared invalidation between workers, Node parity, physical-phone verification, server-side install (operator action).
- Commits: see `git log` on `dev`. Branch policy: `dev` only, no `main`/`demo` merge, no deployment.
