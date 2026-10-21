/** Coverage for the Node command line: scaffolding, measuring and the report. */
import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { cacheVerdict } from "../src/policy.ts";
import { runDoctor, runMeasure } from "../src/cli.ts";

test("cache verdict mirrors the engine rules", () => {
  assert.deepEqual(cacheVerdict({"cache-control": "public, max-age=300"}, 200),
    {cacheable: true, reason: "stored", ttlSeconds: 300});
  assert.equal(cacheVerdict({"cache-control": "private, no-store"}, 200).cacheable, false);
  assert.equal(cacheVerdict({"cache-control": "public"}, 404).reason, "status_not_cacheable");
  assert.equal(cacheVerdict({"cache-control": "public, max-age=300", vary: "User-Agent"}, 200).cacheable, false);
  assert.equal(cacheVerdict({"cache-control": "public, max-age=300", vary: "User-Agent"}, 200,
    300, ["user-agent"]).cacheable, true);
  assert.equal(cacheVerdict({"cache-control": "public, max-age=60", age: "600"}, 200).cacheable, false);
});

test("doctor reports the runtime and the engine version", () => {
  const report = runDoctor() as Record<string, string>;
  assert.ok(report["node"]);
  assert.ok(report["booster"]);
  assert.ok(report["platform"]);
});

test("measure reports the response and the timings", async t => {
  const server = http.createServer((req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end("body{}");
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => { server.closeAllConnections(); server.close(); });
  const url = `http://127.0.0.1:${(server.address() as import("node:net").AddressInfo).port}/style.css`;
  const report = await runMeasure({url, requests: 3}) as Record<string, any>;
  assert.equal(report["status"], 200);
  assert.equal(report["samples"], 3);
  assert.equal(report["verdict"]["cacheable"], true);
  assert.ok(report["p50_ms"] >= 0);
});
