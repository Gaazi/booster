/**
 * Adaptive Brotli and Gzip HTTP response compressor using Node.js built-in zlib.
 */
import * as zlib from "zlib";

export const COMPRESSIBLE_TYPES: Set<string> = new Set([
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

export interface CompressionResult {
  data: Buffer;
  encoding: string | null;
}

export function isCompressible(
  contentType: string,
  length: number,
  minSize: number = 512
): boolean {
  if (length < minSize) return false;
  const baseType = (contentType || "").split(";")[0].trim().toLowerCase();
  return COMPRESSIBLE_TYPES.has(baseType);
}

export function chooseEncoding(acceptEncoding: string = ""): string | null {
  const qualities = new Map<string, number>();
  for (const item of acceptEncoding.toLowerCase().split(",")) {
    const [name, ...parameters] = item.trim().split(";");
    const quality = parameters.find(value => value.trim().startsWith("q="));
    const value = quality ? Number(quality.trim().slice(2)) : 1;
    qualities.set(name.trim(), Number.isFinite(value) && value >= 0 && value <= 1 ? value : 0);
  }
  const weight = (name: string): number => qualities.get(name) ?? qualities.get("*") ?? 0;
  const candidates = ["br", "gzip", "deflate"].sort((a, b) => weight(b) - weight(a));
  const selected = candidates[0];
  const identity = qualities.get("identity") ?? 0;
  return weight(selected) > 0 && weight(selected) >= identity ? selected : null;
}

export function compressBuffer(buffer: Buffer, encoding: string): Buffer {
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

export class ResponseCompressor {
  public minSize: number;

  constructor(minSize: number = 512) {
    this.minSize = minSize;
  }

  public compress(
    content: Buffer | string,
    contentType: string,
    acceptEncoding: string = ""
  ): CompressionResult {
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
