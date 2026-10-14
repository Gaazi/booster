/**
 * booster-node - Ultra-fast drop-in caching, minification, and compression engine for Node.js.
 */
const { FastMemoryCache } = require("./cache");
const { ResponseCompressor } = require("./compressor");
const { FastMinifier } = require("./minifier");

const STATIC_EXTENSIONS = [
  ".css", ".js", ".mjs", ".woff", ".woff2", ".ttf", ".eot", ".otf",
  ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".map"
];

function isStaticAsset(path) {
  const clean = (path || "").split("?")[0].toLowerCase();
  return clean.startsWith("/static/") || clean.startsWith("/assets/") || clean.startsWith("/public/") ||
         STATIC_EXTENSIONS.some(ext => clean.endsWith(ext));
}

function booster(options = {}) {
  const cache = new FastMemoryCache(options.maxItems || 2000, options.ttl || 300);
  const compressor = new ResponseCompressor(options.minCompressSize || 512);
  const minifier = new FastMinifier();

  return function boosterMiddleware(req, res, next) {
    const method = req.method.toUpperCase();
    const url = req.url || "/";
    const path = url.split("?")[0];
    const query = url.split("?")[1] || "";
    const isStatic = isStaticAsset(path);

    // Mutation auto-invalidation
    if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
      cache.invalidatePrefix(path);
      return next();
    }

    // Authenticated requests must never be cached publicly
    if (req.headers["authorization"]) {
      return next();
    }

    if (method !== "GET" && method !== "HEAD") {
      return next();
    }

    const key = cache.makeKey("GET", path, query);
    const cached = cache.get(key);

    if (cached) {
      if (req.headers["if-none-match"] === cached.etag) {
        res.statusCode = 304;
        res.setHeader("ETag", cached.etag);
        res.setHeader("Vary", "Accept-Encoding");
        return res.end();
      }

      const { data, encoding } = compressor.compress(
        cached.body, cached.contentType, req.headers["accept-encoding"]
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
    const chunks = [];
    let isStreaming = false;

    const originalWrite = res.write;
    res.write = function (chunk, ...args) {
      isStreaming = true;
      if (chunk) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
      return originalWrite.apply(res, [chunk, ...args]);
    };

    res.end = function (chunk, ...args) {
      if (chunk) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
      const rawBody = Buffer.concat(chunks);
      const contentType = (res.getHeader("content-type") || "text/plain").toString();
      const cacheControl = (res.getHeader("cache-control") || "").toString().toLowerCase();
      const isExplicitPrivate = cacheControl.includes("private") || cacheControl.includes("no-store");
      const hasSetCookie = Boolean(res.getHeader("set-cookie"));
      const isCacheable = !isStreaming && (isStatic || (!isExplicitPrivate && !hasSetCookie)) && res.statusCode === 200 && rawBody.length < 3000000;

      if (isCacheable) {
        const minified = minifier.minify(rawBody, contentType);
        const entry = cache.set(key, path, 200, {}, minified, contentType);
        if (!res.headersSent) res.setHeader("ETag", entry.etag);
      } else if (options.compressDynamic && !isStreaming && res.statusCode === 200 && !res.getHeader("content-encoding")) {
        const { data, encoding } = compressor.compress(rawBody, contentType, req.headers["accept-encoding"]);
        if (encoding) {
          if (!res.headersSent) {
            res.setHeader("Content-Encoding", encoding);
            res.setHeader("Content-Length", data.length);
          }
          return originalEnd.apply(res, [data, ...args]);
        }
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


module.exports = {
  booster,
  FastMemoryCache,
  ResponseCompressor,
  FastMinifier,
};
