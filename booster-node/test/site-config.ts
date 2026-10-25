/** Parity coverage for the route policy and the declarative site configuration. */
import test from "node:test";
import type { TestContext } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { booster, loadSiteConfig, optionsFrom, siteConfigFrom } from "./engine.ts";

/** Start a bounded server that runs the middleware in front of the origin. */
async function server(t: TestContext, origin: (req: http.IncomingMessage, res: http.ServerResponse) => void,
                      middleware: ReturnType<typeof booster>): Promise<string> {
  const instance = http.createServer((req, res) => middleware(req, res, () => origin(req, res)));
  await new Promise<void>(resolve => instance.listen(0, "127.0.0.1", resolve));
  t.after(() => { instance.closeAllConnections(); instance.close(); });
  return `http://127.0.0.1:${(instance.address() as import("node:net").AddressInfo).port}`;
}

/** Read the raw response body of one request. */
async function fetchBody(url: string, options: http.RequestOptions = {}): Promise<string> {
  return new Promise((resolve, reject) => {
    const req = http.request(url, options, res => {
      const chunks: Buffer[] = [];
      res.on("data", chunk => chunks.push(chunk));
      res.on("end", () => resolve(Buffer.concat(chunks).toString()));
      res.on("error", reject);
    });
    req.on("error", reject);
    req.end();
  });
}

test("route policy caches only the selected routes", async t => {
  const middleware = booster({includePaths: ["/static/"], excludePaths: ["/static/private/"]});
  let hits = 0;
  const url = await server(t, (req, res) => {
    hits++;
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end("body{}");
  }, middleware);
  await fetchBody(`${url}/static/app.css`);
  await fetchBody(`${url}/static/app.css`);
  assert.equal(hits, 1, "the selected route must be served from the cache");
  await fetchBody(`${url}/other/page`);
  await fetchBody(`${url}/other/page`);
  assert.equal(hits, 3, "an unselected route must reach the origin every time");
  await fetchBody(`${url}/static/private/file.css`);
  await fetchBody(`${url}/static/private/file.css`);
  assert.equal(hits, 5, "an excluded route must reach the origin every time");
});

test("route policy reports the unselected reason", async t => {
  const middleware = booster({includePaths: ["/static/"]});
  const url = await server(t, (req, res) => {
    res.setHeader("Cache-Control", "public, max-age=60");
    res.end("body{}");
  }, middleware);
  await fetchBody(`${url}/other/page`);
  assert.equal(middleware.status().metrics.bypassReasons.route_not_selected, 1);
});

test("site configuration builds the engine options", () => {
  const config = siteConfigFrom({
    includePaths: ["/static/"], excludePaths: ["/media/"], ttl: 120,
    maxCacheBytes: 8388608, compressDynamic: false,
  });
  const options = optionsFrom(config);
  assert.deepEqual(options.includePaths, ["/static/"]);
  assert.deepEqual(options.excludePaths, ["/media/"]);
  assert.equal(options.ttl, 120);
  assert.equal(options.maxCacheBytes, 8388608);
});

test("site configuration rejects unknown and invalid settings", () => {
  assert.throws(() => siteConfigFrom({turbo: true}), /Unknown site configuration keys/);
  assert.throws(() => siteConfigFrom({includePaths: "static/"}), /absolute URL prefixes/);
  assert.throws(() => siteConfigFrom({excludePaths: ["media/"]}), /absolute URL prefixes/);
  assert.throws(() => siteConfigFrom({ttl: 0}), /positive number/);
});

test("site configuration is read from a JSON file", () => {
  const path = join(mkdtempSync(join(tmpdir(), "booster-config-")), "booster.json");
  writeFileSync(path, JSON.stringify({includePaths: ["/static/"], ttl: 90}));
  const config = loadSiteConfig(path);
  assert.deepEqual(config.includePaths, ["/static/"]);
  assert.equal(config.ttl, 90);
});
