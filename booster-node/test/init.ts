/** Coverage for the host-project scaffolding command. */
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { ADAPTER_NAME, CONFIG_NAME, DEFAULT_EXCLUDE, writeAdapter, writeConfig } from "../src/initializer.ts";
import { parseArgs, runInit, usage } from "../src/cli.ts";

const CLI = fileURLToPath(new URL("../src/cli.ts", import.meta.url));

test("adapter is generated with the requested policy", () => {
  const directory = mkdtempSync(join(tmpdir(), "booster-init-"));
  const target = writeAdapter(directory, ["/static/css/"], ["/media/"]);
  const source = readFileSync(target, "utf8");
  assert.ok(source.includes('const INCLUDE_PATHS = ["/static/css/"];'));
  assert.ok(source.includes('const EXCLUDE_PATHS = ["/media/"];'));
  assert.ok(source.includes("booster.json"));
  assert.ok(source.includes("buildMiddleware"));
});

test("existing adapter is not overwritten", () => {
  const directory = mkdtempSync(join(tmpdir(), "booster-init-"));
  const target = writeAdapter(directory, ["/static/"], DEFAULT_EXCLUDE);
  writeFileSync(target, "// hand written\n", "utf8");
  assert.throws(() => writeAdapter(directory, ["/static/"], DEFAULT_EXCLUDE), /already exists/);
  assert.equal(readFileSync(target, "utf8"), "// hand written\n");
  writeAdapter(directory, ["/static/"], DEFAULT_EXCLUDE, true);
  assert.ok(readFileSync(target, "utf8").includes("buildMiddleware"));
});

test("configuration file matches the requested policy", () => {
  const directory = mkdtempSync(join(tmpdir(), "booster-init-"));
  const target = writeConfig(directory, ["/static/js/"], ["/media/"]);
  const document = JSON.parse(readFileSync(target, "utf8"));
  assert.deepEqual(document.includePaths, ["/static/js/"]);
  assert.deepEqual(document.excludePaths, ["/media/"]);
});

test("command arguments are parsed", () => {
  const options = parseArgs(["--path", "/tmp/site", "--include", "/a/", "--include", "/b/",
    "--exclude", "/c/", "--config", "--force"]);
  assert.equal(options.path, "/tmp/site");
  assert.deepEqual(options.include, ["/a/", "/b/"]);
  assert.deepEqual(options.exclude, ["/c/"]);
  assert.equal(options.config, true);
  assert.equal(options.force, true);
  assert.ok(usage().includes("booster-node init"));
});

test("command creates the adapter and the configuration", () => {
  const directory = mkdtempSync(join(tmpdir(), "booster-init-"));
  const written = runInit({path: directory, include: ["/static/css/"], config: true});
  assert.equal(written.length, 2);
  assert.ok(written[0].endsWith(ADAPTER_NAME));
  assert.ok(written[1].endsWith(CONFIG_NAME));
});

test("installed command scaffolds a host project", () => {
  const directory = mkdtempSync(join(tmpdir(), "booster-init-"));
  execFileSync(process.execPath, [CLI, "init", "--path", directory, "--include", "/static/js/"],
    {stdio: "pipe"});
  const source = readFileSync(join(directory, ADAPTER_NAME), "utf8");
  assert.ok(source.includes('const INCLUDE_PATHS = ["/static/js/"];'));
});
