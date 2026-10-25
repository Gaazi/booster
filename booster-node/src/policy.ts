/** Explicit-public cache admission and origin freshness boundaries. */
import type { ServerResponse } from "node:http";
import type { BoosterRequest } from "./engine-types.ts";
import type { CacheHeaders } from "./cache.ts";

export const MAX_BODY_BYTES = 3_000_000;
const FORBIDDEN = ["private", "no-store", "no-cache", "no-transform"];
type CacheResponse = Pick<ServerResponse, "statusCode" | "getHeader" | "hasHeader">;

/** Retain outer host privacy decisions on hits as well as misses. */
export function responseBlocksCache(res: CacheResponse, allowedVary: string[] = []): boolean {
  const controls = ["cache-control", "cdn-cache-control", "surrogate-control"]
    .map(name => directives(String(res.getHeader(name) || "")));
  if (controls.some(control => FORBIDDEN.some(name => control.has(name)))) return true;
  if (["set-cookie", "content-range", "www-authenticate", "content-encoding"].some(name => res.hasHeader(name))) return true;
  return !varyAccepted(res, allowedVary);
}

/** Accept only the negotiation fields the site declared it may ignore. */
function varyAccepted(res: CacheResponse, allowedVary: string[]): boolean {
  const accepted = new Set(["accept-encoding", ...allowedVary.map(field => field.toLowerCase())]);
  const vary = String(res.getHeader("vary") || "").split(",").map(value => value.trim().toLowerCase()).filter(Boolean);
  return vary.every(field => accepted.has(field));
}

/** Parse directives without substring matching or ambiguous duplicate values. */
export function directives(value: string): Map<string, string> {
  const result = new Map<string, string>();
  for (const part of value.split(",")) {
    const [key, ...rest] = part.trim().toLowerCase().split("=");
    if (key) result.set(key, result.has(key) ? "invalid" : rest.join("=").trim());
  }
  return result;
}

/** Check credentials and caller revalidation before any shared lookup. */
export function requestAllowed(req: BoosterRequest): boolean {
  const forbidden = ["authorization", "cookie", "range", "if-range"];
  if (forbidden.some(name => name in req.headers)) return false;
  if (req.user !== undefined || req.session !== undefined || req.auth !== undefined) return false;
  const control = directives(String(req.headers["cache-control"] || ""));
  return !FORBIDDEN.some(name => control.has(name)) && !control.has("max-age")
    && !String(req.headers.pragma || "").toLowerCase().includes("no-cache");
}

/** Include already-aged origin responses when computing their remaining lifetime. */
export function originAge(res: CacheResponse): number {
  const value = String(res.getHeader("age") ?? "0");
  if (!/^\d+$/.test(value)) return Infinity;
  const date = res.getHeader("date");
  const apparent = date ? Math.max(0, (Date.now() - Date.parse(String(date))) / 1000) : 0;
  return Math.max(Number(value), Number.isFinite(apparent) ? apparent : Infinity);
}

/** Bound RAM TTL by all origin freshness policies and prohibit private variants. */
export function responseTTL(res: CacheResponse, configured: number, allowedVary: string[] = []): number {
  const controls = ["cache-control", "cdn-cache-control", "surrogate-control"]
    .map(name => directives(String(res.getHeader(name) || "")));
  if (controls[0].get("public") !== "" || !Number.isFinite(originAge(res))
    || controls.some(c => FORBIDDEN.some(name => c.has(name)))) return 0;
  if (res.statusCode !== 200 || responseBlocksCache(res, allowedVary)) return 0;
  let ttl = configured;
  for (const control of controls) {
    const key = control.has("s-maxage") ? "s-maxage" : "max-age";
    if (!control.has(key)) continue;
    const match = /^(?:"(\d+)"|(\d+))$/.exec(control.get(key)!);
    if (!match) return 0;
    ttl = Math.min(ttl, Number(match[1] ?? match[2]) - originAge(res));
  }
  if (!controls[0].has("max-age") && !controls[0].has("s-maxage") && res.hasHeader("expires")) {
    ttl = Math.min(ttl, (Date.parse(String(res.getHeader("expires"))) - Date.now()) / 1000);
  }
  return Number.isFinite(ttl) ? Math.max(0, ttl) : 0;
}

/** Select cacheable routes without embedding website-specific rules. */
export interface RoutePolicy {
  includePaths?: string[] | null;
  excludePaths?: string[];
}

/** Match complete route names or explicitly slash-terminated subtrees. */
function matches(path: string, prefix: string): boolean {
  return prefix.endsWith("/") ? path.startsWith(prefix) : path === prefix;
}

/** Apply the route policy: exclusions win, and an empty include list selects nothing. */
export function routeAllowed(path: string, policy: RoutePolicy): boolean {
  const excluded = policy.excludePaths ?? [];
  if (excluded.some(prefix => matches(path, prefix))) return false;
  const included = policy.includePaths;
  if (included === undefined || included === null) return true;
  return included.some(prefix => matches(path, prefix));
}

/** Explain whether the engine could store a response and for how long. */
export interface CacheVerdict {
  cacheable: boolean;
  reason: string;
  ttlSeconds: number;
}

/** Judge a plain header record with the engine's own cacheability rules. */
export function cacheVerdict(headers: Record<string, string | undefined>, status: number,
                             configuredTtl = 300, allowedVary: string[] = []): CacheVerdict {
  if (status !== 200) return { cacheable: false, reason: "status_not_cacheable", ttlSeconds: 0 };
  const response: CacheResponse = {
    statusCode: status,
    getHeader: name => headers[name.toLowerCase()],
    hasHeader: name => headers[name.toLowerCase()] !== undefined,
  };
  const ttl = responseTTL(response, configuredTtl, allowedVary);
  return {cacheable: ttl > 0, reason: ttl > 0 ? "stored" : "response_not_public", ttlSeconds: ttl};
}

/** Save original end-to-end headers without connection-specific transport fields. */
export function snapshotHeaders(res: ServerResponse): CacheHeaders {
  const connection = String(res.getHeader("connection") || "").toLowerCase().split(",").map(x => x.trim());
  const excluded = new Set([...connection, "connection", "keep-alive", "transfer-encoding", "upgrade",
    "te", "trailer", "proxy-authenticate", "proxy-authorization", "content-length", "content-encoding", "etag"]);
  const headers: CacheHeaders = {};
  for (const [name, value] of Object.entries(res.getHeaders())) {
    if (value !== undefined && !excluded.has(name)) headers[name] = Array.isArray(value) ? [...value] : String(value);
  }
  headers.age = String(originAge(res));
  return headers;
}

/** Protect private and uncacheable replies from edge storage. */
export function edgePolicy(res: ServerResponse, ttl = 0): void {
  if (res.headersSent) return;
  const policy = ttl > 0 ? "public, max-age=" + Math.floor(ttl) : "no-store";
  res.setHeader("CDN-Cache-Control", policy);
  res.setHeader("Surrogate-Control", policy);
}
