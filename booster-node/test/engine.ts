/** Select the canonical source or installed compiled package for the same test suite. */
import { pathToFileURL } from "node:url";
import type * as PublicAPI from "../src/index.ts";

const location = process.env.BOOSTER_NODE_ENTRY
  ? pathToFileURL(process.env.BOOSTER_NODE_ENTRY).href
  : new URL("../src/index.ts", import.meta.url).href;
const api = await import(location) as typeof PublicAPI;
const policyLocation = new URL(process.env.BOOSTER_NODE_ENTRY ? "./policy.js" : "./policy.ts", location).href;
const policy = await import(policyLocation) as typeof import("../src/policy.ts");
export const {cacheVerdict} = policy;
export const {booster, FastMemoryCache, CacheEntry, ResponseCompressor, FastMinifier, isStaticAsset,
  FileInvalidationBus, LocalInvalidationBus, REASONS, loadSiteConfig, siteConfigFrom, optionsFrom} = api;
