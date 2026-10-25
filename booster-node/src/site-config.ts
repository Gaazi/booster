/** Declarative site configuration for a Node deployment. */
import { readFileSync } from "node:fs";
import { FileInvalidationBus } from "./invalidation.ts";
import type { BoosterOptions } from "./engine-types.ts";

const KNOWN_KEYS = new Set([
  "includePaths", "excludePaths", "ttl", "maxItems", "maxCacheBytes",
  "minCompressSize", "compressDynamic", "invalidationFile",
]);

/** One site's route policy and cache limits. */
export interface SiteConfig {
  includePaths?: string[] | null;
  excludePaths?: string[];
  ttl?: number;
  maxItems?: number;
  maxCacheBytes?: number;
  minCompressSize?: number;
  compressDynamic?: boolean;
  invalidationFile?: string;
}

/** Validate a list of absolute route prefixes. */
function paths(value: unknown, name: string): string[] | undefined {
  if (value === undefined || (value === null && name === "includePaths")) return undefined;
  if (!Array.isArray(value)) throw new Error(`${name} must be a list of absolute URL prefixes`);
  for (const prefix of value) {
    if (typeof prefix !== "string" || !prefix.startsWith("/")) {
      throw new Error(`${name} must be absolute URL prefixes`);
    }
  }
  return value as string[];
}

/** Validate a positive numeric setting. */
function positive(value: unknown, name: string): number | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    throw new Error(`${name} must be a positive number`);
  }
  return value;
}

/** Build a configuration from a parsed JSON document and reject unknown settings. */
export function siteConfigFrom(document: Record<string, unknown>): SiteConfig {
  const unknown = Object.keys(document).filter(key => !KNOWN_KEYS.has(key)).sort();
  if (unknown.length) throw new Error(`Unknown site configuration keys: ${unknown.join(", ")}`);
  const includePaths = paths(document.includePaths, "includePaths");
  const excludePaths = paths(document.excludePaths, "excludePaths");
  const config: SiteConfig = {};
  if (includePaths !== undefined) config.includePaths = includePaths;
  if (excludePaths !== undefined) config.excludePaths = excludePaths;
  for (const key of ["ttl", "maxItems", "maxCacheBytes", "minCompressSize"] as const) {
    const value = positive(document[key], key);
    if (value === undefined) continue;
    if (key !== "ttl" && !Number.isSafeInteger(value)) throw new Error(`${key} must be a positive integer`);
    config[key] = value;
  }
  optionalSettings(document, config);
  return config;
}

/** Reject malformed optional settings instead of silently disabling a shared bus. */
function optionalSettings(document: Record<string, unknown>, config: SiteConfig): void {
  if (document.compressDynamic !== undefined) {
    if (typeof document.compressDynamic !== "boolean") throw new Error("compressDynamic must be a boolean");
    config.compressDynamic = document.compressDynamic;
  }
  const path = document.invalidationFile;
  if (path === undefined || path === null) return;
  if (typeof path !== "string" || !path.trim() || path.includes("\0")) {
    throw new Error("invalidationFile must be a nonempty path string or null");
  }
  config.invalidationFile = path;
}

/** Read a configuration from one JSON file. */
export function loadSiteConfig(path: string): SiteConfig {
  const parsed = JSON.parse(readFileSync(path, "utf8")) as unknown;
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Site configuration must be a JSON object");
  }
  return siteConfigFrom(parsed as Record<string, unknown>);
}

/** Build the engine options for a declarative configuration. */
export function optionsFrom(config: SiteConfig): BoosterOptions {
  const options: BoosterOptions = {};
  if (config.includePaths !== undefined) options.includePaths = config.includePaths;
  if (config.excludePaths !== undefined) options.excludePaths = config.excludePaths;
  if (config.ttl !== undefined) options.ttl = config.ttl;
  if (config.maxItems !== undefined) options.maxItems = config.maxItems;
  if (config.maxCacheBytes !== undefined) options.maxCacheBytes = config.maxCacheBytes;
  if (config.minCompressSize !== undefined) options.minCompressSize = config.minCompressSize;
  if (config.compressDynamic !== undefined) options.compressDynamic = config.compressDynamic;
  if (config.invalidationFile) options.invalidationBus = new FileInvalidationBus(config.invalidationFile);
  return options;
}
