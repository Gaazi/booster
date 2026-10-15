/** TypeScript-owned Express/Connect middleware with conservative public caching. */
import { FastMemoryCache, CacheEntry } from "./cache.ts";
import { ResponseCompressor } from "./compressor.ts";
import { FastMinifier } from "./minifier.ts";
import { requestAllowed, responseBlocksCache } from "./policy.ts";
import { interceptResponse, serveCached } from "./response.ts";
import { guardExplicitHeaders } from "./header-guard.ts";
import type { BoosterOptions, BoosterMiddleware, EngineState, ResponseContext } from "./engine-types.ts";
export type { BoosterOptions, BoosterMiddleware, NextFunction } from "./engine-types.ts";
export type { CompressionResult } from "./compressor.ts";

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
  const invalidate = (): void => { engine.generation++; engine.cache.clear(); };
  invalidate();
  ctx.res.once("finish", invalidate);
  ctx.res.once("close", invalidate);
}

/** Construct one bounded engine while preserving the existing middleware API. */
export function booster(options: BoosterOptions = {}): BoosterMiddleware {
  const engine: EngineState = {
    cache: new FastMemoryCache(options.maxItems ?? 2000, options.ttl ?? 300, options.maxCacheBytes),
    compressor: new ResponseCompressor(options.minCompressSize ?? 512), options, generation: 0,
  };
  return (req, res, next): void => {
    const url = req.originalUrl || req.url || "/";
    const ctx: ResponseContext = {
      engine, req, res, path: url.split("?")[0], generation: engine.generation,
      key: JSON.stringify([req.headers.host || "", url]), eligible: requestAllowed(req) && !responseBlocksCache(res),
    };
    if (req.method !== "GET") guardExplicitHeaders(res);
    if (["POST", "PUT", "PATCH", "DELETE"].includes(req.method || "")) {
      trackMutation(engine, ctx); next(); return;
    }
    if (!["GET", "HEAD"].includes(req.method || "")) { next(); return; }
    const cached = ctx.eligible ? engine.cache.get(ctx.key) : null;
    if (cached) { serveCached(ctx, cached); return; }
    if (req.method === "GET") interceptResponse(ctx);
    next();
  };
}

export { FastMemoryCache, CacheEntry, ResponseCompressor, FastMinifier };
