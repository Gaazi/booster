/** Preserve bytes and headers while caching bounded non-streaming GET bodies. */
import type { ServerResponse } from "node:http";
import { CacheEntry } from "./cache.ts";
import { isCompressible } from "./compressor.ts";
import { directives, edgePolicy, MAX_BODY_BYTES, responseTTL, snapshotHeaders } from "./policy.ts";
import type { ResponseContext } from "./engine-types.ts";
import { guardExplicitHeaders } from "./header-guard.ts";

/** Merge encoding variation without erasing the host's existing Vary fields. */
function varyEncoding(res: ServerResponse): void {
  const vary = String(res.getHeader("vary") || "").split(",").map(x => x.trim()).filter(Boolean);
  if (!vary.some(value => value.toLowerCase() === "accept-encoding")) vary.push("Accept-Encoding");
  res.setHeader("Vary", vary.join(", "));
}

/** Skip encoded, partial, explicitly immutable or oversized transformations. */
function canTransform(ctx: ResponseContext, size: number): boolean {
  const {req, res} = ctx;
  return ["GET", "HEAD"].includes(req.method || "") && size < MAX_BODY_BYTES && res.statusCode === 200
    && !res.headersSent && !res.hasHeader("content-encoding") && !res.hasHeader("content-range")
    && !("range" in req.headers) && !("if-range" in req.headers)
    && !directives(String(req.headers["cache-control"] || "")).has("no-transform")
    && !directives(String(res.getHeader("cache-control") || "")).has("no-transform");
}

/** Negotiate compression consistently on cold responses and warm hits. */
function compress(ctx: ResponseContext, body: Buffer): Buffer {
  const type = String(ctx.res.getHeader("content-type") || "text/plain");
  if (!canTransform(ctx, body.length) || !isCompressible(type, body.length, ctx.engine.compressor.minSize)) return body;
  varyEncoding(ctx.res);
  const result = ctx.engine.compressor.compress(body, type, String(ctx.req.headers["accept-encoding"] || ""));
  if (result.encoding) {
    ctx.res.setHeader("Content-Encoding", result.encoding);
    ctx.res.setHeader("Content-Length", result.data.length);
  }
  return result.data;
}

/** Store immutable origin bytes only while the request's mutation epoch matches. */
function storeBody(ctx: ResponseContext, body: Buffer): CacheEntry | null {
  const ttl = ctx.eligible ? responseTTL(ctx.res, ctx.engine.cache.defaultTTL) : 0;
  if (!ttl || body.length >= MAX_BODY_BYTES || ctx.generation !== ctx.engine.generation) return null;
  const declared = ctx.res.getHeader("content-length");
  if (declared !== undefined && Number(declared) !== body.length) return null;
  const entry = ctx.engine.cache.set(ctx.key, ctx.path, 200, snapshotHeaders(ctx.res), body,
    String(ctx.res.getHeader("content-type") || "text/plain"), ttl);
  ctx.res.setHeader("ETag", entry.etag);
  edgePolicy(ctx.res, ttl);
  return entry;
}

/** Replay validators and security headers, including body-free conditional hits. */
export function serveCached(ctx: ResponseContext, entry: CacheEntry): void {
  const {req, res} = ctx;
  for (const [name, value] of Object.entries(entry.headers)) {
    if (value !== undefined && !res.hasHeader(name)) res.setHeader(name, value);
  }
  res.setHeader("Content-Type", entry.contentType);
  res.setHeader("ETag", entry.etag);
  res.setHeader("Age", Math.floor(Number(entry.headers.age || 0) + entry.ageSeconds));
  edgePolicy(res, (entry.ttlMs / 1000) - entry.ageSeconds);
  const candidates = String(req.headers["if-none-match"] || "").split(",").map(x => x.trim().replace(/^W\//, ""));
  if (candidates.includes("*") || candidates.includes(entry.etag.replace(/^W\//, ""))) {
    res.statusCode = 304;
    res.removeHeader("Content-Length");
    res.end();
    return;
  }
  res.statusCode = entry.statusCode;
  const data = compress(ctx, entry.body);
  res.setHeader("Content-Length", data.length);
  res.end(req.method === "HEAD" ? undefined : data);
}

/** Preserve stream/callback behavior without retaining any streamed chunks. */
export function interceptResponse(ctx: ResponseContext): void {
  const {res} = ctx;
  const originalEnd = res.end.bind(res) as (...args: any[]) => ServerResponse;
  const mode = {automatic: false};
  guardExplicitHeaders(res, mode);
  const end = (...args: any[]): ServerResponse => { mode.automatic = true; return originalEnd(...args); };
  const write = res.write.bind(res) as (...args: any[]) => boolean;
  let streaming = false;
  res.write = function (...args: any[]): boolean {
    streaming = true;
    edgePolicy(res);
    return write(...args);
  };
  res.end = function (chunk?: any, ...args: any[]): ServerResponse {
    if (streaming || res.headersSent || typeof chunk === "function") { edgePolicy(res); return end(chunk, ...args); }
    const size = typeof chunk === "string" ? Buffer.byteLength(chunk) : (chunk?.byteLength || 0);
    if (size >= MAX_BODY_BYTES) { edgePolicy(res); return end(chunk, ...args); }
    const encoding = typeof args[0] === "string" ? args[0] as BufferEncoding : undefined;
    const body = chunk === undefined || chunk === null ? Buffer.alloc(0) : Buffer.from(chunk, encoding);
    const entry = storeBody(ctx, body);
    if (!entry) edgePolicy(res);
    const data = entry || ctx.engine.options.compressDynamic ? compress(ctx, body) : body;
    return end(data, ...args);
  };
}
