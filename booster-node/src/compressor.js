/**
 * Adaptive Brotli and Gzip HTTP response compressor using Node.js built-in zlib.
 */
const zlib = require("zlib");

const COMPRESSIBLE_TYPES = new Set([
  "text/html",
  "text/css",
  "text/plain",
  "text/xml",
  "text/javascript",
  "application/javascript",
  "application/x-javascript",
  "application/json",
  "application/xml",
  "application/ld+json",
  "image/svg+xml",
]);

function isCompressible(contentType, length, minSize = 512) {
  if (length < minSize) return false;
  const baseType = (contentType || "").split(";")[0].trim().toLowerCase();
  return COMPRESSIBLE_TYPES.has(baseType);
}

function chooseEncoding(acceptEncoding = "") {
  const header = acceptEncoding.toLowerCase();
  if (header.includes("br")) return "br";
  if (header.includes("gzip")) return "gzip";
  if (header.includes("deflate")) return "deflate";
  return null;
}

function compressBuffer(buffer, encoding) {
  if (encoding === "br") {
    return zlib.brotliCompressSync(buffer, {
      params: { [zlib.constants.BROTLI_PARAM_QUALITY]: 4 },
    });
  }
  if (encoding === "gzip") {
    return zlib.gzipSync(buffer, { level: 6 });
  }
  if (encoding === "deflate") {
    return zlib.deflateSync(buffer, { level: 6 });
  }
  return buffer;
}

class ResponseCompressor {
  constructor(minSize = 512) {
    this.minSize = minSize;
  }

  compress(content, contentType, acceptEncoding) {
    const buffer = Buffer.isBuffer(content) ? content : Buffer.from(content);
    if (!isCompressible(contentType, buffer.length, this.minSize)) {
      return { data: buffer, encoding: null };
    }

    const encoding = chooseEncoding(acceptEncoding);
    if (!encoding) {
      return { data: buffer, encoding: null };
    }

    const compressed = compressBuffer(buffer, encoding);
    if (compressed.length >= buffer.length) {
      return { data: buffer, encoding: null };
    }

    return { data: compressed, encoding };
  }
}

module.exports = { ResponseCompressor, isCompressible, chooseEncoding };
