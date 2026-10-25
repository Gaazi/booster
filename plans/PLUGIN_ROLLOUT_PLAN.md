# Plugin rollout plan

Goal: let any host project embed Booster as a plugin with one adapter file, one
registration line and a repeatable proof, without changing the engine.

## Phase 1 — Recipe and proof (done)

- `docs/PLUGIN_RECIPE.md`: install a pinned commit, adapter template,
  registration order, route policy, one compression owner, worker limits,
  status/administration, verification, Django and Node notes.
- `docs/CONFORMANCE_CHECKLIST.md`: copy-paste test file with five checks
  (public hit, credential bypass, private route not stored, mutation
  invalidation, security headers on a cache hit) plus manual checks.
- Template executed against a real Starlette application: 5/5 checks pass; the
  security-header check fails when the outer middleware is removed.

Exit criteria: no engine change, no new public API, no new dependency.

## Phase 2 — Host pilot with measurements

- Apply the recipe in one host project (FastAPI application with server-rendered
  HTML, session cookies, CSRF tokens and a static mount).
- Cache only versioned static assets; keep the existing compression owner.
- Measure cold/warm p50/p95, origin call counts, payload sizes and RAM.

Exit criteria: conformance checks pass, measured before/after numbers recorded,
no private page in the cache.

## Phase 3 — Shared abstraction, only on demand

Introduce `booster/integrations/` and a declarative site config only when two
or more host projects need the same boilerplate.

- Config format must stay standard-library only (JSON; core supports 3.10).
- Optional adapters load lazily so core keeps zero runtime dependencies.
- Conformance checks must not pull pytest into a normal install.

Exit criteria: no change to existing behaviour, core import stays dependency
free, existing suites still pass.

## Not in scope now

Shared invalidation for multiple workers, Node parity completion, dashboard
refinements and production deployment. Each needs its own explicit request.

## Rules for every phase

Work on `dev`, one focused commit per unit, normal and edge regressions, update
`PROJECT_STATE.md`, commit and push immediately, never merge to `main` or
`demo`, and never deploy without an explicit request.
