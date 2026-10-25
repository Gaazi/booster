/** Reproduce invalidation races and measurement drift before release promotion. */
import test from "node:test";
import assert from "node:assert/strict";
import {mkdtempSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import type {IncomingMessage, ServerResponse} from "node:http";
import {cacheVerdict, FileInvalidationBus, siteConfigFrom} from "./engine.ts";
import {fixture, request} from "./cache-regressions.ts";

test("a peer invalidation prevents an older in-flight response from refilling RAM", {timeout: 5000}, async t => {
  const path = join(mkdtempSync(join(tmpdir(), "booster-race-")), "notices.log");
  let value = "old", release = (): void => {};
  let signal = (): void => {};
  const started = new Promise<void>(resolve => { signal = resolve; });
  const origin = (req: IncomingMessage, res: ServerResponse): void => {
    if (req.method === "POST") value = "new";
    res.setHeader("Cache-Control", "public, max-age=60");
    const snapshot = value;
    if (req.url?.includes("delayed") && value === "old") {
      release = (): void => { res.end(snapshot); };
      signal();
    } else res.end(snapshot);
  };
  const first = await fixture(t, origin, {invalidationBus: new FileInvalidationBus(path)});
  const second = await fixture(t, origin, {invalidationBus: new FileInvalidationBus(path)});
  const pending = request(first + "?delayed");
  await started;
  t.after(() => release());
  await request(second, {}, "POST");
  assert.equal((await request(first)).body.toString(), "new");
  release();
  await pending;
  assert.equal((await request(first + "?delayed")).body.toString(), "new");
});

test("file bus detects rotation after the file grows past the previous cursor", () => {
  const path = join(mkdtempSync(join(tmpdir(), "booster-rotation-")), "notices.log");
  const publisher = new FileInvalidationBus(path, 128);
  const reader = new FileInvalidationBus(path, 128);
  publisher.publish("/a");
  reader.drain();
  publisher.publish("/rotate".repeat(30));
  publisher.publish("/unrelated".repeat(4));
  assert.ok(reader.drain().includes("*"));
  publisher.close(); reader.close();
});

test("the measurement verdict rejects the same unsafe headers as runtime admission", () => {
  for (const extra of [
    {"set-cookie": "session=secret"}, {"content-encoding": "gzip"},
    {"content-range": "bytes 0-4/10"}, {"age": "invalid"},
    {"age": "-1"}, {"expires": "Thu, 01 Jan 1970 00:00:00 GMT"},
    {"cache-control": "public=invalid"},
  ]) {
    assert.equal(cacheVerdict({"cache-control": "public", ...extra}, 200).cacheable, false);
  }
  assert.equal(cacheVerdict({"cache-control": "public, max-age=60", age: "10"}, 200).ttlSeconds, 50);
});

test("site configuration rejects malformed booleans, limits and notice paths", () => {
  for (const invalid of [
    {compressDynamic: "false"}, {invalidationFile: 42}, {invalidationFile: ""},
    {maxItems: 1.5}, {maxCacheBytes: 0.5}, {excludePaths: null},
  ]) assert.throws(() => siteConfigFrom(invalid));
});
