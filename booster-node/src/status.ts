/** Operator snapshot that exposes counters and configuration, never request data. */
import type { EngineState } from "./engine-types.ts";

export const VERSION = "1.0.1";

export interface StatusSnapshot {
  version: string;
  cache: { items: number; bytes: number; maxItems: number; maxCacheBytes: number };
  metrics: {
    totalRequests: number;
    cacheHits: number;
    cacheMisses: number;
    hitRatioPercent: number;
    bypassReasons: Record<string, number>;
  };
  configuration: {
    ttlSeconds: number;
    compressDynamic: boolean;
    maxCacheBytes: number;
    invalidation: string;
  };
}

/** Build the snapshot for one running engine. */
export function buildStatus(engine: EngineState): StatusSnapshot {
  const counters = engine.counters;
  const ratio = counters.totalRequests > 0 ? (counters.cacheHits / counters.totalRequests) * 100 : 0;
  return {
    version: VERSION,
    cache: {
      items: engine.cache.size,
      bytes: engine.cache.residentBytes,
      maxItems: engine.cache.maxItems,
      maxCacheBytes: engine.cache.maxCacheBytes,
    },
    metrics: {
      totalRequests: counters.totalRequests,
      cacheHits: counters.cacheHits,
      cacheMisses: counters.cacheMisses,
      hitRatioPercent: Math.round(ratio * 10) / 10,
      bypassReasons: engine.bypass.getCounts(),
    },
    configuration: {
      ttlSeconds: engine.cache.defaultTTL,
      compressDynamic: engine.options.compressDynamic === true,
      maxCacheBytes: engine.cache.maxCacheBytes,
      invalidation: engine.sharedInvalidation ? "shared" : "process",
    },
  };
}
