/** Monotonic bounded LRU storage for the Node middleware. */
import { createHash } from "node:crypto";
import { performance } from "node:perf_hooks";

export interface CacheHeaders { [header: string]: string | string[] | undefined; }

export class CacheEntry {
  public statusCode: number;
  public headers: CacheHeaders;
  public body: Buffer;
  public contentType: string;
  public etag: string;
  public createdAt: number;
  public ttlMs: number;

  /** Copy bytes so origin buffers cannot mutate a stored representation. */
  constructor(statusCode: number, headers: CacheHeaders, body: Buffer | string, contentType: string, ttl: number) {
    this.statusCode = statusCode;
    this.headers = {...headers};
    this.body = Buffer.from(body);
    this.contentType = contentType;
    this.etag = CacheEntry.computeETag(this.body);
    this.createdAt = performance.now();
    this.ttlMs = ttl * 1000;
  }

  /** Generate a weak validator that remains valid across negotiated encodings. */
  public static computeETag(body: Buffer | string): string {
    return 'W/"' + createHash("sha256").update(body).digest("hex").slice(0, 24) + '"';
  }

  /** Return elapsed monotonic time independently of system clock adjustments. */
  public get ageSeconds(): number { return (performance.now() - this.createdAt) / 1000; }

  /** Expire at the exact configured lifetime boundary. */
  public get isExpired(): boolean { return this.ageSeconds * 1000 >= this.ttlMs; }
}

export class FastMemoryCache {
  public maxItems: number;
  public defaultTTL: number;
  public maxCacheBytes: number;
  public store = new Map<string, CacheEntry>();
  public pathIndex = new Map<string, string>();
  public residentBytes = 0;

  /** Validate explicit zero budgets instead of silently replacing them with defaults. */
  constructor(maxItems = 2000, defaultTTL = 300, maxCacheBytes = 64 * 1024 * 1024) {
    if (!Number.isInteger(maxItems) || maxItems < 0) throw new RangeError("Invalid maxItems");
    if (!Number.isFinite(defaultTTL) || defaultTTL < 0) throw new RangeError("Invalid TTL");
    if (!Number.isSafeInteger(maxCacheBytes) || maxCacheBytes < 0) throw new RangeError("Invalid byte budget");
    this.maxItems = maxItems;
    this.defaultTTL = defaultTTL;
    this.maxCacheBytes = maxCacheBytes;
  }

  /** Preserve the existing public key API without ambiguous delimiter collisions. */
  public makeKey(method: string, path: string, query = ""): string {
    return JSON.stringify([method, path, query]);
  }

  /** Read a fresh entry and refresh its LRU position. */
  public get(key: string): CacheEntry | null {
    const entry = this.store.get(key);
    if (!entry) return null;
    if (entry.isExpired) { this.delete(key); return null; }
    this.store.delete(key);
    this.store.set(key, entry);
    return entry;
  }

  /** Admit only entries fitting both budgets while retaining the return-value API. */
  public set(key: string, path: string, statusCode: number, headers: CacheHeaders,
             body: Buffer | string, contentType: string, ttl = this.defaultTTL): CacheEntry {
    if (!Number.isFinite(ttl) || ttl < 0) throw new RangeError("Invalid TTL");
    const entry = new CacheEntry(statusCode, headers, body, contentType, ttl);
    this.delete(key);
    if (!this.maxItems || !ttl || entry.body.length > this.maxCacheBytes) return entry;
    while (this.store.size >= this.maxItems || this.residentBytes + entry.body.length > this.maxCacheBytes) {
      this.delete(this.store.keys().next().value!);
    }
    this.store.set(key, entry);
    this.pathIndex.set(key, path);
    this.residentBytes += entry.body.length;
    return entry;
  }

  /** Update byte accounting whenever an entry leaves the cache. */
  public delete(key: string): boolean {
    const entry = this.store.get(key);
    if (entry) this.residentBytes -= entry.body.length;
    this.pathIndex.delete(key);
    return this.store.delete(key);
  }

  /** Invalidate matching paths without changing unaffected entries. */
  public invalidatePrefix(prefix: string): number {
    let count = 0;
    for (const [key, path] of this.pathIndex) {
      if (path.startsWith(prefix) && this.delete(key)) count++;
    }
    return count;
  }

  /** Clear all cache indexes and release the resident body budget. */
  public clear(): void { this.store.clear(); this.pathIndex.clear(); this.residentBytes = 0; }

  /** Report the number of resident entries. */
  public get size(): number { return this.store.size; }
}
