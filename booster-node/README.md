# booster-node

A zero-runtime-dependency cache and compression middleware for Express/Connect
style applications and native Node HTTP servers. Test your framework adapter
before rollout; Next.js and Fastify are not automatic drop-in integrations.

The canonical runtime is the TypeScript source in `src/*.ts`. The legacy
`src/*.js` files are unused mirrors kept for history; they are not built, not
tested and not published, so do not edit them.

## Safety and operation

- Cache only explicitly public GET responses. Cookies, credentials, host user
  scope, ranges and revalidation requests bypass shared storage on every path.
- Respect origin freshness, private/no-store/no-transform, encodings and variants.
  Replay origin security headers on hits and use Age and conditional validators.
- Bound resident body bytes (default 64 MiB) and entry count with monotonic TTL.
  Budgets apply per process and exclude runtime/metadata overhead.
- Preserve HTML/CSS and cached body bytes. The optional JSON minifier removes
  whitespace without rewriting numeric literals or string content.
- Avoid retaining streamed chunks. Clear before/after writes and reject captures
  from earlier mutation generations. Multiple workers still require coordination.

## Scaffold an adapter in your project

```bash
npx booster-node init --path . --include /static/css/ --exclude /media/ --config
```

The command writes `booster_plugin.ts` and, with `--config`, the matching
`booster.json` into your project. It never overwrites existing files unless
you pass `--force`.

```typescript
import express from "express";
import {buildMiddleware} from "./booster_plugin";

const app = express();
app.use(buildMiddleware());
```

## Measure and check the installation

```bash
npx booster-node measure https://your-site.example/static/app.css --requests 20
npx booster-node doctor
```

`measure` reports the status, the size, the cache headers, the p50/p95 timings
and whether the engine could store the response, using the engine's own rules.
`doctor` reports the runtime, the engine version and the running command.

## Route policy and declarative configuration

```typescript
import {booster} from "booster-node";

const middleware = booster({
  includePaths: ["/static/css/", "/static/js/"],
  excludePaths: ["/media/", "/api/"],
});
app.use(middleware);
```

The rules match the Python engine: an exclusion always wins, a prefix ending in
`/` selects a subtree, any other prefix selects that exact path, an omitted
`includePaths` allows every eligible route and an empty list selects nothing.

A hosting layer that adds `Vary: User-Agent` to immutable assets needs an
explicit decision. Only a site that proves the bytes are identical for every
user agent may pass `allowedVary: ["user-agent"]`.

One JSON file can describe the same site:

```json
{
  "includePaths": ["/static/css/"],
  "excludePaths": ["/media/"],
  "ttl": 300,
  "maxCacheBytes": 8388608,
  "compressDynamic": false
}
```

```typescript
import {booster, loadSiteConfig, optionsFrom} from "booster-node";

app.use(booster(optionsFrom(loadSiteConfig("booster.json"))));
```

An unknown key, a relative prefix or a non-positive limit is rejected with a
clear error instead of being ignored.

## Operator snapshot and shared invalidation

```typescript
import {booster, FileInvalidationBus} from "booster-node";

const middleware = booster({
  invalidationBus: new FileInvalidationBus("/var/run/booster/notices.log"),
});
app.use(middleware);

middleware.status();
// { version, cache: {items, bytes, maxItems, maxCacheBytes},
//   metrics: {totalRequests, cacheHits, cacheMisses, hitRatioPercent, bypassReasons},
//   configuration: {ttlSeconds, compressDynamic, maxCacheBytes, invalidation} }
```

`bypassReasons` counts why a response was not stored (`credentialed_request`,
`route_not_selected`, `response_not_public`, `request_directive`,
`method_not_read`, `streamed_response`, `body_too_large`). Only fixed reason
names are recorded: no cookie, token, path or payload.

The invalidation bus lets workers on one host apply each other's invalidation.
Every worker opens its own bus on the shared file, so one worker never consumes
another worker's notice. Without a bus the engine keeps its documented
process-local behaviour.

## TypeScript integration

Install a reviewed CI tarball in the consuming project. Development source and
tests are TypeScript; the tarball contains generated CommonJS and declarations,
so runtime consumers do not install TypeScript.

```typescript
import express from "express";
import {booster} from "booster-node";

const app = express();
app.use(booster({ttl: 60, maxCacheBytes: 8 * 1024 * 1024}));
app.get("/api/catalog", (_req, res) => {
  res.setHeader("Cache-Control", "public, max-age=60");
  res.json({catalog: ["public item"]});
});
```

Keep authorization, host validation and CORS outside the cache middleware.
Do not mark personalized responses public. Keep one compression owner.
Dynamic compression is opt-in; leave it off for pages carrying secrets.

## Development and verification

From the repository root, using Node 22.18+ (CI covers 22 and 24):

```bash
npm ci --prefix booster-node --ignore-scripts
npm run build --prefix booster-node
npm run check:types --prefix booster-node
node --test booster-node/test/test-ts.ts
```

The build creates ignored dist output from src/*.ts; package exports and generated
declarations point there. Legacy src/*.js files are not distributed or edited.
npm pack normally builds first; CI explicitly builds before packing with
--ignore-scripts. The same native test suite also runs against the installed
tarball using BOOSTER_NODE_ENTRY, so passing source tests cannot hide a different
packaged runtime.
