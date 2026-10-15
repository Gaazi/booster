/** Shared types for the conservative HTTP middleware. */
import type { IncomingMessage, ServerResponse } from "node:http";
import type { FastMemoryCache } from "./cache.ts";
import type { ResponseCompressor } from "./compressor.ts";

export interface BoosterOptions {
  maxItems?: number;
  ttl?: number;
  minCompressSize?: number;
  compressDynamic?: boolean;
  maxCacheBytes?: number;
}

export type BoosterRequest = IncomingMessage & {
  originalUrl?: string; user?: unknown; session?: unknown; auth?: unknown;
};
export type NextFunction = (err?: any) => void;
export type BoosterMiddleware = (req: BoosterRequest, res: ServerResponse, next: NextFunction) => void;
export interface EngineState {
  cache: FastMemoryCache;
  compressor: ResponseCompressor;
  options: BoosterOptions;
  generation: number;
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
