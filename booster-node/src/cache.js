/**
 * High-performance in-memory LRU cache with TTL for Node.js.
 */
const crypto = require("crypto");

class CacheEntry {
  constructor(statusCode, headers, body, contentType, ttl) {
    this.statusCode = statusCode;
    this.headers = headers;
    this.body = body;
    this.contentType = contentType;
    this.etag = CacheEntry.computeETag(body);
    this.createdAt = Date.now();
    this.ttlMs = ttl * 1000;
  }

  static computeETag(body) {
    const hash = crypto.createHash("sha256").update(body).digest("hex").slice(0, 24);
    return `W/"${hash}"`;
  }

  get isExpired() {
    return (Date.now() - this.createdAt) > this.ttlMs;
  }
}

class FastMemoryCache {
  constructor(maxItems = 2000, defaultTTL = 300) {
    this.maxItems = maxItems;
    this.defaultTTL = defaultTTL;
    this.store = new Map();
    this.pathIndex = new Map();
  }

  makeKey(method, path, query = "") {
    return `${method}:${path}:${query}`;
  }

  get(key) {
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

  set(key, path, statusCode, headers, body, contentType, ttl = this.defaultTTL) {
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

  delete(key) {
    this.pathIndex.delete(key);
    return this.store.delete(key);
  }

  invalidatePrefix(prefix) {
    let count = 0;
    const toDelete = [];
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


  clear() {
    this.store.clear();
    this.pathIndex.clear();
  }

  get size() {
    return this.store.size;
  }
}

module.exports = { FastMemoryCache, CacheEntry };
