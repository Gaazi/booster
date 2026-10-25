/** Parity coverage for the operator snapshot, bypass reasons and the invalidation bus. */
import test from "node:test";
import type { TestContext } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { booster, FileInvalidationBus, REASONS } from "./engine.ts";

/** Start a bounded server that runs the middleware in front of the origin. */
async function server(t: TestContext, origin: (req: http.IncomingMessage, res: http.ServerResponse) => void,
                      middleware: ReturnType<typeof booster>): Promise<string> {
  const instance = http.createServer((req, res) => middleware(req, res, () => origin(req, res)));
  await new Promise<void>(resolve => instance.listen(0, "127.0.0.1", resolve));
  t.after(() => { instance.closeAllConnections(); instance.close(); });
  return `http://127.0.0.1:${(instance.address() as import("node:net").AddressInfo).port}`;
}

/** Read the raw response body and status of one request. */
async function fetchBody(url: string, options: http.RequestOptions = {}): Promise<{body: string; status: number}> {
  return new Promise((resolve, reject) => {
    const req = http.request(url, options, res => {
      const chunks: Buffer[] = [];
      res.on("data", chunk => chunks.push(chunk));
      res.on("end", () => resolve({body: Buffer.concat(chunks).toString(), status: res.statusCode!}));
      res.on("error", reject);
    });
    req.on("error", reject);
    req.end();
  });
}

test("status snapshot reports counters and bypass reasons", async t => {
  const middleware = booster();
  const url = await server(t, (req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end("body{}");
  }, middleware);
  await fetchBody(url);
  await fetchBody(url);
  const status = middleware.status();
  assert.equal(status.metrics.totalRequests, 2);
  assert.equal(status.metrics.cacheHits, 1);
  assert.equal(status.metrics.cacheMisses, 1);
  assert.equal(status.configuration.invalidation, "process");
  assert.ok(status.cache.items >= 1);
});

test("bypass reasons count a credentialed request", async t => {
  const middleware = booster();
  const url = await server(t, (req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end("body{}");
  }, middleware);
  await fetchBody(url, {headers: {cookie: "session=secret-value"}});
  const reasons = middleware.status().metrics.bypassReasons;
  assert.equal(reasons[REASONS.CREDENTIALS], 1);
  assert.equal(reasons[REASONS.STORED], undefined);
});

test("status snapshot holds no request data", async t => {
  const middleware = booster();
  const url = await server(t, (req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end("body{}");
  }, middleware);
  await fetchBody(url, {headers: {cookie: "session=secret-value"}});
  const snapshot = JSON.stringify(middleware.status());
  assert.ok(!snapshot.includes("secret-value"));
  assert.ok(!snapshot.includes("/style.css"));
});

test("file invalidation bus delivers notices to another reader", () => {
  const path = join(mkdtempSync(join(tmpdir(), "booster-bus-")), "notices.log");
  const publisher = new FileInvalidationBus(path);
  const reader = new FileInvalidationBus(path);
  publisher.publish("/catalog");
  assert.deepEqual(reader.drain(), ["/catalog"]);
  assert.deepEqual(reader.drain(), []);
  publisher.publish("*");
  assert.deepEqual(reader.drain(), ["*"]);
  reader.close();
});

test("shared invalidation clears the peer engine cache", async t => {
  const path = join(mkdtempSync(join(tmpdir(), "booster-bus-")), "notices.log");
  const first = booster({invalidationBus: new FileInvalidationBus(path)});
  const second = booster({invalidationBus: new FileInvalidationBus(path)});
  let value = "old";
  const origin = (req: http.IncomingMessage, res: http.ServerResponse): void => {
    if (req.method === "POST") value = "new";
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end(value);
  };
  const firstUrl = await server(t, origin, first);
  const secondUrl = await server(t, origin, second);
  assert.equal((await fetchBody(firstUrl)).body, "old");
  assert.equal((await fetchBody(secondUrl)).body, "old");
  await fetchBody(firstUrl, {method: "POST"});
  assert.equal((await fetchBody(firstUrl)).body, "new");
  assert.equal((await fetchBody(secondUrl)).body, "new");
  assert.equal(second.status().configuration.invalidation, "shared");
});

test("vary negotiation is accepted and extra fields need the allow list", async t => {
  const calls = { count: 0 };
  const origin = (req: http.IncomingMessage, res: http.ServerResponse): void => {
    calls.count++;
    res.setHeader("Cache-Control", "public, max-age=60");
    res.setHeader("Vary", "Accept-Encoding, User-Agent");
    res.end("body{}");
  };

  const blocked = booster();
  const blockedUrl = await server(t, origin, blocked);
  await fetchBody(`${blockedUrl}/static/app.css`);
  await fetchBody(`${blockedUrl}/static/app.css`);
  assert.equal(calls.count, 2, "an extra Vary field must block the cache by default");

  const allowed = booster({allowedVary: ["user-agent"]});
  const allowedUrl = await server(t, origin, allowed);
  await fetchBody(`${allowedUrl}/static/app.css`);
  await fetchBody(`${allowedUrl}/static/app.css`);
  assert.equal(calls.count, 3, "the allow list must admit the declared field");
});
