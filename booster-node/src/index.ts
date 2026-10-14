/**
 * booster-node - Ultra-fast drop-in caching, minification, and compression engine for Node.js.
 */
import { FastMemoryCache, CacheEntry } from "./cache.ts";
import { ResponseCompressor } from "./compressor.ts";
import type { CompressionResult } from "./compressor.ts";
import { FastMinifier } from "./minifier.ts";



export interface BoosterOptions {
  /** Maximum number of items in cache (default: 2000) */
  maxItems?: number;
  /** Default cache time-to-live in seconds (default: 300) */
  ttl?: number;
  /** Minimum payload size in bytes eligible for Brotli/Gzip compression (default: 512) */
  minCompressSize?: number;
}

export type NextFunction = (err?: any) => void;

export type BoosterMiddleware = (
  req: any,
  res: any,
  next: NextFunction
) => void;

export function booster(options: BoosterOptions = {}): BoosterMiddleware {
  const cache = new FastMemoryCache(options.maxItems || 2000, options.ttl || 300);
  const compressor = new ResponseCompressor(options.minCompressSize || 512);
  const minifier = new FastMinifier();

  return function boosterMiddleware(req: any, res: any, next: NextFunction): void {
    const method: string = (req.method || "GET").toUpperCase();
    const url: string = req.url || "/";
    const path: string = url.split("?")[0];
    const query: string = url.split("?")[1] || "";

    // Mutation auto-invalidation
    if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
      cache.invalidatePrefix(path);
      return next();
    }

    // Authenticated requests must never be cached publicly
    if (req.headers && req.headers["authorization"]) {
      return next();
    }

    if (method !== "GET" && method !== "HEAD") {
      return next();
    }

    const key = cache.makeKey("GET", path, query);
    const cached = cache.get(key);

    if (cached) {
      if (req.headers && req.headers["if-none-match"] === cached.etag) {
        res.statusCode = 304;
        res.setHeader("ETag", cached.etag);
        res.setHeader("Vary", "Accept-Encoding");
        return res.end();
      }

      const { data, encoding } = compressor.compress(
        cached.body,
        cached.contentType,
        req.headers ? req.headers["accept-encoding"] : ""
      );

      res.statusCode = cached.statusCode;
      res.setHeader("Content-Type", cached.contentType);
      res.setHeader("ETag", cached.etag);
      res.setHeader("Vary", "Accept-Encoding");
      res.setHeader("CDN-Cache-Control", "public, max-age=300, stale-while-revalidate=60");
      res.setHeader("Surrogate-Control", "max-age=300");
      res.setHeader("X-Powered-By", "booster-node");
      if (encoding) res.setHeader("Content-Encoding", encoding);
      res.setHeader("Content-Length", data.length);
      return res.end(data);
    }

    // Intercept response
    const originalEnd = res.end;
    const chunks: Buffer[] = [];
    let isStreaming = false;

    const originalWrite = res.write;
    res.write = function (chunk: any, ...args: any[]): any {
      isStreaming = true;
      if (chunk) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
      return originalWrite.apply(res, [chunk, ...args]);
    };

    res.end = function (chunk: any, ...args: any[]): any {
      if (chunk) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
      const rawBody = Buffer.concat(chunks);
      const contentType = (res.getHeader("content-type") || "text/plain").toString();
      const cacheControl = (res.getHeader("cache-control") || "").toString().toLowerCase();
      const isPrivate = cacheControl.includes("no-store") || cacheControl.includes("private");

      if (!isStreaming && !isPrivate && res.statusCode === 200 && rawBody.length < 3000000) {
        const minified = minifier.minify(rawBody, contentType);
        const entry = cache.set(key, path, 200, {}, minified, contentType);
        if (!res.headersSent) res.setHeader("ETag", entry.etag);
      }

      if (!res.headersSent) {
        res.setHeader("CDN-Cache-Control", "public, max-age=300, stale-while-revalidate=60");
        res.setHeader("Surrogate-Control", "max-age=300");
        res.setHeader("X-Powered-By", "booster-node");
      }
      return originalEnd.apply(res, [chunk, ...args]);
    };

    next();
  };
}

export {
  FastMemoryCache,
  CacheEntry,
  ResponseCompressor,
  FastMinifier,
};

export type { CompressionResult };

