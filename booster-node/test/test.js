const test = require("node:test");
const assert = require("node:assert");
const http = require("node:http");
const zlib = require("node:zlib");

const { booster, FastMemoryCache, ResponseCompressor, FastMinifier } = require("../src/index");

test("FastMemoryCache - set, get, etag, and expiry", async (t) => {
  const cache = new FastMemoryCache(10, 0.05); // 50ms TTL
  const key = cache.makeKey("GET", "/test");
  const entry = cache.set(key, "/test", 200, {}, Buffer.from("hello world"), "text/plain");

  assert.strictEqual(entry.statusCode, 200);
  assert.ok(entry.etag.startsWith('W/"'));

  const cached = cache.get(key);
  assert.ok(cached);
  assert.strictEqual(cached.body.toString(), "hello world");

  // Wait for expiry
  await new Promise((r) => setTimeout(r, 60));
  assert.strictEqual(cache.get(key), null);
});

test("FastMemoryCache - prefix invalidation", () => {
  const cache = new FastMemoryCache();
  cache.set("k1", "/api/users/1", 200, {}, Buffer.from("u1"), "text/plain");
  cache.set("k2", "/api/users/2", 200, {}, Buffer.from("u2"), "text/plain");
  cache.set("k3", "/posts/1", 200, {}, Buffer.from("p1"), "text/plain");

  const count = cache.invalidatePrefix("/api/users");
  assert.strictEqual(count, 2);
  assert.strictEqual(cache.get("k1"), null);
  assert.strictEqual(cache.get("k2"), null);
  assert.ok(cache.get("k3"));
});

test("ResponseCompressor - Brotli and Gzip compression", () => {
  const compressor = new ResponseCompressor(10);
  const payload = Buffer.from("A".repeat(1000));

  // Brotli
  const resBr = compressor.compress(payload, "text/plain", "br, gzip");
  assert.strictEqual(resBr.encoding, "br");
  assert.ok(resBr.data.length < payload.length);
  const decompressedBr = zlib.brotliDecompressSync(resBr.data);
  assert.strictEqual(decompressedBr.toString(), payload.toString());

  // Gzip
  const resGz = compressor.compress(payload, "text/plain", "gzip");
  assert.strictEqual(resGz.encoding, "gzip");
  assert.ok(resGz.data.length < payload.length);
  const decompressedGz = zlib.gunzipSync(resGz.data);
  assert.strictEqual(decompressedGz.toString(), payload.toString());
});

test("FastMinifier - HTML, CSS, and JSON minification", () => {
  const minifier = new FastMinifier();

  const html = minifier.minify("<div>   <!-- c -->   <p>Hello</p>   </div>", "text/html");
  assert.strictEqual(html.toString(), "<div><p>Hello</p></div>");

  const css = minifier.minify("/* c */ body {  margin: 0px ; }", "text/css");
  assert.strictEqual(css.toString(), "body{margin:0px;}");

  const json = minifier.minify('{\n  "status": "ok"\n}', "application/json");
  assert.strictEqual(json.toString(), '{"status":"ok"}');
});

test("booster middleware integration - caching, 304, and CDN headers", async () => {
  const middleware = booster();

  const server = http.createServer((req, res) => {
    middleware(req, res, () => {
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify({ message: "rocket" }));
    });
  });

  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;

  // 1st request -> prime cache
  const res1 = await fetch(`http://127.0.0.1:${port}/api/data`);
  assert.strictEqual(res1.status, 200);
  assert.ok(res1.headers.get("etag"));
  assert.ok(res1.headers.get("cdn-cache-control"));
  const etag = res1.headers.get("etag");

  // 2nd request -> cached + 304 Not Modified
  const res2 = await fetch(`http://127.0.0.1:${port}/api/data`, {
    headers: { "if-none-match": etag },
  });
  assert.strictEqual(res2.status, 304);

  // Authenticated request -> bypasses cache
  const resAuth = await fetch(`http://127.0.0.1:${port}/api/data`, {
    headers: { authorization: "Bearer secret-token" },
  });
  assert.strictEqual(resAuth.status, 200);

  server.close();
});

test("booster-node - private responses are never cached or leaked", async () => {
  const middleware = booster();
  let calls = 0;

  const server = http.createServer((req, res) => {
    middleware(req, res, () => {
      calls++;
      res.setHeader("Content-Type", "text/plain");
      res.setHeader("Cache-Control", "private, no-cache, no-store");
      res.end(`User: ${req.headers["x-user"] || "anon"}`);
    });
  });

  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;

  const res1 = await fetch(`http://127.0.0.1:${port}/dashboard`, {
    headers: { "x-user": "alice" },
  });
  assert.strictEqual(await res1.text(), "User: alice");

  const res2 = await fetch(`http://127.0.0.1:${port}/dashboard`, {
    headers: { "x-user": "bob" },
  });
  assert.strictEqual(await res2.text(), "User: bob");
  assert.strictEqual(calls, 2); // Origin called each time, no cross-user cache leak!

  server.close();
});

test("booster-node - static assets cached and accelerated", async () => {
  const middleware = booster();
  let calls = 0;

  const server = http.createServer((req, res) => {
    middleware(req, res, () => {
      calls++;
      res.setHeader("Content-Type", "text/css");
      res.setHeader("Cache-Control", "public, max-age=31536000");
      res.end("body { background: #000; }");
    });
  });

  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;

  const res1 = await fetch(`http://127.0.0.1:${port}/static/bundle.css`, {
    headers: { "cookie": "session=xyz" },
  });
  assert.strictEqual(res1.status, 200);
  assert.strictEqual(calls, 1);

  const res2 = await fetch(`http://127.0.0.1:${port}/static/bundle.css`, {
    headers: { "cookie": "session=different" },
  });
  assert.strictEqual(res2.status, 200);
  assert.strictEqual(calls, 1); // Served directly from memory!

  server.close();
});

