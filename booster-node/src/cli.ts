#!/usr/bin/env node
/** Command line helper that scaffolds a Booster adapter inside a host project. */
import { ADAPTER_NAME, CONFIG_NAME, DEFAULT_EXCLUDE, DEFAULT_INCLUDE, writeAdapter, writeConfig } from "./initializer.ts";

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
    "Usage: booster-node init [options]",
    "",
    "  --path <dir>      Host project directory (default: current directory)",
    "  --include <path>  Public route prefix to cache (repeatable)",
    "  --exclude <path>  Route prefix to keep out (repeatable)",
    "  --config          Also write booster.json",
    "  --force           Replace existing files",
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

/** Run the command and report the created files. */
export function main(argv: string[] = process.argv.slice(2)): number {
  if (!argv.includes("--help")) {
    for (const written of runInit(parseArgs(argv))) console.log(`Created ${written}`);
    console.log(`Next: import buildMiddleware from ${ADAPTER_NAME} and register it.`);
    console.log(`See the Booster repository for the plugin recipe and the conformance checklist.`);
    return 0;
  }
  console.log(usage());
  return 0;
}

const entry = process.argv[1] ?? "";
if (/(^|[\\/])cli\.(ts|js)$/.test(entry)) process.exitCode = main();
