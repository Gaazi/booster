/** Regression coverage for credential isolation, freshness and response integrity. */
import test from "node:test";
import type { TestContext } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { gzipSync } from "node:zlib";
import { booster, ResponseCompressor, FastMemoryCache, FastMinifier } from "./engine.ts";
import type { BoosterOptions } from "../src/index.ts";

type Origin = (req: http.IncomingMessage, res: http.ServerResponse) => void;

/** Start a bounded local fixture and always close its sockets after the test. */
export async function fixture(t: TestContext, origin: Origin, options: BoosterOptions = {}): Promise<string> {
  const middleware = booster(options);
  const server = http.createServer((req, res) => middleware(req, res, () => origin(req, res)));
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => { server.closeAllConnections(); server.close(); });
  return `http://127.0.0.1:${(server.address() as import("node:net").AddressInfo).port}/style.css`;
}

/** Read raw wire bytes without fetch's automatic decompression or cache headers. */
export async function request(url: string, headers: http.OutgoingHttpHeaders = {}, method = "GET"):
Promise<{body: Buffer; headers: http.IncomingHttpHeaders; status: number}> {
  return new Promise<{body: Buffer; headers: http.IncomingHttpHeaders; status: number}>(
    (resolve, reject) => {
      const req = http.request(url, {headers, method}, res => {
        const chunks: Buffer[] = [];
        res.on("data", chunk => chunks.push(chunk));
        res.on("end", () => resolve({body: Buffer.concat(chunks), headers: res.headers, status: res.statusCode!}));
        res.on("error", reject);
      });
      req.on("error", reject);
      req.end();
    },
  );
}

test("static-looking URLs must not share cookie-specific responses", async t => {
  const url = await fixture(t, (req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end(req.headers.cookie || "anonymous");
  });
  await request(url, {cookie: "user=alice"});
  assert.equal((await request(url, {cookie: "user=bob"})).body.toString(), "user=bob");
  assert.equal((await request(url)).body.toString(), "anonymous");
});

test("cache hits preserve origin security/freshness headers and identical CSS", async t => {
  let calls = 0;
  const body = 'p::after { content: "a ; b"; }';
  const url = await fixture(t, (_req, res) => {
    calls++;
    res.setHeader("Content-Type", "text/css");
    res.setHeader("Cache-Control", "public, max-age=60");
    res.setHeader("Content-Security-Policy", "default-src 'none'");
    res.end(body);
  });
  const first = await request(url);
  const hit = await request(url);
  assert.equal(calls, 1);
  assert.deepEqual(hit.body, first.body);
  assert.equal(hit.headers["cache-control"], first.headers["cache-control"]);
  assert.equal(hit.headers["content-security-policy"], "default-src 'none'");
  assert.ok(Number(hit.headers.age) >= 0);
});

test("HEAD misses cannot seed an empty GET representation", async t => {
  const url = await fixture(t, (req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end(req.method === "HEAD" ? undefined : "body");
  });
  await request(url, {}, "HEAD");
  assert.equal((await request(url)).body.toString(), "body");
});

test("origin max-age bounds the configured RAM TTL", async t => {
  let calls = 0;
  const url = await fixture(t, (_req, res) => {
    res.setHeader("Cache-Control", "public, max-age=1");
    res.end(String(++calls));
  });
  await request(url);
  await new Promise(resolve => setTimeout(resolve, 1100));
  assert.equal((await request(url)).body.toString(), "2");
});

test("implicit public responses cannot enter shared caching", async t => {
  let calls = 0;
  const url = await fixture(t, (_req, res) => res.end(String(++calls)));
  await request(url);
  assert.equal((await request(url)).body.toString(), "2");
});

test("no-transform forbids dynamic compression", async t => {
  const body = "private body ".repeat(100);
  const url = await fixture(t, (_req, res) => {
    res.setHeader("Cache-Control", "private, no-transform");
    res.setHeader("Content-Type", "text/plain");
    res.end(body);
  }, {compressDynamic: true, minCompressSize: 1});
  const response = await request(url, {"accept-encoding": "gzip"});
  assert.equal(response.headers["content-encoding"], undefined);
  assert.equal(response.body.toString(), body);
});

test("encoding quality zero must not select a forbidden codec", () => {
  const compressor = new ResponseCompressor(1);
  const result = compressor.compress("A".repeat(2000), "text/plain", "br;q=0, gzip;q=1");
  assert.equal(result.encoding, "gzip");
});

test("a write clears values cached while that write was in flight", async t => {
  let value = "old";
  let release!: () => void;
  let started!: () => void;
  const ready = new Promise<void>(resolve => { started = resolve; });
  const url = await fixture(t, (req, res) => {
    if (req.method === "POST") {
      release = () => { value = "new"; res.end("saved"); };
      started();
    } else {
      res.setHeader("Cache-Control", "public, max-age=60");
      res.end(value);
    }
  });
  const write = request(url, {}, "POST");
  await ready;
  await request(url);
  release();
  await write;
  assert.equal((await request(url)).body.toString(), "new");
});

