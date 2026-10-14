/// <reference types="node" />

export class CacheEntry {
  statusCode: number;
  headers: Record<string, string | string[]>;
  body: Buffer | string;
  contentType: string;
  etag: string;
  createdAt: number;
  ttlMs: number;

  constructor(
    statusCode: number,
    headers: Record<string, string | string[]>,
    body: Buffer | string,
    contentType: string,
    ttl: number
  );

  static computeETag(body: Buffer | string): string;
  get isExpired(): boolean;
}

export class FastMemoryCache {
  maxItems: number;
  defaultTTL: number;
  store: Map<string, CacheEntry>;
  pathIndex: Map<string, string>;

  constructor(maxItems?: number, defaultTTL?: number);

  makeKey(method: string, path: string, query?: string): string;
  get(key: string): CacheEntry | null;
  set(
    key: string,
    path: string,
    statusCode: number,
    headers: Record<string, string | string[]>,
    body: Buffer | string,
    contentType: string,
    ttl?: number
  ): CacheEntry;
  delete(key: string): boolean;
  invalidatePrefix(prefix: string): number;
  clear(): void;
  get size(): number;
}
