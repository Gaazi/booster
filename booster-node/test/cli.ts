/** Coverage for the Node command line: scaffolding, measuring and the report. */
import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import {spawn, spawnSync} from "node:child_process";
import {fileURLToPath, pathToFileURL} from "node:url";
import { cacheVerdict } from "../src/policy.ts";
import { runDoctor, runMeasure } from "../src/cli.ts";

/** Exercise the installed CLI when the release suite selects an archive. */
function cliEntry(): string {
  return process.env.BOOSTER_NODE_ENTRY
    ? fileURLToPath(new URL("./cli.js", pathToFileURL(process.env.BOOSTER_NODE_ENTRY)))
    : fileURLToPath(new URL("../src/cli.ts", import.meta.url));
}

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

test("the actual measure command fetches twenty samples when requests is omitted", async t => {
  let calls = 0;
  const server = http.createServer((_req, res) => {
    calls++;
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end("body{}");
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => { server.closeAllConnections(); server.close(); });
  const url = `http://127.0.0.1:${(server.address() as import("node:net").AddressInfo).port}/style.css`;
  const child = spawn(process.execPath, [cliEntry(), "measure", url]);
  t.after(() => child.kill());
  let output = "", errors = "";
  child.stdout.on("data", chunk => { output += chunk; });
  child.stderr.on("data", chunk => { errors += chunk; });
  const exit = await new Promise<number | null>((resolve, reject) => {
    child.on("error", reject); child.on("close", resolve);
  });
  assert.equal(exit, 0, errors);
  const report = JSON.parse(output);
  assert.equal(report.samples, 20);
  assert.equal(report.status, 200);
  assert.equal(calls, 20);
});

test("the actual measure command rejects an invalid sample count before fetching", () => {
  for (const count of ["invalid", "0", "-1", "Infinity", "1.5"]) {
    const result = spawnSync(process.execPath, [cliEntry(), "measure", "http://127.0.0.1:1", "--requests", count]);
    assert.equal(result.status, 1);
    assert.match(result.stderr.toString(), /POSITIVE_INTEGER/);
  }
});