test("conditional hits retain security headers and honor explicit caller refresh", async t => {
  let calls = 0;
  const url = await fixture(t, (_req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.end(String(++calls));
  });
  const first = await request(url);
  const hit = await request(url, {"if-none-match": first.headers.etag});
  assert.equal(hit.status, 304);
  assert.equal(hit.headers["x-content-type-options"], "nosniff");
  assert.equal(hit.headers["cache-control"], first.headers["cache-control"]);
  assert.equal((await request(url, {"cache-control": "no-cache"})).body.toString(), "2");
});

test("already-aged responses do not enter shared storage", async t => {
  let calls = 0;
  const url = await fixture(t, (_req, res) => {
    res.setHeader("Cache-Control", "public, max-age=1");
    res.setHeader("Age", "1");
    res.end(String(++calls));
  });
  await request(url);
  assert.equal((await request(url)).body.toString(), "2");
});

test("origin variants bypass shared storage", async t => {
  let calls = 0;
  const url = await fixture(t, (_req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.setHeader("Vary", "Accept-Language");
    res.end(String(++calls));
  });
  await request(url);
  assert.equal((await request(url)).body.toString(), "2");
});

test("byte budgets evict LRU entries and explicit zero disables storage", () => {
  const cache = new FastMemoryCache(10, 60, 6);
  cache.set("a", "/a", 200, {}, "aaaa", "text/plain");
  cache.set("b", "/b", 200, {}, "bbbb", "text/plain");
  assert.equal(cache.get("a"), null);
  assert.equal(cache.residentBytes, 4);
  cache.set("large", "/large", 200, {}, "too large", "text/plain");
  assert.equal(cache.get("large"), null);
  const disabled = new FastMemoryCache(0, 60);
  disabled.set("a", "/a", 200, {}, "a", "text/plain");
  assert.equal(disabled.size, 0);
  assert.throws(() => new FastMemoryCache(-1), RangeError);
});

test("minification preserves large JSON numbers, string whitespace and binary bytes", () => {
  const minifier = new FastMinifier();
  const json = '{ "id": 9007199254740993, "label": "a ; b" }';
  assert.equal(minifier.minify(json, "application/json").toString(),
    '{"id":9007199254740993,"label":"a ; b"}');
  const bytes = Buffer.from([0xff, 0x7b, 0x7d]);
  assert.deepEqual(minifier.minify(bytes, "application/json"), bytes);
  assert.deepEqual(minifier.minify(bytes, "text/css"), bytes);
});

test("streamed bodies pass through without transformation", async t => {
  const url = await fixture(t, (_req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.setHeader("Content-Type", "text/plain");
    res.write("first ");
    res.end("second");
  }, {compressDynamic: true, minCompressSize: 1});
  const result = await request(url, {"accept-encoding": "gzip"});
  assert.equal(result.body.toString(), "first second");
  assert.equal(result.headers["content-encoding"], undefined);
  assert.equal(result.headers["cdn-cache-control"], "no-store");
});

for (const raw of [false, true]) test("explicit writeHead protects edge headers (raw=" + raw + ")", async t => {
  const url = await fixture(t, (_req, res) => {
    const headers = raw ? ["Cache-Control", "private", "CDN-Cache-Control", "public, max-age=999"]
      : {"Cache-Control": "private", "CDN-Cache-Control": "public, max-age=999"};
    res.writeHead(200, headers);
    res.end("private");
  });
  const result = await request(url);
  assert.equal(result.body.toString(), "private");
  assert.equal(result.headers["cdn-cache-control"], "no-store");
  assert.equal(result.headers["surrogate-control"], "no-store");
});

test("pre-encoded bytes pass through unchanged and never enter RAM cache", async t => {
  let calls = 0;
  const bytes = gzipSync("origin bytes ".repeat(100));
  const url = await fixture(t, (_req, res) => {
    calls++;
    res.setHeader("Cache-Control", "public, max-age=60");
    res.setHeader("Content-Type", "text/plain");
    res.setHeader("Content-Encoding", "gzip");
    res.end(bytes);
  }, {compressDynamic: true, minCompressSize: 1});
  await request(url);
  const result = await request(url);
  assert.deepEqual(result.body, bytes);
  assert.equal(result.headers["content-encoding"], "gzip");
  assert.equal(calls, 2);
});

test("outer host privacy headers prevent reading a previously public cache entry", async t => {
  const middleware = booster();
  const server = http.createServer((req, res) => {
    const privateRequest = Boolean(req.headers["x-private"]);
    res.setHeader("Cache-Control", privateRequest ? "private" : "public, max-age=60");
    middleware(req, res, () => res.end(privateRequest ? "private" : "public"));
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => { server.closeAllConnections(); server.close(); });
  const url = "http://127.0.0.1:" + (server.address() as import("node:net").AddressInfo).port;
  await request(url);
  const result = await request(url, {"x-private": "1"});
  assert.equal(result.body.toString(), "private");
  assert.equal(result.headers["cdn-cache-control"], "no-store");
});
