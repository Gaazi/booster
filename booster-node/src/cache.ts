/**
 * High-performance in-memory LRU cache with TTL for Node.js.
 */
import * as crypto from "crypto";

export interface CacheHeaders {
  [header: string]: string | string[] | undefined;
}

export class CacheEntry {
  public statusCode: number;
  public headers: CacheHeaders;
  public body: Buffer | string;
  public contentType: string;
  public etag: string;
  public createdAt: number;
  public ttlMs: number;

  constructor(
    statusCode: number,
    headers: CacheHeaders,
    body: Buffer | string,
    contentType: string,
    ttl: number
  ) {
    this.statusCode = statusCode;
    this.headers = headers;
    this.body = body;
    this.contentType = contentType;
    this.etag = CacheEntry.computeETag(body);
    this.createdAt = Date.now();
    this.ttlMs = ttl * 1000;
  }

  public static computeETag(body: Buffer | string): string {
    const hash = crypto.createHash("sha256").update(body).digest("hex").slice(0, 24);
    return `W/"${hash}"`;
  }

  public get isExpired(): boolean {
    return Date.now() - this.createdAt > this.ttlMs;
  }
}

export class FastMemoryCache {
  public maxItems: number;
  public defaultTTL: number;
  public store: Map<string, CacheEntry>;
  public pathIndex: Map<string, string>;

  constructor(maxItems: number = 2000, defaultTTL: number = 300) {
    this.maxItems = maxItems;
    this.defaultTTL = defaultTTL;
    this.store = new Map<string, CacheEntry>();
    this.pathIndex = new Map<string, string>();
  }

  public makeKey(method: string, path: string, query: string = ""): string {
    return `${method}:${path}:${query}`;
  }

  public get(key: string): CacheEntry | null {
    const entry = this.store.get(key);
    if (!entry) return null;
    if (entry.isExpired) {
      this.delete(key);
      return null;
    }
    // Refresh LRU order
    this.store.delete(key);
    this.store.set(key, entry);
    return entry;
  }

  public set(
    key: string,
    path: string,
    statusCode: number,
    headers: CacheHeaders,
    body: Buffer | string,
    contentType: string,
    ttl: number = this.defaultTTL
  ): CacheEntry {
    if (this.store.size >= this.maxItems && !this.store.has(key)) {
      const oldestKey = this.store.keys().next().value;
      if (oldestKey) {
        this.store.delete(oldestKey);
        this.pathIndex.delete(oldestKey);
      }
    }
    const entry = new CacheEntry(statusCode, headers, body, contentType, ttl);
    this.store.set(key, entry);
    this.pathIndex.set(key, path);
    return entry;
  }

  public delete(key: string): boolean {
    this.pathIndex.delete(key);
    return this.store.delete(key);
  }

  public invalidatePrefix(prefix: string): number {
    let count = 0;
    const toDelete: string[] = [];
    for (const [key, path] of this.pathIndex.entries()) {
      if (path.startsWith(prefix)) {
        toDelete.push(key);
      }
    }
    for (const key of toDelete) {
      if (this.delete(key)) count++;
    }
    return count;
  }

  public clear(): void {
    this.store.clear();
    this.pathIndex.clear();
  }

  public get size(): number {
    return this.store.size;
  }
}
