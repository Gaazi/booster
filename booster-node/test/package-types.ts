/** Compile-check the public package exports generated from canonical TypeScript. */
import {booster, FastMemoryCache, ResponseCompressor, FastMinifier} from "booster-node";
import type {BoosterMiddleware, BoosterOptions} from "booster-node";

const options: BoosterOptions = {maxCacheBytes: 1024, ttl: 30, compressDynamic: false};
const middleware: BoosterMiddleware = booster(options);
const cache = new FastMemoryCache(10, 30, options.maxCacheBytes);
const compressor = new ResponseCompressor(100);
const minifier = new FastMinifier();
void [middleware, cache, compressor, minifier];
