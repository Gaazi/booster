# booster-node

A zero-runtime-dependency cache and compression middleware for Express/Connect
style applications and native Node HTTP servers. Test your framework adapter
before rollout; Next.js and Fastify are not automatic drop-in integrations.

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
