/** Serialize notice access with the same bounded directory lock as Python. */
import {mkdirSync, rmdirSync} from "node:fs";

/** Fail closed if a peer cannot release its lock within five seconds. */
export function withFileBusLock<T>(path: string, operation: () => T): T {
  const deadline = Date.now() + 5000;
  const delay = new Int32Array(new SharedArrayBuffer(4));
  while (true) {
    try { mkdirSync(path); break; }
    catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
      if (Date.now() >= deadline) throw new Error(`Invalidation lock is busy: ${path}`);
      Atomics.wait(delay, 0, 0, 5);
    }
  }
  try { return operation(); }
  finally { rmdirSync(path); }
}
