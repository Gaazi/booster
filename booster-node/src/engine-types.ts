/** Shared types for the conservative HTTP middleware. */
import type { IncomingMessage, ServerResponse } from "node:http";
import type { FastMemoryCache } from "./cache.ts";
import type { ResponseCompressor } from "./compressor.ts";
import type { BypassTracker } from "./bypass.ts";
import type { InvalidationBus } from "./invalidation.ts";
import type { StatusSnapshot } from "./status.ts";

export interface BoosterOptions {
  maxItems?: number;
  ttl?: number;
  minCompressSize?: number;
  compressDynamic?: boolean;
  maxCacheBytes?: number;
  invalidationBus?: InvalidationBus;
  includePaths?: string[] | null;
  excludePaths?: string[];
}

export type BoosterRequest = IncomingMessage & {
  originalUrl?: string; user?: unknown; session?: unknown; auth?: unknown;
};
export type NextFunction = (err?: any) => void;
export interface BoosterMiddleware {
  (req: BoosterRequest, res: ServerResponse, next: NextFunction): void;
  /** Return an operator snapshot without cache keys, payloads or request data. */
  status(): StatusSnapshot;
}
export interface EngineCounters {
  totalRequests: number;
  cacheHits: number;
  cacheMisses: number;
}
export interface EngineState {
  cache: FastMemoryCache;
  compressor: ResponseCompressor;
  options: BoosterOptions;
  generation: number;
  bus: InvalidationBus;
  sharedInvalidation: boolean;
  bypass: BypassTracker;
  counters: EngineCounters;
}
export interface ResponseContext {
  engine: EngineState;
  req: BoosterRequest;
  res: ServerResponse;
  key: string;
  path: string;
  generation: number;
  eligible: boolean;
}
