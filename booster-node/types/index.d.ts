/// <reference types="node" />

import { FastMemoryCache, CacheEntry } from "./cache";
import { ResponseCompressor, CompressionResult } from "./compressor";
import { FastMinifier } from "./minifier";

export interface BoosterOptions {
  /** Maximum number of items in cache (default: 2000) */
  maxItems?: number;
  /** Default cache time-to-live in seconds (default: 300) */
  ttl?: number;
  /** Minimum payload size in bytes eligible for Brotli/Gzip compression (default: 512) */
  minCompressSize?: number;
  /** Adaptively compress dynamic/uncached responses on the fly (default: false) */
  compressDynamic?: boolean;
}

export type NextFunction = (err?: any) => void;

export type BoosterMiddleware = (
  req: any,
  res: any,
  next: NextFunction
) => void;

export const STATIC_EXTENSIONS: string[];
export function isStaticAsset(path: string): boolean;

/**
 * Drop-in ultra-fast caching, minification, and compression engine for Node.js.
 */
export function booster(options?: BoosterOptions): BoosterMiddleware;

export {
  FastMemoryCache,
  CacheEntry,
  ResponseCompressor,
  CompressionResult,
  FastMinifier,
};
