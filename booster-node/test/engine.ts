/** Select the canonical source or installed compiled package for the same test suite. */
import { pathToFileURL } from "node:url";
import type * as PublicAPI from "../src/index.ts";

const location = process.env.BOOSTER_NODE_ENTRY
  ? pathToFileURL(process.env.BOOSTER_NODE_ENTRY).href
  : new URL("../src/index.ts", import.meta.url).href;
const api = await import(location) as typeof PublicAPI;
export const {booster, FastMemoryCache, CacheEntry, ResponseCompressor, FastMinifier, isStaticAsset} = api;
