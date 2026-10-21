#!/usr/bin/env node
/** Command line helper that scaffolds a Booster adapter inside a host project. */
import { ADAPTER_NAME, CONFIG_NAME, DEFAULT_EXCLUDE, DEFAULT_INCLUDE, writeAdapter, writeConfig } from "./initializer.ts";
import { cacheVerdict } from "./policy.ts";
import { VERSION } from "./status.ts";

export interface InitOptions {
  path?: string;
  include?: string[];
  exclude?: string[];
  config?: boolean;
  force?: boolean;
}

/** Generate the adapter and, when asked, the matching site configuration. */
export function runInit(options: InitOptions = {}): string[] {
  const include = options.include?.length ? options.include : DEFAULT_INCLUDE;
  const exclude = options.exclude?.length ? options.exclude : DEFAULT_EXCLUDE;
  const directory = options.path ?? process.cwd();
  const written = [writeAdapter(directory, include, exclude, options.force)];
  if (options.config) written.push(writeConfig(directory, include, exclude, options.force));
  return written;
}

/** Print the command help. */
export function usage(): string {
  return [
    "Usage: booster-node <command> [options]",
    "",
    "  init      Scaffold a Booster adapter in a host project",
    "  measure   Measure one URL and report whether the engine could store it",
    "  doctor    Report the runtime and the engine version",
  ].join("\n");
}

/** Parse the command arguments without a dependency on a parser library. */
export function parseArgs(argv: string[]): InitOptions {
  const options: InitOptions = {include: [], exclude: []};
  for (let index = 0; index < argv.length; index++) {
    const argument = argv[index];
    if (argument === "--path") options.path = argv[++index];
    else if (argument === "--include") options.include!.push(argv[++index]);
    else if (argument === "--exclude") options.exclude!.push(argv[++index]);
    else if (argument === "--config") options.config = true;
    else if (argument === "--force") options.force = true;
  }
  if (!options.include!.length) delete options.include;
  if (!options.exclude!.length) delete options.exclude;
  return options;
}

/** Measure one URL and report whether the engine could store the response. */
export async function runMeasure(options: { url: string; requests: number }): Promise<unknown> {
  const durations: number[] = [];
  let status = 0;
  let bytes = 0;
  let headers: Record<string, string> = {};
  for (let index = 0; index < Math.max(1, options.requests); index++) {
    const start = performance.now();
    const response = await fetch(options.url, { headers: {"accept-encoding": "identity"} });
    const body = Buffer.from(await response.arrayBuffer());
    durations.push(performance.now() - start);
    status = response.status;
    bytes = body.length;
    headers = Object.fromEntries(response.headers.entries());
  }
  const ordered = [...durations].sort((a, b) => a - b);
  const pick = (fraction: number): number => ordered[Math.min(ordered.length - 1,
    Math.max(0, Math.round(fraction * (ordered.length - 1))))];
  return {
    url: options.url,
    status,
    bytes,
    cache_control: headers["cache-control"] ?? "",
    etag: headers["etag"] ?? "",
    vary: headers["vary"] ?? "",
    p50_ms: Math.round(pick(0.5) * 100) / 100,
    p95_ms: Math.round(pick(0.95) * 100) / 100,
    samples: durations.length,
    verdict: cacheVerdict(headers, status),
  };
}

/** Report the runtime and the engine version. */
export function runDoctor(): unknown {
  return {
    node: process.versions.node,
    booster: VERSION,
    platform: process.platform,
    command: process.argv[1] ?? "",
  };
}

/** Run the command and report the created files. */
export function main(argv: string[] = process.argv.slice(2)): number {
  const command = argv[0];
  if (command === "measure") {
    const url = argv[1];
    if (!url) { console.error("Usage: booster-node measure <url> [--requests N]"); return 1; }
    const requests = Number(argv[argv.indexOf("--requests") + 1] ?? "20");
    runMeasure({url, requests}).then(report => console.log(JSON.stringify(report, null, 2)));
    return 0;
  }
  if (command === "doctor") {
    console.log(JSON.stringify(runDoctor(), null, 2));
    return 0;
  }
  if (command === "init") {
    for (const written of runInit(parseArgs(argv.slice(1)))) console.log(`Created ${written}`);
    console.log(`Next: import buildMiddleware from ${ADAPTER_NAME} and register it.`);
    console.log(`See the Booster repository for the plugin recipe and the conformance checklist.`);
    return 0;
  }
  console.log(usage());
  return 0;
}

const entry = process.argv[1] ?? "";
if (/(^|[\\/])cli\.(ts|js)$/.test(entry)) process.exitCode = main();
