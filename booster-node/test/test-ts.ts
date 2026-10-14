import test from "node:test";
import assert from "node:assert";
import { booster, FastMemoryCache, ResponseCompressor, FastMinifier } from "../src/index.ts";
import type { BoosterOptions } from "../src/index.ts";


test("TypeScript native - FastMemoryCache type check", () => {
  const cache = new FastMemoryCache(100, 60);
  const entry = cache.set("k1", "/path", 200, {}, Buffer.from("test body"), "text/plain");
  assert.strictEqual(entry.statusCode, 200);
  assert.ok(entry.etag.startsWith('W/"'));
  assert.strictEqual(cache.size, 1);
});

test("TypeScript native - ResponseCompressor and FastMinifier", () => {
  const compressor = new ResponseCompressor(10);
  const minifier = new FastMinifier();

  const payload = "<h1>Hello TypeScript Booster</h1> ".repeat(20);
  const min = minifier.minify(payload, "text/html");
  assert.ok(min.toString().includes("Hello TypeScript Booster"));

  const comp = compressor.compress(min, "text/html", "gzip");
  assert.strictEqual(comp.encoding, "gzip");
  assert.ok(comp.data.length < min.length);

});

test("TypeScript native - booster middleware initialization", () => {
  const opts: BoosterOptions = { maxItems: 500, ttl: 120, minCompressSize: 100 };
  const middleware = booster(opts);
  assert.strictEqual(typeof middleware, "function");
});
