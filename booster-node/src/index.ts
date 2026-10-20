/** TypeScript-owned Express/Connect middleware with conservative public caching. */
import { FastMemoryCache, CacheEntry } from "./cache.ts";
import { ResponseCompressor } from "./compressor.ts";
import { FastMinifier } from "./minifier.ts";
import { requestAllowed, responseBlocksCache } from "./policy.ts";
import { interceptResponse, serveCached } from "./response.ts";
import { guardExplicitHeaders } from "./header-guard.ts";
import { BypassTracker, REASONS } from "./bypass.ts";
import { FULL_CLEAR, LocalInvalidationBus } from "./invalidation.ts";
import { buildStatus } from "./status.ts";
import type { StatusSnapshot } from "./status.ts";
import type { BoosterOptions, BoosterMiddleware, EngineState, ResponseContext } from "./engine-types.ts";
export type { BoosterOptions, BoosterMiddleware, NextFunction } from "./engine-types.ts";
export type { CompressionResult } from "./compressor.ts";
export { BypassTracker, REASONS } from "./bypass.ts";
export { FileInvalidationBus, LocalInvalidationBus, FULL_CLEAR } from "./invalidation.ts";
export type { InvalidationBus } from "./invalidation.ts";
export { buildStatus } from "./status.ts";
export type { StatusSnapshot } from "./status.ts";

export const STATIC_EXTENSIONS: string[] = [
  ".css", ".js", ".mjs", ".woff", ".woff2", ".ttf", ".eot", ".otf",
  ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".map"
];

/** Classify assets for callers; extensions never override credential privacy. */
export function isStaticAsset(path: string): boolean {
  const clean = (path || "").split("?")[0].toLowerCase();
  return ["/static/", "/assets/", "/public/"].some(prefix => clean.startsWith(prefix))
    || STATIC_EXTENSIONS.some(extension => clean.endsWith(extension));
}

/** Clear before/after mutations and invalidate older in-flight capture contexts. */
function trackMutation(engine: EngineState, ctx: ResponseContext): void {
  const invalidate = (): void => {
    engine.generation++;
    engine.cache.clear();
    engine.bus.publish(FULL_CLEAR);
  };
  invalidate();
  ctx.res.once("finish", invalidate);
  ctx.res.once("close", invalidate);
}

/** Apply the invalidation notices published by the other workers. */
function applyPendingInvalidations(engine: EngineState): void {
  for (const notice of engine.bus.drain()) {
    if (notice === FULL_CLEAR) engine.cache.clear();
    else engine.cache.invalidatePrefix(notice);
  }
}

/** Record why this request may not use the shared cache. */
function bypassReason(ctx: ResponseContext): string | null {
  const {req} = ctx;
  if (req.user !== undefined || req.session !== undefined || req.auth !== undefined) return REASONS.PERSONALIZED;
  if ("cookie" in req.headers || "authorization" in req.headers) return REASONS.CREDENTIALS;
  if (!requestAllowed(req)) return REASONS.REQUEST_DIRECTIVE;
  return null;
}

/** Construct one bounded engine while preserving the existing middleware API. */
export function booster(options: BoosterOptions = {}): BoosterMiddleware {
  const bus = options.invalidationBus ?? new LocalInvalidationBus();
  const engine: EngineState = {
    cache: new FastMemoryCache(options.maxItems ?? 2000, options.ttl ?? 300, options.maxCacheBytes),
    compressor: new ResponseCompressor(options.minCompressSize ?? 512), options, generation: 0,
    bus, sharedInvalidation: options.invalidationBus !== undefined,
    bypass: new BypassTracker(), counters: { totalRequests: 0, cacheHits: 0, cacheMisses: 0 },
  };
  const middleware = ((req, res, next): void => {
    const url = req.originalUrl || req.url || "/";
    applyPendingInvalidations(engine);
    engine.counters.totalRequests++;
    const ctx: ResponseContext = {
      engine, req, res, path: url.split("?")[0], generation: engine.generation,
      key: JSON.stringify([req.headers.host || "", url]), eligible: requestAllowed(req) && !responseBlocksCache(res),
    };
    if (req.method !== "GET") guardExplicitHeaders(res);
    if (["POST", "PUT", "PATCH", "DELETE"].includes(req.method || "")) {
      engine.bypass.record(REASONS.METHOD);
      trackMutation(engine, ctx); next(); return;
    }
    if (!["GET", "HEAD"].includes(req.method || "")) {
      engine.bypass.record(REASONS.METHOD);
      next(); return;
    }
    const reason = bypassReason(ctx);
    if (reason) engine.bypass.record(reason);
    const cached = ctx.eligible ? engine.cache.get(ctx.key) : null;
    if (cached) {
      engine.counters.cacheHits++;
      serveCached(ctx, cached);
      return;
    }
    engine.counters.cacheMisses++;
    if (req.method === "GET") interceptResponse(ctx);
    next();
  }) as BoosterMiddleware;
  middleware.status = (): StatusSnapshot => buildStatus(engine);
  return middleware;
}

export { FastMemoryCache, CacheEntry, ResponseCompressor, FastMinifier };
