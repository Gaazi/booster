/** Prevent explicit header commits from bypassing conservative edge policy. */
import type { ServerResponse } from "node:http";

/** Preserve both supported writeHead header forms while replacing edge directives. */
function protectedHeaders(headers: any): any {
  const blocked = new Set(["cdn-cache-control", "surrogate-control"]);
  if (Array.isArray(headers)) {
    const pairs: string[] = [];
    for (let index = 0; index < headers.length; index += 2) {
      if (!blocked.has(String(headers[index]).toLowerCase())) pairs.push(headers[index], headers[index + 1]);
    }
    return [...pairs, "CDN-Cache-Control", "no-store", "Surrogate-Control", "no-store"];
  }
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(headers || {})) {
    if (!blocked.has(key.toLowerCase())) result[key] = value;
  }
  return {...result, "CDN-Cache-Control": "no-store", "Surrogate-Control": "no-store"};
}

/** Fail closed on manual writeHead; automatic verified end headers remain intact. */
export function guardExplicitHeaders(res: ServerResponse, mode = {automatic: false}): void {
  const writeHead = res.writeHead.bind(res) as (...args: any[]) => ServerResponse;
  res.writeHead = function (...args: any[]): ServerResponse {
    if (!mode.automatic) {
      const index = typeof args[1] === "string" ? 2 : 1;
      args[index] = protectedHeaders(args[index]);
      res.setHeader("CDN-Cache-Control", "no-store");
      res.setHeader("Surrogate-Control", "no-store");
    }
    return writeHead(...args);
  };
}
